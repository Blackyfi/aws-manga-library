"""
Unit tests for Manga Scraper
=============================

Comprehensive test suite for all scraper components
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from io import BytesIO
from PIL import Image
import hashlib

from manga_scraper import (
    ImageProcessor,
    RateLimiter,
    RetryHandler,
    S3Storage,
    DynamoDBManager,
    MangaScraper,
    MangaMetadata,
    ChapterData
)


class TestImageProcessor:
    """Tests for ImageProcessor class"""
    
    def test_optimize_image_reduces_size(self):
        """Test that image optimization reduces file size"""
        processor = ImageProcessor(target_size_kb=200, quality=85)
        
        # Create a test image
        img = Image.new('RGB', (800, 1200), color='red')
        original_bytes = BytesIO()
        img.save(original_bytes, format='JPEG', quality=95)
        original_data = original_bytes.getvalue()
        
        # Optimize
        optimized_data, image_hash = processor.optimize_image(original_data)
        
        # Verify optimization worked
        assert len(optimized_data) < len(original_data)
        assert isinstance(image_hash, str)
        assert len(image_hash) == 32  # MD5 hash length
    
    def test_optimize_image_converts_to_webp(self):
        """Test that images are converted to WebP format"""
        processor = ImageProcessor()
        
        # Create JPEG image
        img = Image.new('RGB', (800, 1200), color='blue')
        jpeg_bytes = BytesIO()
        img.save(jpeg_bytes, format='JPEG')
        
        optimized_data, _ = processor.optimize_image(jpeg_bytes.getvalue())
        
        # Verify WebP format
        optimized_img = Image.open(BytesIO(optimized_data))
        assert optimized_img.format == 'WEBP'
    
    def test_optimize_image_handles_rgba(self):
        """Test that RGBA images are properly converted"""
        processor = ImageProcessor()
        
        # Create RGBA image
        img = Image.new('RGBA', (800, 1200), color=(255, 0, 0, 128))
        rgba_bytes = BytesIO()
        img.save(rgba_bytes, format='PNG')
        
        # Should not raise exception
        optimized_data, _ = processor.optimize_image(rgba_bytes.getvalue())
        assert optimized_data is not None
    
    def test_create_thumbnail(self):
        """Test thumbnail creation"""
        processor = ImageProcessor()
        
        # Create test image
        img = Image.new('RGB', (800, 1200), color='green')
        img_bytes = BytesIO()
        img.save(img_bytes, format='JPEG')
        
        # Create thumbnail
        thumb_data = processor.create_thumbnail(img_bytes.getvalue(), max_width=300)
        
        # Verify thumbnail
        thumb_img = Image.open(BytesIO(thumb_data))
        assert thumb_img.width == 300
        assert thumb_img.height == 450  # Maintains aspect ratio
        assert thumb_img.format == 'WEBP'


class TestRateLimiter:
    """Tests for RateLimiter class"""
    
    def test_rate_limiter_enforces_delay(self):
        """Test that rate limiter enforces minimum delay"""
        import time
        
        limiter = RateLimiter(requests_per_second=2.0, base_delay=0.1)
        
        start_time = time.time()
        limiter.wait()
        limiter.wait()
        elapsed = time.time() - start_time
        
        # Should take at least the minimum interval + base delay
        min_expected = 0.5 + 0.1  # (1/2) + 0.1
        assert elapsed >= min_expected
    
    def test_rate_limiter_tracks_last_request(self):
        """Test that rate limiter tracks last request time"""
        limiter = RateLimiter(requests_per_second=1.0)
        
        assert limiter.last_request_time == 0
        limiter.wait()
        assert limiter.last_request_time > 0


class TestRetryHandler:
    """Tests for RetryHandler class"""
    
    def test_retry_succeeds_on_first_attempt(self):
        """Test that successful function doesn't retry"""
        handler = RetryHandler(max_retries=3)
        
        mock_func = Mock(return_value='success')
        result = handler.execute_with_retry(mock_func)
        
        assert result == 'success'
        assert mock_func.call_count == 1
    
    def test_retry_on_failure(self):
        """Test that function retries on failure"""
        handler = RetryHandler(max_retries=3, base_delay=0.1)
        
        mock_func = Mock(side_effect=[Exception('fail'), Exception('fail'), 'success'])
        result = handler.execute_with_retry(mock_func)
        
        assert result == 'success'
        assert mock_func.call_count == 3
    
    def test_retry_exhaustion(self):
        """Test that exception raised after max retries"""
        handler = RetryHandler(max_retries=3, base_delay=0.1)
        
        mock_func = Mock(side_effect=Exception('persistent failure'))
        
        with pytest.raises(Exception, match='persistent failure'):
            handler.execute_with_retry(mock_func)
        
        assert mock_func.call_count == 3


