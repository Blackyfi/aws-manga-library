"""
Base Scraper
============

Abstract base class for manga scrapers.
"""

import logging
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

from ..models import Manga, Chapter, Page
from ..utils import RateLimiter, RetryHandler

logger = logging.getLogger(__name__)


class ScraperError(Exception):
    """Custom exception for scraper errors"""
    pass


class BaseScraper(ABC):
    """
    Abstract base class for manga scrapers

    All site-specific scrapers should inherit from this class
    and implement the abstract methods.
    """

    def __init__(
        self,
        base_url: str,
        user_agent: str = 'MangaScraperBot/1.0 (Educational Purpose)',
        requests_per_second: float = 0.5,
        request_timeout: int = 30,
        max_retries: int = 3
    ):
        """
        Initialize base scraper

        Args:
            base_url: Base URL of the manga site
            user_agent: User agent string for requests
            requests_per_second: Rate limit for requests
            request_timeout: Request timeout in seconds
            max_retries: Maximum retry attempts
        """
        self.base_url = base_url
        self.user_agent = user_agent
        self.request_timeout = request_timeout

        # Setup HTTP session
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': user_agent,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })

        # Initialize utilities
        self.rate_limiter = RateLimiter(requests_per_second=requests_per_second)
        self.retry_handler = RetryHandler(max_retries=max_retries)

        logger.info(f"Initialized {self.__class__.__name__} for {base_url}")

    @abstractmethod
    def get_selectors(self) -> Dict[str, str]:
        """
        Get CSS selectors for the site

        Returns:
            Dictionary of selector names to CSS selector strings
        """
        pass

    @abstractmethod
    def scrape_manga_list(self, page: int = 1) -> List[str]:
        """
        Scrape list of manga URLs from index page

        Args:
            page: Page number

        Returns:
            List of manga URLs
        """
        pass

    @abstractmethod
    def scrape_manga_details(self, manga_url: str) -> Optional[Manga]:
        """
        Scrape detailed manga information

        Args:
            manga_url: URL to manga detail page

        Returns:
            Manga object or None if scraping failed
        """
        pass

    @abstractmethod
    def scrape_chapter_list(self, manga_url: str) -> List[Dict[str, str]]:
        """
        Scrape list of chapters from manga page

        Args:
            manga_url: URL to manga detail page

        Returns:
            List of chapter dictionaries with 'url', 'number', 'title'
        """
        pass

    @abstractmethod
    def scrape_chapter_pages(self, chapter_url: str) -> List[str]:
        """
        Scrape image URLs from chapter page

        Args:
            chapter_url: URL to chapter reader page

        Returns:
            List of image URLs
        """
        pass

    def fetch_page(self, url: str) -> BeautifulSoup:
        """
        Fetch and parse a web page with rate limiting and retry logic

        Args:
            url: URL to fetch

        Returns:
            BeautifulSoup object

        Raises:
            ScraperError: If page fetch fails after retries
        """
        def _fetch():
            # Apply rate limiting
            self.rate_limiter.wait()

            # Make request
            full_url = self._make_absolute_url(url)
            logger.debug(f"Fetching: {full_url}")

            response = self.session.get(full_url, timeout=self.request_timeout)
            response.raise_for_status()

            return BeautifulSoup(response.content, 'html.parser')

        try:
            return self.retry_handler.execute_with_retry(_fetch)
        except Exception as e:
            logger.error(f"Failed to fetch page {url}: {e}")
            raise ScraperError(f"Failed to fetch page: {e}") from e

    def download_image(self, url: str) -> bytes:
        """
        Download image from URL

        Args:
            url: Image URL

        Returns:
            Image bytes

        Raises:
            ScraperError: If download fails after retries
        """
        def _download():
            # Apply rate limiting
            self.rate_limiter.wait()

            # Make request
            full_url = self._make_absolute_url(url)
            logger.debug(f"Downloading image: {full_url}")

            response = self.session.get(
                full_url,
                timeout=self.request_timeout,
                stream=True
            )
            response.raise_for_status()

            return response.content

        try:
            return self.retry_handler.execute_with_retry(_download)
        except Exception as e:
            logger.error(f"Failed to download image {url}: {e}")
            raise ScraperError(f"Failed to download image: {e}") from e

    def _make_absolute_url(self, url: str) -> str:
        """
        Convert relative URL to absolute URL

        Args:
            url: URL (relative or absolute)

        Returns:
            Absolute URL
        """
        if not url:
            return ""

        # Already absolute
        if url.startswith(('http://', 'https://')):
            return url

        # Relative URL
        return urljoin(self.base_url, url)

    def _extract_text(
        self,
        soup: BeautifulSoup,
        selector: str,
        default: str = ""
    ) -> str:
        """
        Extract text from element using CSS selector

        Args:
            soup: BeautifulSoup object
            selector: CSS selector
            default: Default value if element not found

        Returns:
            Extracted text or default
        """
        element = soup.select_one(selector)
        if element:
            return element.get_text(strip=True)
        return default

    def _extract_attribute(
        self,
        soup: BeautifulSoup,
        selector: str,
        attribute: str,
        default: str = ""
    ) -> str:
        """
        Extract attribute from element using CSS selector

        Args:
            soup: BeautifulSoup object
            selector: CSS selector
            attribute: Attribute name
            default: Default value if element not found

        Returns:
            Attribute value or default
        """
        element = soup.select_one(selector)
        if element:
            return element.get(attribute, default)
        return default

    def _extract_list(
        self,
        soup: BeautifulSoup,
        selector: str
    ) -> List[str]:
        """
        Extract list of text values using CSS selector

        Args:
            soup: BeautifulSoup object
            selector: CSS selector

        Returns:
            List of text values
        """
        elements = soup.select(selector)
        return [elem.get_text(strip=True) for elem in elements]

    def validate_url(self, url: str) -> bool:
        """
        Validate that URL belongs to this scraper's domain

        Args:
            url: URL to validate

        Returns:
            True if URL is valid for this scraper
        """
        try:
            parsed = urlparse(url)
            base_parsed = urlparse(self.base_url)
            return parsed.netloc == base_parsed.netloc
        except Exception:
            return False

    def close(self) -> None:
        """Close HTTP session"""
        self.session.close()
        logger.info(f"Closed {self.__class__.__name__} session")

    def __enter__(self):
        """Context manager entry"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()
