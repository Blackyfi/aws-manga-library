"""
AWS Integration Tests
=====================

Tests requiring actual AWS services.
"""

import pytest
import os
from datetime import datetime

from src.storage import S3Storage, DynamoDBManager
from src.models import Manga, Chapter, Page, MangaStatus


@pytest.mark.aws
@pytest.mark.integration
class TestAWSIntegration:
    """
    AWS integration tests

    Note: These tests require valid AWS credentials and will
    create actual resources. Use only in test environments.
    """

    @pytest.fixture
    def test_s3_bucket(self):
        """Get test S3 bucket name from environment"""
        bucket = os.environ.get('TEST_S3_BUCKET')
        if not bucket:
            pytest.skip("TEST_S3_BUCKET not set")
        return bucket

    @pytest.fixture
    def test_dynamodb_table(self):
        """Get test DynamoDB table name from environment"""
        table = os.environ.get('TEST_DYNAMODB_TABLE')
        if not table:
            pytest.skip("TEST_DYNAMODB_TABLE not set")
        return table

    def test_s3_upload_and_download(self, test_s3_bucket):
        """Test actual S3 upload and download"""
        storage = S3Storage(test_s3_bucket)

        test_key = f"test/integration-test-{datetime.now().timestamp()}.txt"
        test_data = b"Test data for integration test"

        try:
            # Upload
            result = storage.upload_image(test_data, test_key)
            assert result is True

            # Check exists
            exists = storage.exists(test_key)
            assert exists is True

            # Download
            downloaded_data = storage.get_object(test_key)
            assert downloaded_data == test_data

        finally:
            # Cleanup
            storage.delete(test_key)

    def test_dynamodb_save_and_retrieve(self, test_dynamodb_table):
        """Test actual DynamoDB save and retrieve"""
        manager = DynamoDBManager(test_dynamodb_table)

        test_manga = Manga(
            manga_id=f'test-{datetime.now().timestamp()}',
            title='Integration Test Manga',
            author='Test Author',
            description='Test description',
            status=MangaStatus.ONGOING
        )

        try:
            # Save
            result = manager.save_manga(test_manga)
            assert result is True

            # Retrieve
            retrieved_manga = manager.get_manga(test_manga.manga_id)
            assert retrieved_manga is not None
            assert retrieved_manga.title == test_manga.title
            assert retrieved_manga.author == test_manga.author

        finally:
            # Cleanup
            manager.delete_manga(test_manga.manga_id, delete_chapters=False)

    def test_dynamodb_chapter_operations(self, test_dynamodb_table):
        """Test chapter save and list operations"""
        manager = DynamoDBManager(test_dynamodb_table)

        manga_id = f'test-manga-{datetime.now().timestamp()}'

        # Create test chapters
        chapters = []
        for i in range(1, 4):
            pages = [
                Page(page_number=j, image_url=f'https://example.com/page{j}.jpg')
                for j in range(1, 6)
            ]

            chapter = Chapter(
                manga_id=manga_id,
                chapter_id=f'{manga_id}-{i}',
                chapter_number=str(i),
                chapter_title=f'Chapter {i}',
                pages=pages
            )
            chapters.append(chapter)

        try:
            # Save chapters
            for chapter in chapters:
                result = manager.save_chapter(chapter)
                assert result is True

            # List chapters
            retrieved_chapters = manager.list_chapters(manga_id)
            assert len(retrieved_chapters) == 3

            # Verify order (should be sorted by chapter number)
            for i, chapter in enumerate(retrieved_chapters):
                assert chapter.chapter_number == str(i + 1)

        finally:
            # Cleanup
            manager.delete_manga(manga_id, delete_chapters=True)

    @pytest.mark.slow
    def test_full_aws_workflow(self, test_s3_bucket, test_dynamodb_table, sample_image_data):
        """Test complete workflow with real AWS services"""
        from src.processors import ImageProcessor

        storage = S3Storage(test_s3_bucket)
        db_manager = DynamoDBManager(test_dynamodb_table)
        processor = ImageProcessor()

        manga_id = f'test-{datetime.now().timestamp()}'

        try:
            # Create and save manga
            manga = Manga(
                manga_id=manga_id,
                title='Full Workflow Test',
                author='Test Author',
                description='Testing full workflow',
                status=MangaStatus.ONGOING
            )

            assert db_manager.save_manga(manga) is True

            # Process and upload image
            optimized_data, image_hash, _ = processor.optimize_image(sample_image_data)

            s3_key = f"manga/{manga_id}/cover.webp"
            assert storage.upload_image(optimized_data, s3_key) is True

            # Create and save chapter
            pages = [Page(page_number=1, image_url='https://example.com/page1.jpg')]
            chapter = Chapter(
                manga_id=manga_id,
                chapter_id=f'{manga_id}-1',
                chapter_number='1',
                chapter_title='Chapter 1',
                pages=pages
            )

            assert db_manager.save_chapter(chapter) is True

            # Verify everything exists
            assert storage.exists(s3_key) is True
            assert db_manager.get_manga(manga_id) is not None
            assert len(db_manager.list_chapters(manga_id)) == 1

        finally:
            # Cleanup
            storage.delete(s3_key)
            db_manager.delete_manga(manga_id, delete_chapters=True)
