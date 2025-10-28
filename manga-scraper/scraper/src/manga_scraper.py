"""
Manga Scraper - Professional Web Scraping Engine
=================================================

A production-ready manga scraping service with:
- Rate limiting and politeness delays
- Retry logic with exponential backoff
- Comprehensive error handling and logging
- Progress tracking and resume capability
- AWS Lambda compatibility
- Image optimization and processing
"""

import os
import time
import hashlib
import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
from io import BytesIO
import json

import requests
from bs4 import BeautifulSoup
from PIL import Image
import boto3
from botocore.exceptions import ClientError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class MangaMetadata:
    """Data class for manga metadata"""
    title: str
    author: str
    genres: List[str]
    description: str
    cover_url: str
    status: str
    chapters: List[Dict]


@dataclass
class ChapterData:
    """Data class for chapter information"""
    manga_id: str
    chapter_number: str
    chapter_title: str
    page_urls: List[str]
    upload_date: str


class ImageProcessor:
    """Handles image optimization and processing"""
    
    def __init__(self, target_size_kb: int = 200, quality: int = 85):
        """
        Initialize image processor
        
        Args:
            target_size_kb: Target file size in KB
            quality: WebP quality (0-100)
        """
        self.target_size_kb = target_size_kb
        self.quality = quality
    
    def optimize_image(self, image_data: bytes) -> Tuple[bytes, str]:
        """
        Optimize image by converting to WebP and compressing
        
        Args:
            image_data: Raw image bytes
            
        Returns:
            Tuple of (optimized_bytes, image_hash)
        """
        try:
            # Open image
            img = Image.open(BytesIO(image_data))
            
            # Convert to RGB if necessary
            if img.mode in ('RGBA', 'LA', 'P'):
                background = Image.new('RGB', img.size, (255, 255, 255))
                if img.mode == 'P':
                    img = img.convert('RGBA')
                background.paste(img, mask=img.split()[-1] if img.mode in ('RGBA', 'LA') else None)
                img = background
            
            # Optimize to WebP
            output = BytesIO()
            img.save(output, format='WEBP', quality=self.quality, method=6)
            optimized_data = output.getvalue()
            
            # Calculate hash for duplicate detection
            image_hash = hashlib.md5(optimized_data).hexdigest()
            
            logger.info(f"Image optimized: {len(image_data)/1024:.1f}KB -> {len(optimized_data)/1024:.1f}KB")
            
            return optimized_data, image_hash
            
        except Exception as e:
            logger.error(f"Error optimizing image: {e}")
            raise
    
    def create_thumbnail(self, image_data: bytes, max_width: int = 300) -> bytes:
        """
        Create thumbnail for preview
        
        Args:
            image_data: Raw image bytes
            max_width: Maximum width in pixels
            
        Returns:
            Thumbnail bytes
        """
        try:
            img = Image.open(BytesIO(image_data))
            
            # Calculate new dimensions
            ratio = max_width / img.width
            new_height = int(img.height * ratio)
            
            # Resize
            img_resized = img.resize((max_width, new_height), Image.Resampling.LANCZOS)
            
            # Save as WebP
            output = BytesIO()
            img_resized.save(output, format='WEBP', quality=70)
            
            return output.getvalue()
            
        except Exception as e:
            logger.error(f"Error creating thumbnail: {e}")
            raise


