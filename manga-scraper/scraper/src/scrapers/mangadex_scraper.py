"""
MangaDex Scraper
================

Scraper implementation for MangaDex.org
"""

import logging
from typing import List, Optional, Dict
from datetime import datetime

from .base_scraper import BaseScraper, ScraperError
from ..models import Manga, MangaStatus

logger = logging.getLogger(__name__)


class MangaDexScraper(BaseScraper):
    """
    Scraper for MangaDex.org

    Note: MangaDex provides an official API. This implementation demonstrates
    HTML scraping, but for production use, the official API is recommended.

    API Documentation: https://api.mangadex.org/docs/
    """

    def __init__(
        self,
        user_agent: str = 'MangaScraperBot/1.0 (Educational Purpose)',
        requests_per_second: float = 0.5
    ):
        """
        Initialize MangaDex scraper

        Args:
            user_agent: User agent string
            requests_per_second: Rate limit (MangaDex has strict rate limits)
        """
        super().__init__(
            base_url='https://mangadex.org',
            user_agent=user_agent,
            requests_per_second=requests_per_second
        )

    def get_selectors(self) -> Dict[str, str]:
        """
        Get CSS selectors for MangaDex

        Returns:
            Dictionary of selector names to CSS selectors

        Note: These selectors may need updating as the site changes
        """
        return {
            'manga_title': 'h1.text-3xl',
            'author': 'a[href*="/author/"]',
            'artist': 'a[href*="/artist/"]',
            'description': 'div.markdown',
            'cover_image': 'img.rounded',
            'status': 'div.font-bold:contains("Status") + div',
            'genres': 'a[href*="/tag/"]',
            'rating': 'div[class*="rating"]',
            'chapters': 'div[class*="chapter-row"]',
            'chapter_images': 'img.page-img',
        }

    def scrape_manga_list(self, page: int = 1) -> List[str]:
        """
        Scrape list of manga URLs from MangaDex

        Args:
            page: Page number (offset calculation: (page-1) * 20)

        Returns:
            List of manga URLs
        """
        try:
            offset = (page - 1) * 20
            url = f"/titles/recent?page={page}"

            soup = self.fetch_page(url)
            manga_links = []

            # Find manga links
            for link in soup.select('a[href*="/title/"]'):
                href = link.get('href')
                if href and '/title/' in href:
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
        Scrape detailed manga information from MangaDex

        Args:
            manga_url: URL to manga detail page

        Returns:
            Manga object or None if scraping failed
        """
        try:
            if not self.validate_url(manga_url):
                raise ScraperError(f"Invalid MangaDex URL: {manga_url}")

            soup = self.fetch_page(manga_url)
            selectors = self.get_selectors()

            # Extract manga ID from URL
            manga_id = manga_url.split('/title/')[-1].split('/')[0]

            # Extract basic info
            title = self._extract_text(soup, selectors['manga_title'])
            if not title:
                raise ScraperError("Could not extract manga title")

            author = self._extract_text(soup, selectors['author'])
            artist = self._extract_text(soup, selectors['artist'])
            description = self._extract_text(soup, selectors['description'])

            # Extract cover image
            cover_url = self._extract_attribute(soup, selectors['cover_image'], 'src')

            # Extract genres
            genres = self._extract_list(soup, selectors['genres'])

            # Extract status
            status_text = self._extract_text(soup, selectors['status'], 'unknown')
            status = self._parse_status(status_text)

            # Create Manga object
            manga = Manga(
                manga_id=manga_id,
                title=title,
                author=author,
                artist=artist,
                description=description,
                status=status,
                genres=genres,
                cover_url=cover_url,
                original_url=manga_url,
            )

            logger.info(f"Scraped manga: {title}")
            return manga

        except Exception as e:
            logger.error(f"Error scraping manga details from {manga_url}: {e}")
            return None

    def scrape_chapter_list(self, manga_url: str) -> List[Dict[str, str]]:
        """
        Scrape list of chapters from MangaDex manga page

        Args:
            manga_url: URL to manga detail page

        Returns:
            List of chapter dictionaries
        """
        try:
            soup = self.fetch_page(manga_url)
            chapters = []

            # Find chapter elements
            for chapter_elem in soup.select('div[class*="chapter-row"]'):
                chapter_link = chapter_elem.select_one('a[href*="/chapter/"]')
                if not chapter_link:
                    continue

                chapter_url = self._make_absolute_url(chapter_link.get('href'))

                # Extract chapter number and title
                chapter_text = chapter_link.get_text(strip=True)
                chapter_parts = chapter_text.split(' - ', 1)

                chapter_number = chapter_parts[0].replace('Chapter', '').strip()
                chapter_title = chapter_parts[1] if len(chapter_parts) > 1 else ""

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
        Scrape image URLs from MangaDex chapter page

        Args:
            chapter_url: URL to chapter reader page

        Returns:
            List of image URLs
        """
        try:
            if not self.validate_url(chapter_url):
                raise ScraperError(f"Invalid MangaDex URL: {chapter_url}")

            soup = self.fetch_page(chapter_url)
            selectors = self.get_selectors()

            # Extract image URLs
            image_urls = []
            for img in soup.select(selectors['chapter_images']):
                img_url = img.get('src') or img.get('data-src')
                if img_url:
                    image_urls.append(self._make_absolute_url(img_url))

            logger.info(f"Found {len(image_urls)} pages in chapter")
            return image_urls

        except Exception as e:
            logger.error(f"Error scraping chapter pages: {e}")
            return []

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

        if 'ongoing' in status_text or 'publishing' in status_text:
            return MangaStatus.ONGOING
        elif 'completed' in status_text or 'finished' in status_text:
            return MangaStatus.COMPLETED
        elif 'hiatus' in status_text:
            return MangaStatus.HIATUS
        elif 'cancelled' in status_text or 'canceled' in status_text:
            return MangaStatus.CANCELLED
        else:
            return MangaStatus.UNKNOWN
