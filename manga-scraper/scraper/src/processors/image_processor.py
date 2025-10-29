"""
Image Processor
===============

Handles image optimization, conversion, and thumbnail generation.
"""

import hashlib
import logging
from io import BytesIO
from typing import Tuple, Optional, Dict, Any

from PIL import Image, ImageOps

logger = logging.getLogger(__name__)


class ImageProcessor:
    """
    Handles image optimization and processing operations

    Features:
    - Convert images to WebP format
    - Compress images to target size
    - Generate thumbnails
    - Calculate image hashes for duplicate detection
    - Handle various image formats (PNG, JPEG, GIF, etc.)
    """

    def __init__(
        self,
        target_size_kb: int = 200,
        webp_quality: int = 85,
        thumbnail_max_width: int = 300,
        thumbnail_quality: int = 70
    ):
        """
        Initialize image processor

        Args:
            target_size_kb: Target file size in KB for optimization
            webp_quality: WebP quality (1-100, higher is better)
            thumbnail_max_width: Maximum width for thumbnails in pixels
            thumbnail_quality: Quality for thumbnail compression (1-100)
        """
        self.target_size_kb = target_size_kb
        self.webp_quality = webp_quality
        self.thumbnail_max_width = thumbnail_max_width
        self.thumbnail_quality = thumbnail_quality

    def optimize_image(
        self,
        image_data: bytes,
        format: str = 'WEBP'
    ) -> Tuple[bytes, str, Dict[str, Any]]:
        """
        Optimize image by converting to WebP and compressing

        Args:
            image_data: Raw image bytes
            format: Output format (default: WEBP)

        Returns:
            Tuple of (optimized_bytes, image_hash, metadata_dict)

        Raises:
            ValueError: If image data is invalid
            IOError: If image processing fails
        """
        try:
            # Open and validate image
            img = Image.open(BytesIO(image_data))
            original_format = img.format
            original_size = len(image_data)

            # Get original dimensions
            width, height = img.size

            # Fix orientation from EXIF data if present
            img = ImageOps.exif_transpose(img)

            # Convert to RGB if necessary (WebP doesn't support all modes)
            if img.mode in ('RGBA', 'LA'):
                # Preserve transparency
                background = Image.new('RGBA', img.size, (255, 255, 255, 255))
                background.paste(img, mask=img.split()[-1] if img.mode in ('RGBA', 'LA') else None)
                img = background
            elif img.mode == 'P':
                # Convert palette to RGBA
                img = img.convert('RGBA')
            elif img.mode not in ('RGB', 'RGBA'):
                # Convert other modes to RGB
                img = img.convert('RGB')

            # Optimize to target format
            output = BytesIO()
            save_kwargs = {
                'format': format,
                'optimize': True,
            }

            if format == 'WEBP':
                save_kwargs['quality'] = self.webp_quality
                save_kwargs['method'] = 6  # Slowest but best compression
            elif format in ('JPEG', 'JPG'):
                save_kwargs['quality'] = self.webp_quality
                save_kwargs['progressive'] = True
            elif format == 'PNG':
                save_kwargs['compress_level'] = 9

            img.save(output, **save_kwargs)
            optimized_data = output.getvalue()

            # Calculate hash for duplicate detection
            image_hash = self._calculate_hash(optimized_data)

            # Prepare metadata
            metadata = {
                'original_format': original_format,
                'original_size': original_size,
                'optimized_size': len(optimized_data),
                'width': width,
                'height': height,
                'compression_ratio': round(len(optimized_data) / original_size, 2),
            }

            logger.info(
                f"Image optimized: {original_size/1024:.1f}KB -> "
                f"{len(optimized_data)/1024:.1f}KB "
                f"({metadata['compression_ratio']*100:.1f}% of original)"
            )

            return optimized_data, image_hash, metadata

        except Exception as e:
            logger.error(f"Error optimizing image: {e}")
            raise

    def create_thumbnail(
        self,
        image_data: bytes,
        max_width: Optional[int] = None,
        max_height: Optional[int] = None
    ) -> bytes:
        """
        Create thumbnail for preview

        Args:
            image_data: Raw image bytes or optimized bytes
            max_width: Maximum width in pixels (default: self.thumbnail_max_width)
            max_height: Maximum height in pixels (maintains aspect ratio if not set)

        Returns:
            Thumbnail bytes

        Raises:
            ValueError: If image data is invalid
            IOError: If thumbnail creation fails
        """
        try:
            img = Image.open(BytesIO(image_data))

            # Fix orientation
            img = ImageOps.exif_transpose(img)

            # Calculate new dimensions
            if max_width is None:
                max_width = self.thumbnail_max_width

            # Use thumbnail method which maintains aspect ratio
            if max_height:
                img.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)
            else:
                # Calculate height maintaining aspect ratio
                ratio = max_width / img.width
                new_height = int(img.height * ratio)
                img.thumbnail((max_width, new_height), Image.Resampling.LANCZOS)

            # Convert to RGB if necessary
            if img.mode in ('RGBA', 'LA', 'P'):
                background = Image.new('RGB', img.size, (255, 255, 255))
                if img.mode == 'P':
                    img = img.convert('RGBA')
                if img.mode in ('RGBA', 'LA'):
                    background.paste(img, mask=img.split()[-1])
                    img = background

            # Save as WebP
            output = BytesIO()
            img.save(
                output,
                format='WEBP',
                quality=self.thumbnail_quality,
                method=4
            )

            thumbnail_data = output.getvalue()

            logger.debug(
                f"Thumbnail created: {img.size[0]}x{img.size[1]}, "
                f"{len(thumbnail_data)/1024:.1f}KB"
            )

            return thumbnail_data

        except Exception as e:
            logger.error(f"Error creating thumbnail: {e}")
            raise

    def validate_image(self, image_data: bytes) -> bool:
        """
        Validate that data is a valid image

        Args:
            image_data: Raw image bytes

        Returns:
            True if valid image, False otherwise
        """
        try:
            img = Image.open(BytesIO(image_data))
            img.verify()
            return True
        except Exception as e:
            logger.warning(f"Invalid image data: {e}")
            return False

    def get_image_info(self, image_data: bytes) -> Dict[str, Any]:
        """
        Get detailed image information

        Args:
            image_data: Raw image bytes

        Returns:
            Dictionary with image information
        """
        try:
            img = Image.open(BytesIO(image_data))

            info = {
                'format': img.format,
                'mode': img.mode,
                'size': img.size,
                'width': img.width,
                'height': img.height,
                'file_size': len(image_data),
                'has_transparency': img.mode in ('RGBA', 'LA', 'P'),
            }

            # Add EXIF data if available
            if hasattr(img, '_getexif') and img._getexif():
                info['has_exif'] = True
            else:
                info['has_exif'] = False

            return info

        except Exception as e:
            logger.error(f"Error getting image info: {e}")
            return {}

    def convert_format(
        self,
        image_data: bytes,
        target_format: str,
        quality: int = 85
    ) -> bytes:
        """
        Convert image to different format

        Args:
            image_data: Raw image bytes
            target_format: Target format (WEBP, JPEG, PNG, etc.)
            quality: Quality for lossy formats

        Returns:
            Converted image bytes
        """
        try:
            img = Image.open(BytesIO(image_data))

            # Fix orientation
            img = ImageOps.exif_transpose(img)

            # Handle transparency for formats that don't support it
            if target_format in ('JPEG', 'JPG') and img.mode in ('RGBA', 'LA', 'P'):
                background = Image.new('RGB', img.size, (255, 255, 255))
                if img.mode == 'P':
                    img = img.convert('RGBA')
                if img.mode in ('RGBA', 'LA'):
                    background.paste(img, mask=img.split()[-1])
                    img = background

            output = BytesIO()
            save_kwargs = {'format': target_format}

            if target_format in ('WEBP', 'JPEG', 'JPG'):
                save_kwargs['quality'] = quality
            elif target_format == 'PNG':
                save_kwargs['compress_level'] = 9

            img.save(output, **save_kwargs)
            return output.getvalue()

        except Exception as e:
            logger.error(f"Error converting image format: {e}")
            raise

    @staticmethod
    def _calculate_hash(data: bytes) -> str:
        """
        Calculate MD5 hash of image data

        Args:
            data: Image bytes

        Returns:
            Hexadecimal hash string
        """
        return hashlib.md5(data).hexdigest()

    def calculate_perceptual_hash(self, image_data: bytes) -> str:
        """
        Calculate perceptual hash for similarity detection

        Args:
            image_data: Raw image bytes

        Returns:
            Perceptual hash string

        Note:
            This uses a simple average hash algorithm. For production,
            consider using more sophisticated algorithms like pHash or dHash
        """
        try:
            img = Image.open(BytesIO(image_data))

            # Resize to 8x8 for hash calculation
            img = img.convert('L')  # Convert to grayscale
            img = img.resize((8, 8), Image.Resampling.LANCZOS)

            # Calculate average pixel value
            pixels = list(img.getdata())
            avg = sum(pixels) / len(pixels)

            # Generate hash based on whether pixels are above/below average
            hash_str = ''.join('1' if p > avg else '0' for p in pixels)

            # Convert binary string to hex
            return hex(int(hash_str, 2))[2:].zfill(16)

        except Exception as e:
            logger.error(f"Error calculating perceptual hash: {e}")
            return ""
