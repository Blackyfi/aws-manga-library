"""
Manga Data Models
=================

Data classes and models for manga information.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List, Optional, Dict, Any


class MangaStatus(Enum):
    """Enum for manga publication status"""
    ONGOING = "ongoing"
    COMPLETED = "completed"
    HIATUS = "hiatus"
    CANCELLED = "cancelled"
    UNKNOWN = "unknown"


@dataclass
class Manga:
    """
    Core manga data model

    Attributes:
        manga_id: Unique identifier for the manga
        title: Manga title
        author: Author name(s)
        artist: Artist name(s)
        description: Synopsis or description
        status: Publication status
        genres: List of genres
        tags: Additional tags
        cover_url: URL to cover image
        original_url: Source URL
        alternative_titles: Alternative names
        year_released: Year of first publication
        rating: Average rating (0-10)
        views: View count
        created_at: When record was created
        updated_at: When record was last updated
    """
    manga_id: str
    title: str
    author: str
    description: str
    status: MangaStatus = MangaStatus.UNKNOWN
    genres: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    cover_url: Optional[str] = None
    original_url: Optional[str] = None
    artist: Optional[str] = None
    alternative_titles: List[str] = field(default_factory=list)
    year_released: Optional[int] = None
    rating: Optional[float] = None
    views: int = 0
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert manga to dictionary for storage

        Returns:
            Dictionary representation
        """
        return {
            'manga_id': self.manga_id,
            'title': self.title,
            'author': self.author,
            'artist': self.artist,
            'description': self.description,
            'status': self.status.value,
            'genres': self.genres,
            'tags': self.tags,
            'cover_url': self.cover_url,
            'original_url': self.original_url,
            'alternative_titles': self.alternative_titles,
            'year_released': self.year_released,
            'rating': self.rating,
            'views': self.views,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Manga':
        """
        Create manga from dictionary

        Args:
            data: Dictionary with manga data

        Returns:
            Manga instance
        """
        # Parse status
        status_str = data.get('status', 'unknown')
        try:
            status = MangaStatus(status_str)
        except ValueError:
            status = MangaStatus.UNKNOWN

        # Parse datetimes
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
            title=data['title'],
            author=data['author'],
            artist=data.get('artist'),
            description=data['description'],
            status=status,
            genres=data.get('genres', []),
            tags=data.get('tags', []),
            cover_url=data.get('cover_url'),
            original_url=data.get('original_url'),
            alternative_titles=data.get('alternative_titles', []),
            year_released=data.get('year_released'),
            rating=data.get('rating'),
            views=data.get('views', 0),
            created_at=created_at,
            updated_at=updated_at,
        )

    def update_timestamp(self) -> None:
        """Update the updated_at timestamp to current time"""
        self.updated_at = datetime.utcnow()


@dataclass
class MangaMetadata:
    """
    Simplified manga metadata for scraping

    This is a lighter version used during the scraping process
    """
    title: str
    author: str
    description: str
    genres: List[str]
    cover_url: str
    status: str
    chapters: List[Dict[str, Any]] = field(default_factory=list)

    def to_manga(self, manga_id: str, original_url: str) -> Manga:
        """
        Convert to full Manga model

        Args:
            manga_id: Unique manga identifier
            original_url: Source URL

        Returns:
            Manga instance
        """
        # Parse status
        try:
            status = MangaStatus(self.status.lower())
        except (ValueError, AttributeError):
            status = MangaStatus.UNKNOWN

        return Manga(
            manga_id=manga_id,
            title=self.title,
            author=self.author,
            description=self.description,
            status=status,
            genres=self.genres,
            cover_url=self.cover_url,
            original_url=original_url,
        )
