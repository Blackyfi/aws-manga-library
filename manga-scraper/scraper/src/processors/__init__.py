"""
Processors Package
==================

Image processing and duplicate detection utilities.
"""

from .image_processor import ImageProcessor
from .duplicate_detector import DuplicateDetector

__all__ = [
    'ImageProcessor',
    'DuplicateDetector',
]
