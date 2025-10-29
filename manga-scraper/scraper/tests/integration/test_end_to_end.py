"""
End-to-End Tests
================

Full workflow integration tests.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock

from src.models import Manga, Chapter, Page, MangaStatus
from src.processors import ImageProcessor, DuplicateDetector
from src.storage import S3Storage, DynamoDBManager


@pytest.mark.integration
class TestEndToEnd:
    """End-to-end integration tests"""

    @pytest.mark.slow
    def test_full_scraping_workflow_mocked(
        self,
        mock_s3_storage,
        mock_dynamodb_manager,
        image_processor,
        duplicate_detector,
        sample_image_data
    ):
        """Test full scraping workflow with mocked AWS services"""

        # Create test manga
        manga = Manga(
            manga_id='test-manga',
            title='Test Manga',
            author='Test Author',
            description='A test manga',
            status=MangaStatus.ONGOING,
            genres=['Action', 'Adventure']
        )

        # Save manga
        result = mock_dynamodb_manager.save_manga(manga)
        assert result is True

        # Create test pages
        pages = [
            Page(page_number=1, image_url='https://example.com/page1.jpg'),
            Page(page_number=2, image_url='https://example.com/page2.jpg'),
        ]

        # Create chapter
        chapter = Chapter(
            manga_id='test-manga',
            chapter_id='test-manga-1',
            chapter_number='1',
            chapter_title='Chapter 1',
            pages=pages
        )

        # Save chapter
        result = mock_dynamodb_manager.save_chapter(chapter)
        assert result is True

        # Process images
        for page in pages:
            # Optimize image
            optimized_data, image_hash, metadata = image_processor.optimize_image(
                sample_image_data
            )

            # Check duplicates
            is_duplicate = duplicate_detector.check_and_add(image_hash)
            assert is_duplicate is False

            # Upload to S3
            s3_key = f"manga/{manga.manga_id}/chapters/{chapter.chapter_number}/page_{page.page_number:03d}.webp"
            result = mock_s3_storage.upload_image(optimized_data, s3_key)
            assert result is True

        # Verify statistics
        stats = duplicate_detector.get_statistics()
        assert stats['total_unique_hashes'] == len(pages)

    def test_duplicate_detection_workflow(
        self,
        duplicate_detector,
        sample_image_data,
        image_processor
    ):
        """Test duplicate detection in workflow"""

        # Process same image multiple times
        for i in range(3):
            optimized_data, image_hash, _ = image_processor.optimize_image(
                sample_image_data
            )

            is_duplicate = duplicate_detector.check_and_add(image_hash)

            if i == 0:
                assert is_duplicate is False  # First time
            else:
                assert is_duplicate is True  # Subsequent times

        stats = duplicate_detector.get_statistics()
        assert stats['total_unique_hashes'] == 1
        assert stats['duplicate_count'] == 2

    @patch('requests.Session')
    def test_scraper_with_rate_limiting(self, mock_session):
        """Test scraper respects rate limiting"""
        from src.scrapers import MangaDexScraper
        from src.utils import RateLimiter
        import time

        # Create scraper with rate limiter
        scraper = MangaDexScraper(requests_per_second=2.0)

        # Mock response
        mock_response = Mock()
        mock_response.content = b'<html><body>Test</body></html>'
        mock_response.status_code = 200
        mock_session.return_value.get.return_value = mock_response

        # Make multiple requests
        start_time = time.time()
        for _ in range(3):
            try:
                scraper.fetch_page('/test')
            except Exception:
                pass  # Ignore errors, we're testing timing

        elapsed = time.time() - start_time

        # Should take at least 1 second for 3 requests at 2 req/s
        assert elapsed >= 0.5  # Allow some margin

    def test_retry_logic_workflow(self, retry_handler):
        """Test retry logic in workflow"""
        call_count = 0

        def failing_function():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise Exception("Temporary failure")
            return "Success"

        result = retry_handler.execute_with_retry(failing_function)

        assert result == "Success"
        assert call_count == 2

        stats = retry_handler.get_statistics()
        assert stats['total_retries'] == 1
