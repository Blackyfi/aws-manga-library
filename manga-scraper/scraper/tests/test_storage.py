"""
Storage Tests
=============

Tests for S3 and DynamoDB storage operations.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from src.storage import S3Storage, DynamoDBManager
from src.models import Manga, Chapter, Page, MangaStatus


class TestS3Storage:
    """Test cases for S3Storage"""

    @patch('boto3.client')
    def test_initialize(self, mock_boto_client):
        """Test S3Storage initialization"""
        storage = S3Storage('test-bucket', 'eu-west-3')

        assert storage.bucket_name == 'test-bucket'
        assert storage.region == 'eu-west-3'
        mock_boto_client.assert_called_once_with('s3', region_name='eu-west-3')

    @patch('boto3.client')
    def test_upload_image_success(self, mock_boto_client):
        """Test successful image upload"""
        storage = S3Storage('test-bucket')
        mock_s3 = Mock()
        mock_boto_client.return_value = mock_s3

        result = storage.upload_image(
            b'test image data',
            'test/image.webp',
            metadata={'test': 'value'}
        )

        assert result is True
        mock_s3.put_object.assert_called_once()

    @patch('boto3.client')
    def test_exists_true(self, mock_boto_client):
        """Test checking if object exists (exists)"""
        storage = S3Storage('test-bucket')
        mock_s3 = Mock()
        mock_boto_client.return_value = mock_s3
        storage.s3_client = mock_s3

        result = storage.exists('test/key')

        assert result is True
        mock_s3.head_object.assert_called_once()

    @patch('boto3.client')
    def test_exists_false(self, mock_boto_client):
        """Test checking if object exists (not exists)"""
        from botocore.exceptions import ClientError

        storage = S3Storage('test-bucket')
        mock_s3 = Mock()
        mock_boto_client.return_value = mock_s3
        storage.s3_client = mock_s3

        # Simulate 404 error
        error_response = {'Error': {'Code': '404'}}
        mock_s3.head_object.side_effect = ClientError(error_response, 'head_object')

        result = storage.exists('test/key')

        assert result is False

    @patch('boto3.client')
    def test_delete_success(self, mock_boto_client):
        """Test successful object deletion"""
        storage = S3Storage('test-bucket')
        mock_s3 = Mock()
        mock_boto_client.return_value = mock_s3
        storage.s3_client = mock_s3

        result = storage.delete('test/key')

        assert result is True
        mock_s3.delete_object.assert_called_once()

    @patch('boto3.client')
    def test_generate_presigned_url(self, mock_boto_client):
        """Test presigned URL generation"""
        storage = S3Storage('test-bucket')
        mock_s3 = Mock()
        mock_boto_client.return_value = mock_s3
        storage.s3_client = mock_s3

        mock_s3.generate_presigned_url.return_value = 'https://test-url.com'

        url = storage.generate_presigned_url('test/key', expiration=3600)

        assert url == 'https://test-url.com'
        mock_s3.generate_presigned_url.assert_called_once()

    @patch('boto3.client')
    def test_list_objects(self, mock_boto_client):
        """Test listing objects"""
        storage = S3Storage('test-bucket')
        mock_s3 = Mock()
        mock_boto_client.return_value = mock_s3
        storage.s3_client = mock_s3

        mock_s3.list_objects_v2.return_value = {
            'Contents': [
                {
                    'Key': 'test/key1',
                    'Size': 1024,
                    'LastModified': datetime.now(),
                    'ETag': '"abc123"'
                }
            ]
        }

        objects = storage.list_objects(prefix='test/')

        assert len(objects) == 1
        assert objects[0]['key'] == 'test/key1'
        assert objects[0]['size'] == 1024


class TestDynamoDBManager:
    """Test cases for DynamoDBManager"""

    @patch('boto3.resource')
    def test_initialize(self, mock_boto_resource):
        """Test DynamoDBManager initialization"""
        manager = DynamoDBManager('test-table', 'eu-west-3')

        assert manager.table_name == 'test-table'
        assert manager.region == 'eu-west-3'
        mock_boto_resource.assert_called_once_with('dynamodb', region_name='eu-west-3')

    @patch('boto3.resource')
    def test_save_manga_success(self, mock_boto_resource):
        """Test successful manga save"""
        manager = DynamoDBManager('test-table')
        mock_table = Mock()
        mock_boto_resource.return_value.Table.return_value = mock_table
        manager.table = mock_table

        manga = Manga(
            manga_id='test-manga',
            title='Test Manga',
            author='Test Author',
            description='Test description',
            status=MangaStatus.ONGOING
        )

        result = manager.save_manga(manga)

        assert result is True
        mock_table.put_item.assert_called_once()

    @patch('boto3.resource')
    def test_get_manga_exists(self, mock_boto_resource):
        """Test retrieving existing manga"""
        manager = DynamoDBManager('test-table')
        mock_table = Mock()
        mock_boto_resource.return_value.Table.return_value = mock_table
        manager.table = mock_table

        mock_table.get_item.return_value = {
            'Item': {
                'manga_id': 'test-manga',
                'title': 'Test Manga',
                'author': 'Test Author',
                'description': 'Test description',
                'status': 'ongoing',
                'genres': ['Action'],
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat(),
            }
        }

        manga = manager.get_manga('test-manga')

        assert manga is not None
        assert manga.manga_id == 'test-manga'
        assert manga.title == 'Test Manga'

    @patch('boto3.resource')
    def test_get_manga_not_exists(self, mock_boto_resource):
        """Test retrieving non-existent manga"""
        manager = DynamoDBManager('test-table')
        mock_table = Mock()
        mock_boto_resource.return_value.Table.return_value = mock_table
        manager.table = mock_table

        mock_table.get_item.return_value = {}

        manga = manager.get_manga('nonexistent')

        assert manga is None

    @patch('boto3.resource')
    def test_save_chapter_success(self, mock_boto_resource):
        """Test successful chapter save"""
        manager = DynamoDBManager('test-table')
        mock_table = Mock()
        mock_boto_resource.return_value.Table.return_value = mock_table
        manager.table = mock_table

        pages = [
            Page(page_number=1, image_url='https://example.com/page1.jpg'),
            Page(page_number=2, image_url='https://example.com/page2.jpg'),
        ]

        chapter = Chapter(
            manga_id='test-manga',
            chapter_id='test-chapter-1',
            chapter_number='1',
            chapter_title='Chapter 1',
            pages=pages
        )

        result = manager.save_chapter(chapter)

        assert result is True
        mock_table.put_item.assert_called_once()

    @patch('boto3.resource')
    def test_list_chapters(self, mock_boto_resource):
        """Test listing chapters"""
        manager = DynamoDBManager('test-table')
        mock_table = Mock()
        mock_boto_resource.return_value.Table.return_value = mock_table
        manager.table = mock_table

        mock_table.query.return_value = {
            'Items': [
                {
                    'manga_id': 'test-manga',
                    'chapter_id': 'test-chapter-1',
                    'chapter_number': '1',
                    'chapter_title': 'Chapter 1',
                    'pages': [],
                    'page_count': 0,
                    'created_at': datetime.now().isoformat(),
                    'updated_at': datetime.now().isoformat(),
                }
            ]
        }

        chapters = manager.list_chapters('test-manga')

        assert len(chapters) == 1
        assert chapters[0].chapter_number == '1'

    @patch('boto3.resource')
    def test_delete_manga_with_chapters(self, mock_boto_resource):
        """Test deleting manga with chapters"""
        manager = DynamoDBManager('test-table')
        mock_table = Mock()
        mock_boto_resource.return_value.Table.return_value = mock_table
        manager.table = mock_table

        # Mock query to return chapters
        mock_table.query.return_value = {
            'Items': [
                {'PK': 'MANGA#test', 'SK': 'CHAPTER#001'},
                {'PK': 'MANGA#test', 'SK': 'CHAPTER#002'},
            ]
        }

        # Mock batch writer
        mock_batch = MagicMock()
        mock_table.batch_writer.return_value.__enter__.return_value = mock_batch

        result = manager.delete_manga('test-manga', delete_chapters=True)

        assert result is True
        mock_table.delete_item.assert_called_once()  # For manga metadata