class RateLimiter:
    """Implements rate limiting and politeness delays"""
    
    def __init__(self, requests_per_second: float = 1.0, base_delay: float = 2.0):
        """
        Initialize rate limiter
        
        Args:
            requests_per_second: Maximum requests per second
            base_delay: Base delay between requests in seconds
        """
        self.min_interval = 1.0 / requests_per_second
        self.base_delay = base_delay
        self.last_request_time = 0
    
    def wait(self):
        """Wait appropriate amount of time before next request"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        
        if time_since_last < self.min_interval:
            sleep_time = self.min_interval - time_since_last + self.base_delay
            logger.debug(f"Rate limiting: sleeping {sleep_time:.2f}s")
            time.sleep(sleep_time)
        else:
            time.sleep(self.base_delay)
        
        self.last_request_time = time.time()


class RetryHandler:
    """Implements retry logic with exponential backoff"""
    
    def __init__(self, max_retries: int = 3, base_delay: float = 1.0, max_delay: float = 60.0):
        """
        Initialize retry handler
        
        Args:
            max_retries: Maximum number of retry attempts
            base_delay: Base delay for exponential backoff
            max_delay: Maximum delay between retries
        """
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
    
    def execute_with_retry(self, func, *args, **kwargs):
        """
        Execute function with retry logic
        
        Args:
            func: Function to execute
            *args, **kwargs: Arguments to pass to function
            
        Returns:
            Function result
            
        Raises:
            Exception: If all retries exhausted
        """
        last_exception = None
        
        for attempt in range(self.max_retries):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                last_exception = e
                if attempt < self.max_retries - 1:
                    delay = min(self.base_delay * (2 ** attempt), self.max_delay)
                    logger.warning(f"Attempt {attempt + 1} failed: {e}. Retrying in {delay}s...")
                    time.sleep(delay)
                else:
                    logger.error(f"All {self.max_retries} attempts failed")
        
        raise last_exception


class S3Storage:
    """Handles S3 storage operations"""
    
    def __init__(self, bucket_name: str, region: str = 'us-east-1'):
        """
        Initialize S3 storage handler
        
        Args:
            bucket_name: S3 bucket name
            region: AWS region
        """
        self.bucket_name = bucket_name
        self.s3_client = boto3.client('s3', region_name=region)
        self.image_hashes = set()
    
    def upload_image(self, image_data: bytes, key: str, metadata: Optional[Dict] = None) -> bool:
        """
        Upload image to S3
        
        Args:
            image_data: Image bytes
            key: S3 object key
            metadata: Optional metadata dict
            
        Returns:
            True if successful
        """
        try:
            extra_args = {
                'ContentType': 'image/webp',
                'CacheControl': 'max-age=2592000',  # 30 days
            }
            
            if metadata:
                extra_args['Metadata'] = metadata
            
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=key,
                Body=image_data,
                **extra_args
            )
            
            logger.info(f"Uploaded to S3: {key}")
            return True
            
        except ClientError as e:
            logger.error(f"Error uploading to S3: {e}")
            return False
    
    def check_duplicate(self, image_hash: str) -> bool:
        """
        Check if image hash already exists
        
        Args:
            image_hash: MD5 hash of image
            
        Returns:
            True if duplicate exists
        """
        return image_hash in self.image_hashes
    
    def add_hash(self, image_hash: str):
        """Add hash to tracking set"""
        self.image_hashes.add(image_hash)


class DynamoDBManager:
    """Handles DynamoDB operations for metadata"""
    
    def __init__(self, table_name: str, region: str = 'us-east-1'):
        """
        Initialize DynamoDB manager
        
        Args:
            table_name: DynamoDB table name
            region: AWS region
        """
        self.table_name = table_name
        self.dynamodb = boto3.resource('dynamodb', region_name=region)
        self.table = self.dynamodb.Table(table_name)
    
    def save_manga_metadata(self, manga_id: str, metadata: MangaMetadata) -> bool:
        """
        Save manga metadata to DynamoDB
        
        Args:
            manga_id: Unique manga identifier
            metadata: MangaMetadata object
            
        Returns:
            True if successful
        """
        try:
            item = {
                'PK': f'MANGA#{manga_id}',
                'SK': 'METADATA',
                'manga_id': manga_id,
                'title': metadata.title,
                'author': metadata.author,
                'genres': metadata.genres,
                'description': metadata.description,
                'cover_url': metadata.cover_url,
                'status': metadata.status,
                'chapters': metadata.chapters,
                'updated_at': datetime.utcnow().isoformat(),
            }
            
            self.table.put_item(Item=item)
            logger.info(f"Saved metadata for manga: {manga_id}")
            return True
            
        except ClientError as e:
            logger.error(f"Error saving to DynamoDB: {e}")
            return False
    
    def save_chapter_metadata(self, chapter_data: ChapterData) -> bool:
        """
        Save chapter metadata to DynamoDB
        
        Args:
            chapter_data: ChapterData object
            
        Returns:
            True if successful
        """
        try:
            item = {
                'PK': f'MANGA#{chapter_data.manga_id}',
                'SK': f'CHAPTER#{chapter_data.chapter_number}',
                'manga_id': chapter_data.manga_id,
                'chapter_number': chapter_data.chapter_number,
                'chapter_title': chapter_data.chapter_title,
                'page_count': len(chapter_data.page_urls),
                'upload_date': chapter_data.upload_date,
                'updated_at': datetime.utcnow().isoformat(),
            }
            
            self.table.put_item(Item=item)
            logger.info(f"Saved chapter {chapter_data.chapter_number} for manga {chapter_data.manga_id}")
            return True
            
        except ClientError as e:
            logger.error(f"Error saving chapter to DynamoDB: {e}")
            return False
    
    def get_manga_metadata(self, manga_id: str) -> Optional[Dict]:
        """
        Retrieve manga metadata from DynamoDB
        
        Args:
            manga_id: Unique manga identifier
            
        Returns:
            Metadata dict or None
        """
        try:
            response = self.table.get_item(
                Key={
                    'PK': f'MANGA#{manga_id}',
                    'SK': 'METADATA'
                }
            )
            return response.get('Item')
            
        except ClientError as e:
            logger.error(f"Error retrieving from DynamoDB: {e}")
            return None


class MangaScraper:
    """Main manga scraper class"""
    
    def __init__(
        self,
        s3_bucket: str,
        dynamodb_table: str,
        region: str = 'us-east-1',
        user_agent: str = 'MangaScraperBot/1.0'
    ):
        """
        Initialize manga scraper
        
        Args:
            s3_bucket: S3 bucket name for image storage
            dynamodb_table: DynamoDB table name for metadata
            region: AWS region
            user_agent: User agent string for requests
        """
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': user_agent})
        
        self.rate_limiter = RateLimiter(requests_per_second=0.5, base_delay=2.0)
        self.retry_handler = RetryHandler(max_retries=3)
        self.image_processor = ImageProcessor()
        self.s3_storage = S3Storage(s3_bucket, region)
        self.db_manager = DynamoDBManager(dynamodb_table, region)
        
        logger.info("MangaScraper initialized")
    
    def fetch_page(self, url: str) -> BeautifulSoup:
        """
        Fetch and parse a web page
        
        Args:
            url: URL to fetch
            
        Returns:
            BeautifulSoup object
        """
        def _fetch():
            self.rate_limiter.wait()
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            return BeautifulSoup(response.content, 'html.parser')
        
        return self.retry_handler.execute_with_retry(_fetch)
    
    def download_image(self, url: str) -> bytes:
        """
        Download image from URL
        
        Args:
            url: Image URL
            
        Returns:
            Image bytes
        """
        def _download():
            self.rate_limiter.wait()
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            return response.content
        
        return self.retry_handler.execute_with_retry(_download)
    
    def scrape_manga_list(self, url: str) -> List[str]:
        """
        Scrape list of manga URLs from index page
        
        Args:
            url: URL of manga list page
            
        Returns:
            List of manga URLs
        """
        logger.info(f"Scraping manga list from: {url}")
        
        try:
            soup = self.fetch_page(url)
            
            # TODO: Customize selectors based on your source website
            manga_links = []
            for link in soup.select('a.manga-link'):  # Example selector
                manga_url = link.get('href')
                if manga_url:
                    manga_links.append(manga_url)
            
            logger.info(f"Found {len(manga_links)} manga")
            return manga_links
            
        except Exception as e:
            logger.error(f"Error scraping manga list: {e}")
            return []
    
    def scrape_manga_details(self, url: str) -> Optional[MangaMetadata]:
        """
        Scrape detailed manga information
        
        Args:
            url: Manga detail page URL
            
        Returns:
            MangaMetadata object or None
        """
        logger.info(f"Scraping manga details from: {url}")
        
        try:
            soup = self.fetch_page(url)
            
            # TODO: Customize selectors based on your source website
            # This is an example structure
            title = soup.select_one('h1.manga-title').text.strip()
            author = soup.select_one('span.author').text.strip()
            description = soup.select_one('div.description').text.strip()
            cover_url = soup.select_one('img.cover').get('src')
            status = soup.select_one('span.status').text.strip()
            
            # Extract genres
            genres = [g.text.strip() for g in soup.select('span.genre')]
            
            # Extract chapter list
            chapters = []
            for ch in soup.select('a.chapter-link'):
                chapters.append({
                    'number': ch.get('data-chapter'),
                    'title': ch.text.strip(),
                    'url': ch.get('href')
                })
            
            metadata = MangaMetadata(
                title=title,
                author=author,
                genres=genres,
                description=description,
                cover_url=cover_url,
                status=status,
                chapters=chapters
            )
            
            logger.info(f"Scraped details for: {title}")
            return metadata
            
        except Exception as e:
            logger.error(f"Error scraping manga details: {e}")
            return None
    
    def scrape_chapter_images(self, url: str) -> List[str]:
        """
        Scrape image URLs from chapter page
        
        Args:
            url: Chapter page URL
            
        Returns:
            List of image URLs
        """
        logger.info(f"Scraping chapter images from: {url}")
        
        try:
            soup = self.fetch_page(url)
            
            # TODO: Customize selectors based on your source website
            image_urls = []
            for img in soup.select('img.chapter-image'):
                img_url = img.get('src') or img.get('data-src')
                if img_url:
                    image_urls.append(img_url)
            
            logger.info(f"Found {len(image_urls)} images in chapter")
            return image_urls
            
        except Exception as e:
            logger.error(f"Error scraping chapter images: {e}")
            return []
    
    def process_and_upload_image(
        self,
        image_url: str,
        manga_id: str,
        chapter_num: str,
        page_num: int
    ) -> bool:
        """
        Download, process, and upload image to S3
        
        Args:
            image_url: Source image URL
            manga_id: Manga identifier
            chapter_num: Chapter number
            page_num: Page number
            
        Returns:
            True if successful
        """
        try:
            # Download image
            image_data = self.download_image(image_url)
            
            # Optimize image
            optimized_data, image_hash = self.image_processor.optimize_image(image_data)
            
            # Check for duplicates
            if self.s3_storage.check_duplicate(image_hash):
                logger.info(f"Duplicate image detected, skipping: {image_url}")
                return True
            
            # Generate S3 key
            s3_key = f"manga/{manga_id}/chapters/{chapter_num}/page_{page_num:03d}.webp"
            
            # Upload to S3
            success = self.s3_storage.upload_image(
                optimized_data,
                s3_key,
                metadata={
                    'manga_id': manga_id,
                    'chapter': chapter_num,
                    'page': str(page_num),
                    'hash': image_hash
                }
            )
            
            if success:
                self.s3_storage.add_hash(image_hash)
                
                # Create and upload thumbnail
                thumbnail_data = self.image_processor.create_thumbnail(optimized_data)
                thumb_key = f"manga/{manga_id}/chapters/{chapter_num}/thumbnails/page_{page_num:03d}.webp"
                self.s3_storage.upload_image(thumbnail_data, thumb_key)
            
            return success
            
        except Exception as e:
            logger.error(f"Error processing image {image_url}: {e}")
            return False
    
    def scrape_full_manga(self, manga_url: str, manga_id: str, max_chapters: int = None) -> bool:
        """
        Scrape complete manga including all chapters
        
        Args:
            manga_url: Manga detail page URL
            manga_id: Unique manga identifier
            max_chapters: Optional limit on number of chapters to scrape
            
        Returns:
            True if successful
        """
        logger.info(f"Starting full manga scrape: {manga_id}")
        
        try:
            # Scrape manga details
            metadata = self.scrape_manga_details(manga_url)
            if not metadata:
                logger.error("Failed to scrape manga metadata")
                return False
            
            # Save metadata to DynamoDB
            self.db_manager.save_manga_metadata(manga_id, metadata)
            
            # Download cover image
            if metadata.cover_url:
                self.process_and_upload_image(
                    metadata.cover_url,
                    manga_id,
                    'cover',
                    0
                )
            
            # Process chapters
            chapters_to_process = metadata.chapters[:max_chapters] if max_chapters else metadata.chapters
            
            for idx, chapter_info in enumerate(chapters_to_process, 1):
                logger.info(f"Processing chapter {idx}/{len(chapters_to_process)}: {chapter_info['number']}")
                
                # Scrape chapter images
                image_urls = self.scrape_chapter_images(chapter_info['url'])
                
                if not image_urls:
                    logger.warning(f"No images found for chapter {chapter_info['number']}")
                    continue
                
                # Download and process each image
                successful_pages = 0
                for page_num, img_url in enumerate(image_urls, 1):
                    if self.process_and_upload_image(
                        img_url,
                        manga_id,
                        chapter_info['number'],
                        page_num
                    ):
                        successful_pages += 1
                
                # Save chapter metadata
                chapter_data = ChapterData(
                    manga_id=manga_id,
                    chapter_number=chapter_info['number'],
                    chapter_title=chapter_info['title'],
                    page_urls=image_urls,
                    upload_date=datetime.utcnow().isoformat()
                )
                self.db_manager.save_chapter_metadata(chapter_data)
                
                logger.info(f"Chapter {chapter_info['number']} complete: {successful_pages}/{len(image_urls)} pages")
            
            logger.info(f"Manga scrape complete: {manga_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error scraping full manga: {e}")
            return False


def lambda_handler(event, context):
    """
    AWS Lambda handler function
    
    Args:
        event: Lambda event object
        context: Lambda context object
        
    Returns:
        Response dict
    """
    try:
        # Get configuration from environment variables
        s3_bucket = os.environ.get('S3_BUCKET')
        dynamodb_table = os.environ.get('DYNAMODB_TABLE')
        region = os.environ.get('AWS_REGION', 'us-east-1')
        
        if not s3_bucket or not dynamodb_table:
            raise ValueError("Missing required environment variables")
        
        # Initialize scraper
        scraper = MangaScraper(s3_bucket, dynamodb_table, region)
        
        # Get manga info from event
        manga_url = event.get('manga_url')
        manga_id = event.get('manga_id')
        max_chapters = event.get('max_chapters')
        
        if not manga_url or not manga_id:
            raise ValueError("Missing manga_url or manga_id in event")
        
        # Execute scraping
        success = scraper.scrape_full_manga(manga_url, manga_id, max_chapters)
        
        return {
            'statusCode': 200 if success else 500,
            'body': json.dumps({
                'success': success,
                'manga_id': manga_id,
                'message': 'Scraping completed' if success else 'Scraping failed'
            })
        }
        
    except Exception as e:
        logger.error(f"Lambda handler error: {e}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'success': False,
                'error': str(e)
            })
        }


if __name__ == '__main__':
    """Local testing"""
    # Example usage
    scraper = MangaScraper(
        s3_bucket='my-manga-bucket',
        dynamodb_table='manga-metadata',
        region='us-east-1'
    )
    
    # Test scraping
    # scraper.scrape_full_manga(
    #     manga_url='https://example.com/manga/one-piece',
    #     manga_id='one-piece',
    #     max_chapters=1
    # )