class TestS3Storage:
    """Tests for S3Storage class"""
    
    @patch('boto3.client')
    def test_upload_image_success(self, mock_boto_client):
        """Test successful image upload to S3"""
        mock_s3 = Mock()
        mock_boto_client.return_value = mock_s3
        
        storage = S3Storage('test-bucket')
        image_data = b'fake image data'
        
        result = storage.upload_image(image_data, 'test/key.webp')
        
        assert result is True
        mock_s3.put_object.assert_called_once()
        
        # Check that correct parameters were passed
        call_args = mock_s3.put_object.call_args
        assert call_args[1]['Bucket'] == 'test-bucket'
        assert call_args[1]['Key'] == 'test/key.webp'
        assert call_args[1]['ContentType'] == 'image/webp'
    
    @patch('boto3.client')
    def test_upload_image_with_metadata(self, mock_boto_client):
        """Test image upload with metadata"""
        mock_s3 = Mock()
        mock_boto_client.return_value = mock_s3
        
        storage = S3Storage('test-bucket')
        metadata = {'manga_id': 'test-manga', 'chapter': '1'}
        
        storage.upload_image(b'data', 'key.webp', metadata=metadata)
        
        call_args = mock_s3.put_object.call_args
        assert call_args[1]['Metadata'] == metadata
    
    def test_check_duplicate(self):
        """Test duplicate detection"""
        storage = S3Storage('test-bucket')
        
        test_hash = 'abc123'
        assert storage.check_duplicate(test_hash) is False
        
        storage.add_hash(test_hash)
        assert storage.check_duplicate(test_hash) is True


class TestDynamoDBManager:
    """Tests for DynamoDBManager class"""
    
    @patch('boto3.resource')
    def test_save_manga_metadata(self, mock_boto_resource):
        """Test saving manga metadata to DynamoDB"""
        mock_table = Mock()
        mock_dynamodb = Mock()
        mock_dynamodb.Table.return_value = mock_table
        mock_boto_resource.return_value = mock_dynamodb
        
        db_manager = DynamoDBManager('test-table')
        
        metadata = MangaMetadata(
            title='Test Manga',
            author='Test Author',
            genres=['Action', 'Adventure'],
            description='Test description',
            cover_url='http://example.com/cover.jpg',
            status='Ongoing',
            chapters=[]
        )
        
        result = db_manager.save_manga_metadata('test-manga-id', metadata)
        
        assert result is True
        mock_table.put_item.assert_called_once()
        
        # Verify item structure
        call_args = mock_table.put_item.call_args
        item = call_args[1]['Item']
        assert item['PK'] == 'MANGA#test-manga-id'
        assert item['SK'] == 'METADATA'
        assert item['title'] == 'Test Manga'
    
    @patch('boto3.resource')
    def test_save_chapter_metadata(self, mock_boto_resource):
        """Test saving chapter metadata to DynamoDB"""
        mock_table = Mock()
        mock_dynamodb = Mock()
        mock_dynamodb.Table.return_value = mock_table
        mock_boto_resource.return_value = mock_dynamodb
        
        db_manager = DynamoDBManager('test-table')
        
        chapter_data = ChapterData(
            manga_id='test-manga',
            chapter_number='1',
            chapter_title='Chapter 1',
            page_urls=['url1', 'url2', 'url3'],
            upload_date='2025-10-28T12:00:00'
        )
        
        result = db_manager.save_chapter_metadata(chapter_data)
        
        assert result is True
        mock_table.put_item.assert_called_once()
        
        call_args = mock_table.put_item.call_args
        item = call_args[1]['Item']
        assert item['PK'] == 'MANGA#test-manga'
        assert item['SK'] == 'CHAPTER#1'
        assert item['page_count'] == 3
    
    @patch('boto3.resource')
    def test_get_manga_metadata(self, mock_boto_resource):
        """Test retrieving manga metadata"""
        mock_table = Mock()
        mock_table.get_item.return_value = {
            'Item': {
                'manga_id': 'test-manga',
                'title': 'Test Manga'
            }
        }
        mock_dynamodb = Mock()
        mock_dynamodb.Table.return_value = mock_table
        mock_boto_resource.return_value = mock_dynamodb
        
        db_manager = DynamoDBManager('test-table')
        result = db_manager.get_manga_metadata('test-manga')
        
        assert result is not None
        assert result['manga_id'] == 'test-manga'


