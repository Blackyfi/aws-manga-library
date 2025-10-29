"""
Pytest Configuration
====================

Shared fixtures and configuration for tests.
"""

import pytest
import os
import sys
from typing import Generator
from unittest.mock import Mock, MagicMock

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.config import ScraperConfig
from src.processors import ImageProcessor, DuplicateDetector
from src.storage import S3Storage, DynamoDBManager
from src.utils import RateLimiter, RetryHandler


@pytest.fixture
def test_config() -> ScraperConfig:
    """
    Provide test configuration

    Returns:
        ScraperConfig instance for testing
    """
    return ScraperConfig(
        s3_bucket='test-manga-bucket',
        dynamodb_table='test-manga-metadata',
        aws_region='eu-west-3',
        requests_per_second=10.0,  # Faster for tests
        max_retries=2,  # Fewer retries for tests
        target_image_size_kb=100,
        webp_quality=80,
    )


@pytest.fixture
def image_processor() -> ImageProcessor:
    """
    Provide image processor for testing

    Returns:
        ImageProcessor instance
    """
    return ImageProcessor(
        target_size_kb=100,
        webp_quality=80,
        thumbnail_max_width=200,
        thumbnail_quality=60
    )


@pytest.fixture
def duplicate_detector() -> DuplicateDetector:
    """
    Provide duplicate detector for testing

    Returns:
        DuplicateDetector instance
    """
    return DuplicateDetector(enable_perceptual_hashing=True)


@pytest.fixture
def rate_limiter() -> RateLimiter:
    """
    Provide rate limiter for testing

    Returns:
        RateLimiter instance with fast settings
    """
    return RateLimiter(requests_per_second=10.0, base_delay=0.0)


@pytest.fixture
def retry_handler() -> RetryHandler:
    """
    Provide retry handler for testing

    Returns:
        RetryHandler instance
    """
    return RetryHandler(max_retries=2, base_delay=0.1, max_delay=1.0)


@pytest.fixture
def mock_s3_storage() -> Mock:
    """
    Provide mocked S3 storage

    Returns:
        Mocked S3Storage instance
    """
    mock_storage = Mock(spec=S3Storage)
    mock_storage.bucket_name = 'test-bucket'
    mock_storage.upload_image.return_value = True
    mock_storage.exists.return_value = False
    mock_storage.delete.return_value = True
    mock_storage.get_object.return_value = b'test data'
    return mock_storage


@pytest.fixture
def mock_dynamodb_manager() -> Mock:
    """
    Provide mocked DynamoDB manager

    Returns:
        Mocked DynamoDBManager instance
    """
    mock_db = Mock(spec=DynamoDBManager)
    mock_db.table_name = 'test-table'
    mock_db.save_manga.return_value = True
    mock_db.save_chapter.return_value = True
    mock_db.get_manga.return_value = None
    mock_db.get_chapter.return_value = None
    mock_db.list_chapters.return_value = []
    return mock_db


@pytest.fixture
def sample_image_data() -> bytes:
    """
    Provide sample image data for testing

    Returns:
        Sample PNG image as bytes
    """
    from PIL import Image
    from io import BytesIO

    # Create a simple test image
    img = Image.new('RGB', (100, 100), color='red')
    buffer = BytesIO()
    img.save(buffer, format='PNG')
    return buffer.getvalue()


@pytest.fixture
def sample_html() -> str:
    """
    Provide sample HTML for scraping tests

    Returns:
        Sample HTML string
    """
    return """
    <html>
        <head><title>Test Manga</title></head>
        <body>
            <h1 class="manga-title">Test Manga Title</h1>
            <span class="author">Test Author</span>
            <div class="description">Test description</div>
            <img class="cover" src="https://example.com/cover.jpg" />
            <span class="genre">Action</span>
            <span class="genre">Adventure</span>
            <a class="chapter-link" href="/chapter/1" data-chapter="1">Chapter 1</a>
            <a class="chapter-link" href="/chapter/2" data-chapter="2">Chapter 2</a>
        </body>
    </html>
    """


@pytest.fixture
def sample_chapter_html() -> str:
    """
    Provide sample chapter HTML

    Returns:
        Sample chapter HTML string
    """
    return """
    <html>
        <body>
            <img class="chapter-image" src="https://example.com/page1.jpg" />
            <img class="chapter-image" src="https://example.com/page2.jpg" />
            <img class="chapter-image" src="https://example.com/page3.jpg" />
        </body>
    </html>
    """


@pytest.fixture(autouse=True)
def reset_environment():
    """
    Reset environment variables before each test

    Yields:
        None
    """
    # Store original environment
    original_env = os.environ.copy()

    # Set test environment variables
    os.environ['S3_BUCKET'] = 'test-bucket'
    os.environ['DYNAMODB_TABLE'] = 'test-table'
    os.environ['AWS_REGION'] = 'eu-west-3'
    os.environ['LOG_LEVEL'] = 'DEBUG'

    yield

    # Restore original environment
    os.environ.clear()
    os.environ.update(original_env)


@pytest.fixture
def temp_directory(tmp_path) -> Generator:
    """
    Provide temporary directory for file operations

    Args:
        tmp_path: Pytest temporary path fixture

    Yields:
        Path to temporary directory
    """
    yield tmp_path


# Pytest configuration
def pytest_configure(config):
    """Configure pytest with custom markers"""
    config.addinivalue_line(
        "markers", "integration: mark test as integration test (may be slow)"
    )
    config.addinivalue_line(
        "markers", "aws: mark test as requiring AWS credentials"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )
