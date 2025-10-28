#!/usr/bin/env python3
"""
Example Usage Script for Manga Scraper
=======================================

This script demonstrates how to use the manga scraper
for common tasks. Customize it for your specific needs.
"""

import logging
from manga_scraper import MangaScraper
from config import ScraperConfig

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def example_1_simple_scrape():
    """Example 1: Simple single manga scrape"""
    logger.info("Example 1: Simple scraping")
    
    scraper = MangaScraper(
        s3_bucket='my-manga-bucket',
        dynamodb_table='manga-metadata',
        region='us-east-1'
    )
    
    # Scrape a manga (limit to 1 chapter for testing)
    success = scraper.scrape_full_manga(
        manga_url='https://example.com/manga/test-manga',
        manga_id='test-manga',
        max_chapters=1
    )
    
    logger.info(f"Scraping {'succeeded' if success else 'failed'}")


def example_2_with_config():
    """Example 2: Using configuration file"""
    logger.info("Example 2: Using configuration")
    
    # Load configuration from environment
    config = ScraperConfig.from_env()
    
    # Validate configuration
    try:
        config.validate()
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        return
    
    # Create scraper with config
    scraper = MangaScraper(
        s3_bucket=config.s3_bucket,
        dynamodb_table=config.dynamodb_table,
        region=config.aws_region
    )
    
    logger.info("Scraper initialized with configuration")


def example_3_multiple_manga():
    """Example 3: Process multiple manga"""
    logger.info("Example 3: Multiple manga scraping")
    
    scraper = MangaScraper(
        s3_bucket='my-manga-bucket',
        dynamodb_table='manga-metadata'
    )
    
    # List of manga to scrape
    manga_list = [
        {
            'url': 'https://example.com/manga/one-piece',
            'id': 'one-piece',
            'max_chapters': 3
        },
        {
            'url': 'https://example.com/manga/naruto',
            'id': 'naruto',
            'max_chapters': 3
        },
    ]
    
    results = {}
    for manga in manga_list:
        logger.info(f"Processing: {manga['id']}")
        
        success = scraper.scrape_full_manga(
            manga_url=manga['url'],
            manga_id=manga['id'],
            max_chapters=manga.get('max_chapters')
        )
        
        results[manga['id']] = success
    
    # Summary
    successful = sum(1 for v in results.values() if v)
    logger.info(f"Completed: {successful}/{len(manga_list)} manga")


def example_4_error_handling():
    """Example 4: With error handling"""
    logger.info("Example 4: Error handling example")
    
    try:
        scraper = MangaScraper(
            s3_bucket='my-manga-bucket',
            dynamodb_table='manga-metadata'
        )
        
        success = scraper.scrape_full_manga(
            manga_url='https://example.com/manga/test',
            manga_id='test-manga',
            max_chapters=1
        )
        
        if not success:
            logger.warning("Scraping completed with errors")
        
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        # Handle error (send notification, retry, etc.)


def example_5_custom_processing():
    """Example 5: Custom processing workflow"""
    logger.info("Example 5: Custom workflow")
    
    scraper = MangaScraper(
        s3_bucket='my-manga-bucket',
        dynamodb_table='manga-metadata'
    )
    
    # Step 1: Scrape manga list
    manga_urls = scraper.scrape_manga_list('https://example.com/popular')
    logger.info(f"Found {len(manga_urls)} manga")
    
    # Step 2: Process each manga
    for idx, url in enumerate(manga_urls[:5], 1):  # Limit to 5 for example
        logger.info(f"Processing manga {idx}/5")
        
        # Extract manga ID from URL
        manga_id = url.split('/')[-1]
        
        # Scrape with custom settings
        scraper.scrape_full_manga(
            manga_url=url,
            manga_id=manga_id,
            max_chapters=2  # Only first 2 chapters
        )


def example_6_testing_components():
    """Example 6: Testing individual components"""
    logger.info("Example 6: Component testing")
    
    from manga_scraper import ImageProcessor, RateLimiter
    from PIL import Image
    from io import BytesIO
    
    # Test image processor
    processor = ImageProcessor(quality=85)
    
    # Create test image
    img = Image.new('RGB', (800, 1200), color='red')
    img_bytes = BytesIO()
    img.save(img_bytes, format='JPEG')
    
    # Optimize
    optimized, hash_val = processor.optimize_image(img_bytes.getvalue())
    logger.info(f"Optimized image: {len(img_bytes.getvalue())/1024:.1f}KB -> {len(optimized)/1024:.1f}KB")
    
    # Test rate limiter
    limiter = RateLimiter(requests_per_second=2.0)
    logger.info("Testing rate limiter...")
    limiter.wait()
    logger.info("Rate limiter working correctly")


def main():
    """Run examples"""
    logger.info("=" * 50)
    logger.info("Manga Scraper - Example Usage")
    logger.info("=" * 50)
    
    # Uncomment the example you want to run:
    
    # example_1_simple_scrape()
    # example_2_with_config()
    # example_3_multiple_manga()
    # example_4_error_handling()
    # example_5_custom_processing()
    example_6_testing_components()
    
    logger.info("=" * 50)
    logger.info("Example completed!")
    logger.info("=" * 50)


if __name__ == '__main__':
    main()
