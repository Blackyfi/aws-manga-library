"""
Chapter Data Models
===================

Data classes and models for chapter information.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Dict, Any


@dataclass
class Page:
    """
    Individual page data model

    Attributes:
        page_number: Page number in chapter
        image_url: Original image URL
        s3_key: S3 storage key
        thumbnail_key: S3 key for thumbnail
        image_hash: MD5 hash for duplicate detection
        width: Image width in pixels
        height: Image height in pixels
        size_bytes: File size in bytes
    """
    page_number: int
    image_url: str
    s3_key: Optional[str] = None
    thumbnail_key: Optional[str] = None
    image_hash: Optional[str] = None
    width: Optional[int] = None
    height: Optional[int] = None
    size_bytes: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert page to dictionary

        Returns:
            Dictionary representation
        """
        return {
            'page_number': self.page_number,
            'image_url': self.image_url,
            's3_key': self.s3_key,
            'thumbnail_key': self.thumbnail_key,
            'image_hash': self.image_hash,
            'width': self.width,
            'height': self.height,
            'size_bytes': self.size_bytes,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Page':
        """
        Create page from dictionary

        Args:
            data: Dictionary with page data

        Returns:
            Page instance
        """
        return cls(
            page_number=data['page_number'],
            image_url=data['image_url'],
            s3_key=data.get('s3_key'),
            thumbnail_key=data.get('thumbnail_key'),
            image_hash=data.get('image_hash'),
            width=data.get('width'),
            height=data.get('height'),
            size_bytes=data.get('size_bytes'),
        )


@dataclass
class Chapter:
    """
    Chapter data model

    Attributes:
        manga_id: Associated manga identifier
        chapter_id: Unique chapter identifier
        chapter_number: Chapter number (can be decimal like 5.5)
        chapter_title: Chapter title
        volume: Volume number
        pages: List of page objects
        page_count: Number of pages
        upload_date: When chapter was uploaded
        scanlation_group: Translation group
        language: Chapter language
        original_url: Source URL
        created_at: When record was created
        updated_at: When record was last updated
    """
    manga_id: str
    chapter_id: str
    chapter_number: str
    chapter_title: str
    pages: List[Page] = field(default_factory=list)
    page_count: int = 0
    volume: Optional[str] = None
    upload_date: Optional[datetime] = None
    scanlation_group: Optional[str] = None
    language: str = "en"
    original_url: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def __post_init__(self):
        """Update page_count after initialization"""
        if not self.page_count and self.pages:
            self.page_count = len(self.pages)

    def add_page(self, page: Page) -> None:
        """
        Add a page to the chapter

        Args:
            page: Page object to add
        """
        self.pages.append(page)
        self.page_count = len(self.pages)
        self.update_timestamp()

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert chapter to dictionary for storage

        Returns:
            Dictionary representation
        """
        return {
            'manga_id': self.manga_id,
            'chapter_id': self.chapter_id,
            'chapter_number': self.chapter_number,
            'chapter_title': self.chapter_title,
            'volume': self.volume,
            'pages': [page.to_dict() for page in self.pages],
            'page_count': self.page_count,
            'upload_date': self.upload_date.isoformat() if self.upload_date else None,
            'scanlation_group': self.scanlation_group,
            'language': self.language,
            'original_url': self.original_url,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Chapter':
        """
        Create chapter from dictionary

        Args:
            data: Dictionary with chapter data

        Returns:
            Chapter instance
        """
        # Parse pages
        pages = [Page.from_dict(p) for p in data.get('pages', [])]

        # Parse datetimes
        upload_date = data.get('upload_date')
        if isinstance(upload_date, str):
            upload_date = datetime.fromisoformat(upload_date)

        created_at = data.get('created_at')
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)
        elif created_at is None:
            created_at = datetime.utcnow()

        updated_at = data.get('updated_at')
        if isinstance(updated_at, str):
            updated_at = datetime.fromisoformat(updated_at)
        elif updated_at is None:
            updated_at = datetime.utcnow()

        return cls(
            manga_id=data['manga_id'],
            chapter_id=data['chapter_id'],
            chapter_number=data['chapter_number'],
            chapter_title=data['chapter_title'],
            volume=data.get('volume'),
            pages=pages,
            page_count=data.get('page_count', len(pages)),
            upload_date=upload_date,
            scanlation_group=data.get('scanlation_group'),
            language=data.get('language', 'en'),
            original_url=data.get('original_url'),
            created_at=created_at,
            updated_at=updated_at,
        )

    def update_timestamp(self) -> None:
        """Update the updated_at timestamp to current time"""
        self.updated_at = datetime.utcnow()

    def get_page(self, page_number: int) -> Optional[Page]:
        """
        Get specific page by number

        Args:
            page_number: Page number to retrieve

        Returns:
            Page object or None if not found
        """
        for page in self.pages:
            if page.page_number == page_number:
                return page
        return None


@dataclass
class ChapterMetadata:
    """
    Simplified chapter metadata for scraping

    This is a lighter version used during the scraping process
    """
    manga_id: str
    chapter_number: str
    chapter_title: str
    page_urls: List[str]
    upload_date: str

    def to_chapter(self, chapter_id: str, original_url: Optional[str] = None) -> Chapter:
        """
        Convert to full Chapter model

        Args:
            chapter_id: Unique chapter identifier
            original_url: Source URL

        Returns:
            Chapter instance
        """
        # Create pages from URLs
        pages = [
            Page(page_number=i, image_url=url)
            for i, url in enumerate(self.page_urls, 1)
        ]

        # Parse upload date
        try:
            upload_dt = datetime.fromisoformat(self.upload_date)
        except (ValueError, AttributeError):
            upload_dt = None

        return Chapter(
            manga_id=self.manga_id,
            chapter_id=chapter_id,
            chapter_number=self.chapter_number,
            chapter_title=self.chapter_title,
            pages=pages,
            page_count=len(pages),
            upload_date=upload_dt,
            original_url=original_url,
        )
