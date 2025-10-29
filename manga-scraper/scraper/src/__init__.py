"""
Manga Scraper Package
A professional manga scraping and processing library for AWS.
"""

__version__ = "1.0.0"
__author__ = "Your Name"

from .manga_scraper import MangaScraper
from .config import Config

__all__ = ["MangaScraper", "Config"]
