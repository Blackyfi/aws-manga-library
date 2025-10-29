"""
Scrapers Package
================

Base scraper and site-specific scraper implementations.
"""

from .base_scraper import BaseScraper, ScraperError
from .mangadex_scraper import MangaDexScraper
from .mangakakalot_scraper import MangaKakalotScraper

__all__ = [
    'BaseScraper',
    'ScraperError',
    'MangaDexScraper',
    'MangaKakalotScraper',
]
