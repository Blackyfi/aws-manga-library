"""
DynamoDB Manager
================

Handles DynamoDB operations for metadata storage.
"""

import logging
from typing import Optional, Dict, Any, List
from datetime import datetime
from decimal import Decimal

import boto3
from boto3.dynamodb.conditions import Key, Attr
from botocore.exceptions import ClientError, BotoCoreError

from ..models import Manga, Chapter

logger = logging.getLogger(__name__)


class DynamoDBManager:
    """
    Handles DynamoDB operations for manga metadata

    Table Schema:
    - PK: Partition key (MANGA#{manga_id})
    - SK: Sort key (METADATA or CHAPTER#{chapter_number})

    Features:
    - Save/retrieve manga metadata
    - Save/retrieve chapter metadata
    - Query chapters by manga
    - Batch operations
    - Pagination support
    """

    def __init__(self, table_name: str, region: str = 'eu-west-3'):
        """
        Initialize DynamoDB manager

        Args:
            table_name: DynamoDB table name
            region: AWS region
        """
        self.table_name = table_name
        self.region = region

        # Initialize DynamoDB resources
        self.dynamodb = boto3.resource('dynamodb', region_name=region)
        self.table = self.dynamodb.Table(table_name)

        logger.info(f"Initialized DynamoDBManager for table: {table_name}")

    def save_manga(self, manga: Manga) -> bool:
        """
        Save manga metadata to DynamoDB

        Args:
            manga: Manga object

        Returns:
            True if successful
        """
        try:
            item = {
                'PK': f'MANGA#{manga.manga_id}',
                'SK': 'METADATA',
                'entity_type': 'manga',
                'manga_id': manga.manga_id,
                'title': manga.title,
                'author': manga.author,
                'artist': manga.artist,
                'description': manga.description,
                'status': manga.status.value,
                'genres': manga.genres,
                'tags': manga.tags,
                'cover_url': manga.cover_url,
                'original_url': manga.original_url,
                'alternative_titles': manga.alternative_titles,
                'year_released': manga.year_released,
                'rating': Decimal(str(manga.rating)) if manga.rating else None,
                'views': manga.views,
                'created_at': manga.created_at.isoformat(),
                'updated_at': manga.updated_at.isoformat(),
            }

            # Remove None values
            item = {k: v for k, v in item.items() if v is not None}

            self.table.put_item(Item=item)

            logger.info(f"Saved manga metadata: {manga.manga_id}")
            return True

        except (ClientError, BotoCoreError) as e:
            logger.error(f"Error saving manga to DynamoDB: {e}")
            return False

    def get_manga(self, manga_id: str) -> Optional[Manga]:
        """
        Retrieve manga metadata from DynamoDB

        Args:
            manga_id: Unique manga identifier

        Returns:
            Manga object or None if not found
        """
        try:
            response = self.table.get_item(
                Key={
                    'PK': f'MANGA#{manga_id}',
                    'SK': 'METADATA'
                }
            )

            item = response.get('Item')
            if not item:
                logger.warning(f"Manga not found: {manga_id}")
                return None

            # Convert DynamoDB item to Manga object
            return self._item_to_manga(item)

        except (ClientError, BotoCoreError) as e:
            logger.error(f"Error retrieving manga from DynamoDB: {e}")
            return None

    def save_chapter(self, chapter: Chapter) -> bool:
        """
        Save chapter metadata to DynamoDB

        Args:
            chapter: Chapter object

        Returns:
            True if successful
        """
        try:
            item = {
                'PK': f'MANGA#{chapter.manga_id}',
                'SK': f'CHAPTER#{chapter.chapter_number.zfill(10)}',  # Zero-pad for sorting
                'entity_type': 'chapter',
                'manga_id': chapter.manga_id,
                'chapter_id': chapter.chapter_id,
                'chapter_number': chapter.chapter_number,
                'chapter_title': chapter.chapter_title,
                'volume': chapter.volume,
                'page_count': chapter.page_count,
                'pages': [page.to_dict() for page in chapter.pages],
                'upload_date': chapter.upload_date.isoformat() if chapter.upload_date else None,
                'scanlation_group': chapter.scanlation_group,
                'language': chapter.language,
                'original_url': chapter.original_url,
                'created_at': chapter.created_at.isoformat(),
                'updated_at': chapter.updated_at.isoformat(),
            }

            # Remove None values
            item = {k: v for k, v in item.items() if v is not None}

            self.table.put_item(Item=item)

            logger.info(f"Saved chapter metadata: {chapter.manga_id} - {chapter.chapter_number}")
            return True

        except (ClientError, BotoCoreError) as e:
            logger.error(f"Error saving chapter to DynamoDB: {e}")
            return False

    def get_chapter(self, manga_id: str, chapter_number: str) -> Optional[Chapter]:
        """
        Retrieve chapter metadata from DynamoDB

        Args:
            manga_id: Manga identifier
            chapter_number: Chapter number

        Returns:
            Chapter object or None if not found
        """
        try:
            response = self.table.get_item(
                Key={
                    'PK': f'MANGA#{manga_id}',
                    'SK': f'CHAPTER#{chapter_number.zfill(10)}'
                }
            )

            item = response.get('Item')
            if not item:
                logger.warning(f"Chapter not found: {manga_id} - {chapter_number}")
                return None

            # Convert DynamoDB item to Chapter object
            return self._item_to_chapter(item)

        except (ClientError, BotoCoreError) as e:
            logger.error(f"Error retrieving chapter from DynamoDB: {e}")
            return None

    def list_chapters(
        self,
        manga_id: str,
        limit: Optional[int] = None
    ) -> List[Chapter]:
        """
        List all chapters for a manga

        Args:
            manga_id: Manga identifier
            limit: Optional limit on number of chapters

        Returns:
            List of Chapter objects
        """
        try:
            query_kwargs = {
                'KeyConditionExpression': Key('PK').eq(f'MANGA#{manga_id}') &
                                        Key('SK').begins_with('CHAPTER#')
            }

            if limit:
                query_kwargs['Limit'] = limit

            response = self.table.query(**query_kwargs)

            chapters = []
            for item in response.get('Items', []):
                chapter = self._item_to_chapter(item)
                if chapter:
                    chapters.append(chapter)

            logger.info(f"Retrieved {len(chapters)} chapters for manga: {manga_id}")
            return chapters

        except (ClientError, BotoCoreError) as e:
            logger.error(f"Error listing chapters from DynamoDB: {e}")
            return []

    def delete_manga(self, manga_id: str, delete_chapters: bool = True) -> bool:
        """
        Delete manga and optionally all its chapters

        Args:
            manga_id: Manga identifier
            delete_chapters: Whether to delete associated chapters

        Returns:
            True if successful
        """
        try:
            # Delete manga metadata
            self.table.delete_item(
                Key={
                    'PK': f'MANGA#{manga_id}',
                    'SK': 'METADATA'
                }
            )

            if delete_chapters:
                # Query and delete all chapters
                response = self.table.query(
                    KeyConditionExpression=Key('PK').eq(f'MANGA#{manga_id}') &
                                          Key('SK').begins_with('CHAPTER#')
                )

                # Batch delete chapters
                with self.table.batch_writer() as batch:
                    for item in response.get('Items', []):
                        batch.delete_item(
                            Key={
                                'PK': item['PK'],
                                'SK': item['SK']
                            }
                        )

            logger.info(f"Deleted manga: {manga_id}")
            return True

        except (ClientError, BotoCoreError) as e:
            logger.error(f"Error deleting manga from DynamoDB: {e}")
            return False

    def delete_chapter(self, manga_id: str, chapter_number: str) -> bool:
        """
        Delete specific chapter

        Args:
            manga_id: Manga identifier
            chapter_number: Chapter number

        Returns:
            True if successful
        """
        try:
            self.table.delete_item(
                Key={
                    'PK': f'MANGA#{manga_id}',
                    'SK': f'CHAPTER#{chapter_number.zfill(10)}'
                }
            )

            logger.info(f"Deleted chapter: {manga_id} - {chapter_number}")
            return True

        except (ClientError, BotoCoreError) as e:
            logger.error(f"Error deleting chapter from DynamoDB: {e}")
            return False

    def search_manga(
        self,
        title: Optional[str] = None,
        author: Optional[str] = None,
        genre: Optional[str] = None,
        limit: int = 50
    ) -> List[Manga]:
        """
        Search manga by various criteria

        Note: This uses scan which is expensive. For production, use GSI with proper indexes.

        Args:
            title: Search by title (partial match)
            author: Search by author (partial match)
            genre: Search by genre (exact match)
            limit: Maximum results

        Returns:
            List of Manga objects
        """
        try:
            filter_expression = Attr('entity_type').eq('manga')

            if title:
                filter_expression &= Attr('title').contains(title)

            if author:
                filter_expression &= Attr('author').contains(author)

            if genre:
                filter_expression &= Attr('genres').contains(genre)

            response = self.table.scan(
                FilterExpression=filter_expression,
                Limit=limit
            )

            mangas = []
            for item in response.get('Items', []):
                manga = self._item_to_manga(item)
                if manga:
                    mangas.append(manga)

            logger.info(f"Search found {len(mangas)} manga")
            return mangas

        except (ClientError, BotoCoreError) as e:
            logger.error(f"Error searching manga in DynamoDB: {e}")
            return []

    def batch_save_chapters(self, chapters: List[Chapter]) -> int:
        """
        Save multiple chapters in batch

        Args:
            chapters: List of Chapter objects

        Returns:
            Number of successfully saved chapters
        """
        if not chapters:
            return 0

        try:
            saved_count = 0

            with self.table.batch_writer() as batch:
                for chapter in chapters:
                    item = {
                        'PK': f'MANGA#{chapter.manga_id}',
                        'SK': f'CHAPTER#{chapter.chapter_number.zfill(10)}',
                        'entity_type': 'chapter',
                        'manga_id': chapter.manga_id,
                        'chapter_id': chapter.chapter_id,
                        'chapter_number': chapter.chapter_number,
                        'chapter_title': chapter.chapter_title,
                        'volume': chapter.volume,
                        'page_count': chapter.page_count,
                        'pages': [page.to_dict() for page in chapter.pages],
                        'upload_date': chapter.upload_date.isoformat() if chapter.upload_date else None,
                        'scanlation_group': chapter.scanlation_group,
                        'language': chapter.language,
                        'original_url': chapter.original_url,
                        'created_at': chapter.created_at.isoformat(),
                        'updated_at': chapter.updated_at.isoformat(),
                    }

                    # Remove None values
                    item = {k: v for k, v in item.items() if v is not None}

                    batch.put_item(Item=item)
                    saved_count += 1

            logger.info(f"Batch saved {saved_count} chapters")
            return saved_count

        except (ClientError, BotoCoreError) as e:
            logger.error(f"Error batch saving chapters: {e}")
            return 0

    @staticmethod
    def _item_to_manga(item: Dict[str, Any]) -> Optional[Manga]:
        """
        Convert DynamoDB item to Manga object

        Args:
            item: DynamoDB item

        Returns:
            Manga object or None
        """
        try:
            return Manga.from_dict({
                'manga_id': item['manga_id'],
                'title': item['title'],
                'author': item.get('author', 'Unknown'),
                'artist': item.get('artist'),
                'description': item.get('description', ''),
                'status': item.get('status', 'unknown'),
                'genres': item.get('genres', []),
                'tags': item.get('tags', []),
                'cover_url': item.get('cover_url'),
                'original_url': item.get('original_url'),
                'alternative_titles': item.get('alternative_titles', []),
                'year_released': item.get('year_released'),
                'rating': float(item['rating']) if item.get('rating') else None,
                'views': item.get('views', 0),
                'created_at': item.get('created_at'),
                'updated_at': item.get('updated_at'),
            })
        except Exception as e:
            logger.error(f"Error converting item to Manga: {e}")
            return None

    @staticmethod
    def _item_to_chapter(item: Dict[str, Any]) -> Optional[Chapter]:
        """
        Convert DynamoDB item to Chapter object

        Args:
            item: DynamoDB item

        Returns:
            Chapter object or None
        """
        try:
            return Chapter.from_dict({
                'manga_id': item['manga_id'],
                'chapter_id': item['chapter_id'],
                'chapter_number': item['chapter_number'],
                'chapter_title': item['chapter_title'],
                'volume': item.get('volume'),
                'pages': item.get('pages', []),
                'page_count': item.get('page_count', 0),
                'upload_date': item.get('upload_date'),
                'scanlation_group': item.get('scanlation_group'),
                'language': item.get('language', 'en'),
                'original_url': item.get('original_url'),
                'created_at': item.get('created_at'),
                'updated_at': item.get('updated_at'),
            })
        except Exception as e:
            logger.error(f"Error converting item to Chapter: {e}")
            return None
