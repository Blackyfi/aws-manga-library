"""
Configuration file for Manga Scraper
=====================================

Centralized configuration management
"""

import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class ScraperConfig:
    """Configuration for manga scraper"""
    
    # AWS Configuration
    s3_bucket: str
    dynamodb_table: str
    aws_region: str = 'us-east-1'
    
    # Rate Limiting
    requests_per_second: float = 0.5
    base_delay_seconds: float = 2.0
    
    # Retry Configuration
    max_retries: int = 3
    retry_base_delay: float = 1.0
    retry_max_delay: float = 60.0
    
    # Image Processing
    target_image_size_kb: int = 200
    webp_quality: int = 85
    thumbnail_max_width: int = 300
    thumbnail_quality: int = 70
    
    # Scraping Behavior
    user_agent: str = 'MangaScraperBot/1.0 (Educational Purpose)'
    request_timeout: int = 30
    respect_robots_txt: bool = True
    
    # Storage Configuration
    s3_cache_control: str = 'max-age=2592000'  # 30 days
    enable_versioning: bool = True
    
    # Logging
    log_level: str = 'INFO'
    enable_cloudwatch_logs: bool = True
    
    @classmethod
    def from_env(cls) -> 'ScraperConfig':
        """
        Create configuration from environment variables
        
        Returns:
            ScraperConfig instance
        """
        return cls(
            s3_bucket=os.environ.get('S3_BUCKET', ''),
            dynamodb_table=os.environ.get('DYNAMODB_TABLE', ''),
            aws_region=os.environ.get('AWS_REGION', 'us-east-1'),
            requests_per_second=float(os.environ.get('REQUESTS_PER_SECOND', '0.5')),
            base_delay_seconds=float(os.environ.get('BASE_DELAY_SECONDS', '2.0')),
            max_retries=int(os.environ.get('MAX_RETRIES', '3')),
            target_image_size_kb=int(os.environ.get('TARGET_IMAGE_SIZE_KB', '200')),
            webp_quality=int(os.environ.get('WEBP_QUALITY', '85')),
            user_agent=os.environ.get('USER_AGENT', 'MangaScraperBot/1.0'),
            log_level=os.environ.get('LOG_LEVEL', 'INFO'),
        )
    
    def validate(self) -> bool:
        """
        Validate configuration
        
        Returns:
            True if valid
            
        Raises:
            ValueError: If configuration is invalid
        """
        if not self.s3_bucket:
            raise ValueError("S3_BUCKET is required")
        
        if not self.dynamodb_table:
            raise ValueError("DYNAMODB_TABLE is required")
        
        if self.requests_per_second <= 0:
            raise ValueError("requests_per_second must be positive")
        
        if self.webp_quality < 1 or self.webp_quality > 100:
            raise ValueError("webp_quality must be between 1 and 100")
        
        if self.max_retries < 1:
            raise ValueError("max_retries must be at least 1")
        
        return True


# Default configuration for local development
DEFAULT_CONFIG = ScraperConfig(
    s3_bucket='my-manga-bucket',
    dynamodb_table='manga-metadata',
    aws_region='us-east-1',
    requests_per_second=0.5,
    base_delay_seconds=2.0,
)


# Source-specific configurations
# Customize these for different manga sources
SOURCE_CONFIGS = {
    'mangadex': {
        'base_url': 'https://mangadex.org',
        'selectors': {
            'manga_title': 'h1.manga-title',
            'author': 'span.author',
            'description': 'div.description',
            'cover_image': 'img.cover',
            'genres': 'span.genre',
            'chapters': 'a.chapter-link',
            'chapter_images': 'img.chapter-image',
        },
        'rate_limit': 0.5,  # requests per second
    },
    'mangakakalot': {
        'base_url': 'https://mangakakalot.com',
        'selectors': {
            'manga_title': 'h1',
            'author': 'a[href*="author"]',
            'description': 'div#noidungm',
            'cover_image': 'div.manga-info-pic img',
            'genres': 'a[href*="genre"]',
            'chapters': 'div.chapter-list a',
            'chapter_images': 'div.container-chapter-reader img',
        },
        'rate_limit': 0.3,
    },
    # Add more sources as needed
}


def get_source_config(source_name: str) -> Optional[dict]:
    """
    Get configuration for a specific manga source
    
    Args:
        source_name: Name of the source
        
    Returns:
        Source configuration dict or None
    """
    return SOURCE_CONFIGS.get(source_name.lower())


def list_available_sources() -> list:
    """
    Get list of available manga sources
    
    Returns:
        List of source names
    """
    return list(SOURCE_CONFIGS.keys())
