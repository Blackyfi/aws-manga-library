"""
MangaKakalot Scraper
====================

Scraper implementation for MangaKakalot.com
"""

import logging
import re
from typing import List, Optional, Dict
from datetime import datetime

from .base_scraper import BaseScraper, ScraperError
from ..models import Manga, MangaStatus

logger = logging.getLogger(__name__)


class MangaKakalotScraper(BaseScraper):
    """
    Scraper for MangaKakalot.com and related sites (Manganato, etc.)

    These sites share similar HTML structure.
    """

    def __init__(
        self,
        user_agent: str = 'MangaScraperBot/1.0 (Educational Purpose)',
        requests_per_second: float = 0.3
    ):
        """
        Initialize MangaKakalot scraper

        Args:
            user_agent: User agent string
            requests_per_second: Rate limit
        """
        super().__init__(
            base_url='https://mangakakalot.com',
            user_agent=user_agent,
            requests_per_second=requests_per_second
        )

    def get_selectors(self) -> Dict[str, str]:
        """
        Get CSS selectors for MangaKakalot

        Returns:
            Dictionary of selector names to CSS selectors
        """
        return {
            'manga_title': 'h1, h2.story-name',
            'author': 'a[href*="author"], li:contains("Author") a',
            'description': 'div#noidungm, div.panel-story-info-description',
            'cover_image': 'div.manga-info-pic img, div.story-info-left img',
            'status': 'td:contains("Status") + td, li:contains("Status")',
            'genres': 'a[href*="genre"], span.info-genres a',
            'chapters': 'div.chapter-list a, div.row-content-chapter a',
            'chapter_images': 'div.container-chapter-reader img, div.vung-doc img',
        }

    def scrape_manga_list(self, page: int = 1) -> List[str]:
        """
        Scrape list of manga URLs from MangaKakalot

        Args:
            page: Page number

        Returns:
            List of manga URLs
        """
        try:
            url = f"/manga_list?type=latest&category=all&state=all&page={page}"

            soup = self.fetch_page(url)
            manga_links = []

            # Find manga links
            for link in soup.select('a[href*="/manga/"], a[href*="/read-"]'):
                href = link.get('href')
                if href:
                    manga_url = self._make_absolute_url(href)
                    if manga_url not in manga_links:
                        manga_links.append(manga_url)

            logger.info(f"Found {len(manga_links)} manga on page {page}")
            return manga_links

        except Exception as e:
            logger.error(f"Error scraping manga list: {e}")
            return []

    def scrape_manga_details(self, manga_url: str) -> Optional[Manga]:
        """
        Scrape detailed manga information from MangaKakalot

        Args:
            manga_url: URL to manga detail page

        Returns:
            Manga object or None if scraping failed
        """
        try:
            if not self.validate_url(manga_url):
                raise ScraperError(f"Invalid MangaKakalot URL: {manga_url}")

            soup = self.fetch_page(manga_url)
            selectors = self.get_selectors()

            # Extract manga ID from URL
            manga_id = self._extract_manga_id(manga_url)

            # Extract basic info
            title = self._extract_text(soup, selectors['manga_title'])
            if not title:
                raise ScraperError("Could not extract manga title")

            # Try multiple selectors for author
            author = self._extract_text(soup, selectors['author'])
            if not author:
                # Alternative extraction
                author_elem = soup.find('td', text=re.compile('Author'))
                if author_elem:
                    author = author_elem.find_next('td').get_text(strip=True)

            # Extract description
            description = self._extract_text(soup, selectors['description'])

            # Extract cover image
            cover_url = self._extract_attribute(soup, selectors['cover_image'], 'src')

            # Extract genres
            genres = self._extract_list(soup, selectors['genres'])

            # Extract status
            status_text = self._extract_text(soup, selectors['status'], 'unknown')
            if not status_text:
                # Alternative extraction
                status_elem = soup.find('td', text=re.compile('Status'))
                if status_elem:
                    status_text = status_elem.find_next('td').get_text(strip=True)

            status = self._parse_status(status_text)

            # Extract alternative titles
            alt_titles = []
            alt_elem = soup.find('h2', class_='story-alternative')
            if alt_elem:
                alt_text = alt_elem.get_text(strip=True)
                alt_titles = [t.strip() for t in alt_text.split(';') if t.strip()]

            # Create Manga object
            manga = Manga(
                manga_id=manga_id,
                title=title,
                author=author if author else "Unknown",
                description=description,
                status=status,
                genres=genres,
                cover_url=cover_url,
                original_url=manga_url,
                alternative_titles=alt_titles,
            )

            logger.info(f"Scraped manga: {title}")
            return manga

        except Exception as e:
            logger.error(f"Error scraping manga details from {manga_url}: {e}")
            return None

    def scrape_chapter_list(self, manga_url: str) -> List[Dict[str, str]]:
        """
        Scrape list of chapters from MangaKakalot manga page

        Args:
            manga_url: URL to manga detail page

        Returns:
            List of chapter dictionaries
        """
        try:
            soup = self.fetch_page(manga_url)
            chapters = []

            # Find chapter links
            for link in soup.select('div.chapter-list a, div.row-content-chapter a'):
                chapter_url = self._make_absolute_url(link.get('href'))
                chapter_text = link.get_text(strip=True)

                # Parse chapter number and title
                chapter_number, chapter_title = self._parse_chapter_text(chapter_text)

                chapters.append({
                    'url': chapter_url,
                    'number': chapter_number,
                    'title': chapter_title,
                })

            logger.info(f"Found {len(chapters)} chapters")
            return chapters

        except Exception as e:
            logger.error(f"Error scraping chapter list: {e}")
            return []

    def scrape_chapter_pages(self, chapter_url: str) -> List[str]:
        """
        Scrape image URLs from MangaKakalot chapter page

        Args:
            chapter_url: URL to chapter reader page

        Returns:
            List of image URLs
        """
        try:
            if not self.validate_url(chapter_url):
                raise ScraperError(f"Invalid MangaKakalot URL: {chapter_url}")

            soup = self.fetch_page(chapter_url)
            selectors = self.get_selectors()

            # Extract image URLs
            image_urls = []
            for img in soup.select(selectors['chapter_images']):
                img_url = img.get('src') or img.get('data-src')
                if img_url:
                    # MangaKakalot uses full URLs
                    image_urls.append(img_url)

            logger.info(f"Found {len(image_urls)} pages in chapter")
            return image_urls

        except Exception as e:
            logger.error(f"Error scraping chapter pages: {e}")
            return []

    @staticmethod
    def _extract_manga_id(manga_url: str) -> str:
        """
        Extract manga ID from URL

        Args:
            manga_url: Manga URL

        Returns:
            Manga ID
        """
        # Try to extract ID from various URL patterns
        patterns = [
            r'/manga/([^/]+)',
            r'/read-([^/]+)',
            r'/mangakakalot/([^/]+)',
        ]

        for pattern in patterns:
            match = re.search(pattern, manga_url)
            if match:
                return match.group(1)

        # Fallback: use last part of URL
        return manga_url.rstrip('/').split('/')[-1]

    @staticmethod
    def _parse_chapter_text(text: str) -> tuple:
        """
        Parse chapter text to extract number and title

        Args:
            text: Chapter text (e.g., "Chapter 123: The Beginning")

        Returns:
            Tuple of (chapter_number, chapter_title)
        """
        # Pattern: "Chapter 123: Title" or "Ch.123 - Title"
        patterns = [
            r'Chapter\s+([0-9.]+)[\s:]+(.+)',
            r'Ch\.?\s*([0-9.]+)[\s:-]+(.+)',
            r'Chapter\s+([0-9.]+)',
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                number = match.group(1)
                title = match.group(2).strip() if len(match.groups()) > 1 else ""
                return number, title

        # Fallback: extract just numbers
        numbers = re.findall(r'[0-9.]+', text)
        if numbers:
            return numbers[0], text

        return "0", text

    @staticmethod
    def _parse_status(status_text: str) -> MangaStatus:
        """
        Parse status text to MangaStatus enum

        Args:
            status_text: Status text from website

        Returns:
            MangaStatus enum value
        """
        status_text = status_text.lower().strip()

        if 'ongoing' in status_text or 'updating' in status_text:
            return MangaStatus.ONGOING
        elif 'completed' in status_text or 'complete' in status_text:
            return MangaStatus.COMPLETED
        elif 'hiatus' in status_text:
            return MangaStatus.HIATUS
        elif 'cancelled' in status_text or 'dropped' in status_text:
            return MangaStatus.CANCELLED
        else:
            return MangaStatus.UNKNOWN
