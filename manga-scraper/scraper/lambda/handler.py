"""
Lambda Handler
==============

AWS Lambda entry point for manga scraping operations.
"""

from __future__ import annotations
import os
import json
import logging
from typing import Dict, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from src.config import ScraperConfig
    from src.processors import ImageProcessor, DuplicateDetector
    from src.storage import S3Storage, DynamoDBManager

# Setup basic logging first
logging.basicConfig(level=os.environ.get('LOG_LEVEL', 'INFO'))
logger = logging.getLogger('lambda_handler')


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    AWS Lambda handler function for manga scraping

    Event structure:
    {
        "action": "scrape_manga" | "scrape_chapter" | "list_manga",
        "source": "mangadex" | "mangakakalot",
        "manga_url": "https://...",  # For scrape_manga
        "manga_id": "one-piece",  # For scrape_chapter
        "chapter_url": "https://...",  # For scrape_chapter
        "max_chapters": 10,  # Optional limit
        "options": {  # Optional configuration overrides
            "skip_images": false,
            "image_quality": 85
        }
    }

    Args:
        event: Lambda event object
        context: Lambda context object

    Returns:
        Response dict with status and results
    """
    try:
        logger.info(f"Lambda invoked with event: {json.dumps(event)}")

        # Extract action
        action = event.get('action', 'scrape_manga')

        # Handle health check first (no imports needed)
        if action == 'health_check':
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'success': True,
                    'message': 'Manga scraper is healthy',
                    'version': '1.0.0',
                    'environment': {
                        'S3_BUCKET': os.environ.get('S3_BUCKET', 'not set'),
                        'DYNAMODB_TABLE': os.environ.get('DYNAMODB_TABLE', 'not set'),
                        'AWS_REGION': os.environ.get('AWS_REGION', 'not set')
                    }
                })
            }

        # Import modules only when needed for actual scraping
        from src.config import ScraperConfig
        from src.scrapers import MangaDexScraper, MangaKakalotScraper
        from src.processors import ImageProcessor, DuplicateDetector
        from src.storage import S3Storage, DynamoDBManager

        source = event.get('source', 'mangadex').lower()

        # Get configuration
        config = ScraperConfig.from_env()
        config.validate()

        # Initialize components
        scraper = _get_scraper(source, MangaDexScraper, MangaKakalotScraper)
        image_processor = ImageProcessor(
            target_size_kb=config.target_image_size_kb,
            webp_quality=config.webp_quality
        )
        duplicate_detector = DuplicateDetector()
        s3_storage = S3Storage(config.s3_bucket, config.aws_region)
        db_manager = DynamoDBManager(config.dynamodb_table, config.aws_region)

        # Route to appropriate handler
        if action == 'scrape_manga':
            result = handle_scrape_manga(
                event, scraper, image_processor, duplicate_detector,
                s3_storage, db_manager, config
            )
        elif action == 'scrape_chapter':
            result = handle_scrape_chapter(
                event, scraper, image_processor, duplicate_detector,
                s3_storage, db_manager
            )
        elif action == 'list_manga':
            result = handle_list_manga(event, scraper)
        else:
            raise ValueError(f"Unknown action: {action}")

        logger.info(f"Lambda completed successfully: {action}")

        return {
            'statusCode': 200,
            'body': json.dumps({
                'success': True,
                'action': action,
                'result': result
            })
        }

    except Exception as e:
        logger.error(f"Lambda execution failed: {e}", exc_info=True)

        return {
            'statusCode': 500,
            'body': json.dumps({
                'success': False,
                'error': str(e),
                'error_type': type(e).__name__
            })
        }


def handle_scrape_manga(
    event: Dict[str, Any],
    scraper: Any,
    image_processor: ImageProcessor,
    duplicate_detector: DuplicateDetector,
    s3_storage: S3Storage,
    db_manager: DynamoDBManager,
    config: ScraperConfig
) -> Dict[str, Any]:
    """
    Handle manga scraping action

    Args:
        event: Lambda event
        scraper: Scraper instance
        image_processor: Image processor
        duplicate_detector: Duplicate detector
        s3_storage: S3 storage manager
        db_manager: DynamoDB manager
        config: Scraper configuration

    Returns:
        Result dictionary
    """
    manga_url = event.get('manga_url')
    if not manga_url:
        raise ValueError("manga_url is required for scrape_manga action")

    manga_id = event.get('manga_id')
    max_chapters = event.get('max_chapters')
    skip_images = event.get('options', {}).get('skip_images', False)

    logger.info(f"Scraping manga: {manga_url}")

    # Scrape manga details
    manga = scraper.scrape_manga_details(manga_url)
    if not manga:
        raise Exception("Failed to scrape manga details")

    # Use provided manga_id or generate from title
    if not manga_id:
        manga_id = manga.manga_id

    manga.manga_id = manga_id

    # Save manga metadata
    success = db_manager.save_manga(manga)
    if not success:
        logger.warning("Failed to save manga metadata")

    # Get chapter list
    chapters_info = scraper.scrape_chapter_list(manga_url)
    logger.info(f"Found {len(chapters_info)} chapters")

    # Limit chapters if specified
    if max_chapters:
        chapters_info = chapters_info[:max_chapters]

    scraped_chapters = []
    failed_chapters = []

    # Process each chapter
    for idx, chapter_info in enumerate(chapters_info, 1):
        try:
            logger.info(f"Processing chapter {idx}/{len(chapters_info)}: {chapter_info['number']}")

            # Scrape chapter pages
            page_urls = scraper.scrape_chapter_pages(chapter_info['url'])

            if not page_urls:
                logger.warning(f"No pages found for chapter {chapter_info['number']}")
                failed_chapters.append(chapter_info['number'])
                continue

            # Process images unless skipped
            if not skip_images:
                _process_chapter_images(
                    manga_id,
                    chapter_info,
                    page_urls,
                    scraper,
                    image_processor,
                    duplicate_detector,
                    s3_storage
                )

            # Save chapter metadata
            from src.models import Chapter, Page
            from datetime import datetime

            pages = [
                Page(page_number=i, image_url=url)
                for i, url in enumerate(page_urls, 1)
            ]

            chapter = Chapter(
                manga_id=manga_id,
                chapter_id=f"{manga_id}-{chapter_info['number']}",
                chapter_number=chapter_info['number'],
                chapter_title=chapter_info['title'],
                pages=pages,
                original_url=chapter_info['url']
            )

            db_manager.save_chapter(chapter)
            scraped_chapters.append(chapter_info['number'])

        except Exception as e:
            logger.error(f"Failed to process chapter {chapter_info['number']}: {e}")
            failed_chapters.append(chapter_info['number'])

    return {
        'manga_id': manga_id,
        'manga_title': manga.title,
        'total_chapters': len(chapters_info),
        'scraped_chapters': len(scraped_chapters),
        'failed_chapters': len(failed_chapters),
        'failed_chapter_numbers': failed_chapters,
        'duplicate_stats': duplicate_detector.get_statistics()
    }


def handle_scrape_chapter(
    event: Dict[str, Any],
    scraper: Any,
    image_processor: ImageProcessor,
    duplicate_detector: DuplicateDetector,
    s3_storage: S3Storage,
    db_manager: DynamoDBManager
) -> Dict[str, Any]:
    """
    Handle single chapter scraping action

    Args:
        event: Lambda event
        scraper: Scraper instance
        image_processor: Image processor
        duplicate_detector: Duplicate detector
        s3_storage: S3 storage manager
        db_manager: DynamoDB manager

    Returns:
        Result dictionary
    """
    chapter_url = event.get('chapter_url')
    manga_id = event.get('manga_id')
    chapter_number = event.get('chapter_number')

    if not chapter_url or not manga_id or not chapter_number:
        raise ValueError("chapter_url, manga_id, and chapter_number are required")

    logger.info(f"Scraping chapter: {chapter_url}")

    # Scrape chapter pages
    page_urls = scraper.scrape_chapter_pages(chapter_url)

    if not page_urls:
        raise Exception("No pages found in chapter")

    # Process images
    successful_pages = _process_chapter_images(
        manga_id,
        {'number': chapter_number, 'title': '', 'url': chapter_url},
        page_urls,
        scraper,
        image_processor,
        duplicate_detector,
        s3_storage
    )

    return {
        'manga_id': manga_id,
        'chapter_number': chapter_number,
        'total_pages': len(page_urls),
        'processed_pages': successful_pages,
        'duplicate_stats': duplicate_detector.get_statistics()
    }


def handle_list_manga(event: Dict[str, Any], scraper: Any) -> Dict[str, Any]:
    """
    Handle manga list scraping action

    Args:
        event: Lambda event
        scraper: Scraper instance

    Returns:
        Result dictionary
    """
    page = event.get('page', 1)

    logger.info(f"Listing manga from page {page}")

    manga_urls = scraper.scrape_manga_list(page)

    return {
        'page': page,
        'manga_count': len(manga_urls),
        'manga_urls': manga_urls
    }


def _get_scraper(source: str, MangaDexScraper, MangaKakalotScraper) -> Any:
    """
    Get scraper instance for source

    Args:
        source: Source name
        MangaDexScraper: MangaDex scraper class
        MangaKakalotScraper: MangaKakalot scraper class

    Returns:
        Scraper instance
    """
    scrapers = {
        'mangadex': MangaDexScraper,
        'mangakakalot': MangaKakalotScraper,
    }

    scraper_class = scrapers.get(source)
    if not scraper_class:
        raise ValueError(f"Unknown source: {source}")

    return scraper_class()


def _process_chapter_images(
    manga_id: str,
    chapter_info: Dict[str, str],
    page_urls: list,
    scraper: Any,
    image_processor: ImageProcessor,
    duplicate_detector: DuplicateDetector,
    s3_storage: S3Storage
) -> int:
    """
    Process and upload chapter images

    Args:
        manga_id: Manga identifier
        chapter_info: Chapter information dict
        page_urls: List of page image URLs
        scraper: Scraper instance
        image_processor: Image processor
        duplicate_detector: Duplicate detector
        s3_storage: S3 storage manager

    Returns:
        Number of successfully processed pages
    """
    successful_pages = 0

    for page_num, img_url in enumerate(page_urls, 1):
        try:
            # Download image
            image_data = scraper.download_image(img_url)

            # Optimize image
            optimized_data, image_hash, metadata = image_processor.optimize_image(image_data)

            # Check for duplicates
            if duplicate_detector.check_and_add(image_hash):
                logger.info(f"Duplicate image detected, skipping page {page_num}")
                continue

            # Generate S3 keys
            s3_key = f"manga/{manga_id}/chapters/{chapter_info['number']}/page_{page_num:03d}.webp"
            thumb_key = f"manga/{manga_id}/chapters/{chapter_info['number']}/thumbnails/page_{page_num:03d}.webp"

            # Upload full image
            s3_storage.upload_image(
                optimized_data,
                s3_key,
                metadata={
                    'manga_id': manga_id,
                    'chapter': chapter_info['number'],
                    'page': str(page_num),
                    'hash': image_hash
                }
            )

            # Create and upload thumbnail
            thumbnail_data = image_processor.create_thumbnail(optimized_data)
            s3_storage.upload_image(thumbnail_data, thumb_key)

            successful_pages += 1

        except Exception as e:
            logger.error(f"Failed to process page {page_num}: {e}")

    return successful_pages


# For local testing
if __name__ == '__main__':
    # Example test event
    test_event = {
        'action': 'list_manga',
        'source': 'mangadex',
        'page': 1
    }

    result = lambda_handler(test_event, None)
    print(json.dumps(result, indent=2))