class TestMangaScraper:
    """Tests for MangaScraper class"""
    
    @patch('manga_scraper.S3Storage')
    @patch('manga_scraper.DynamoDBManager')
    def test_scraper_initialization(self, mock_db, mock_s3):
        """Test scraper initialization"""
        scraper = MangaScraper('test-bucket', 'test-table')
        
        assert scraper.rate_limiter is not None
        assert scraper.retry_handler is not None
        assert scraper.image_processor is not None
    
    @patch('requests.Session')
    @patch('manga_scraper.S3Storage')
    @patch('manga_scraper.DynamoDBManager')
    def test_fetch_page(self, mock_db, mock_s3, mock_session):
        """Test fetching and parsing a page"""
        mock_response = Mock()
        mock_response.content = b'<html><body><h1>Test</h1></body></html>'
        mock_response.raise_for_status = Mock()
        
        mock_session_instance = Mock()
        mock_session_instance.get.return_value = mock_response
        mock_session.return_value = mock_session_instance
        
        scraper = MangaScraper('test-bucket', 'test-table')
        scraper.session = mock_session_instance
        scraper.rate_limiter.wait = Mock()  # Skip rate limiting in test
        
        soup = scraper.fetch_page('http://example.com')
        
        assert soup is not None
        assert soup.find('h1').text == 'Test'
    
    @patch('requests.Session')
    @patch('manga_scraper.S3Storage')
    @patch('manga_scraper.DynamoDBManager')
    def test_download_image(self, mock_db, mock_s3, mock_session):
        """Test downloading an image"""
        mock_response = Mock()
        mock_response.content = b'fake image data'
        mock_response.raise_for_status = Mock()
        
        mock_session_instance = Mock()
        mock_session_instance.get.return_value = mock_response
        mock_session.return_value = mock_session_instance
        
        scraper = MangaScraper('test-bucket', 'test-table')
        scraper.session = mock_session_instance
        scraper.rate_limiter.wait = Mock()
        
        result = scraper.download_image('http://example.com/image.jpg')
        
        assert result == b'fake image data'


class TestLambdaHandler:
    """Tests for Lambda handler function"""
    
    @patch.dict('os.environ', {
        'S3_BUCKET': 'test-bucket',
        'DYNAMODB_TABLE': 'test-table',
        'AWS_REGION': 'eu-west-3'
    })
    @patch('manga_scraper.MangaScraper')
    def test_lambda_handler_success(self, mock_scraper_class):
        """Test successful Lambda execution"""
        from manga_scraper import lambda_handler
        
        mock_scraper = Mock()
        mock_scraper.scrape_full_manga.return_value = True
        mock_scraper_class.return_value = mock_scraper
        
        event = {
            'manga_url': 'http://example.com/manga/test',
            'manga_id': 'test-manga'
        }
        context = {}
        
        response = lambda_handler(event, context)
        
        assert response['statusCode'] == 200
        assert 'success' in response['body']
    
    @patch.dict('os.environ', {})
    def test_lambda_handler_missing_env_vars(self):
        """Test Lambda handler with missing environment variables"""
        from manga_scraper import lambda_handler
        
        event = {
            'manga_url': 'http://example.com/manga/test',
            'manga_id': 'test-manga'
        }
        context = {}
        
        response = lambda_handler(event, context)
        
        assert response['statusCode'] == 500
        assert 'error' in response['body']


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--cov=manga_scraper', '--cov-report=term-missing'])
