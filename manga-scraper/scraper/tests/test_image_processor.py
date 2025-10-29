"""
Image Processor Tests
=====================

Tests for image processing functionality.
"""

import pytest
from PIL import Image
from io import BytesIO

from src.processors import ImageProcessor


class TestImageProcessor:
    """Test cases for ImageProcessor"""

    def test_initialize(self):
        """Test processor initialization"""
        processor = ImageProcessor(
            target_size_kb=200,
            webp_quality=85,
            thumbnail_max_width=300
        )

        assert processor.target_size_kb == 200
        assert processor.webp_quality == 85
        assert processor.thumbnail_max_width == 300

    def test_optimize_image(self, image_processor, sample_image_data):
        """Test image optimization"""
        optimized_data, image_hash, metadata = image_processor.optimize_image(
            sample_image_data
        )

        assert isinstance(optimized_data, bytes)
        assert isinstance(image_hash, str)
        assert len(image_hash) == 32  # MD5 hash length
        assert isinstance(metadata, dict)
        assert 'original_size' in metadata
        assert 'optimized_size' in metadata
        assert 'compression_ratio' in metadata

    def test_optimize_image_reduces_size(self, image_processor):
        """Test that optimization reduces file size"""
        # Create a large test image
        img = Image.new('RGB', (1000, 1000), color='blue')
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        original_data = buffer.getvalue()

        optimized_data, _, metadata = image_processor.optimize_image(original_data)

        assert len(optimized_data) < len(original_data)
        assert metadata['compression_ratio'] < 1.0

    def test_create_thumbnail(self, image_processor, sample_image_data):
        """Test thumbnail creation"""
        thumbnail_data = image_processor.create_thumbnail(sample_image_data)

        assert isinstance(thumbnail_data, bytes)

        # Verify thumbnail is smaller
        assert len(thumbnail_data) < len(sample_image_data)

        # Verify thumbnail dimensions
        thumb_img = Image.open(BytesIO(thumbnail_data))
        assert thumb_img.width <= image_processor.thumbnail_max_width

    def test_validate_image_valid(self, image_processor, sample_image_data):
        """Test image validation with valid image"""
        assert image_processor.validate_image(sample_image_data) is True

    def test_validate_image_invalid(self, image_processor):
        """Test image validation with invalid data"""
        invalid_data = b'not an image'
        assert image_processor.validate_image(invalid_data) is False

    def test_get_image_info(self, image_processor, sample_image_data):
        """Test getting image information"""
        info = image_processor.get_image_info(sample_image_data)

        assert isinstance(info, dict)
        assert 'format' in info
        assert 'width' in info
        assert 'height' in info
        assert 'file_size' in info
        assert info['width'] == 100
        assert info['height'] == 100

    def test_convert_format(self, image_processor, sample_image_data):
        """Test format conversion"""
        # Convert PNG to JPEG
        jpeg_data = image_processor.convert_format(
            sample_image_data,
            'JPEG',
            quality=90
        )

        assert isinstance(jpeg_data, bytes)

        # Verify format
        img = Image.open(BytesIO(jpeg_data))
        assert img.format == 'JPEG'

    def test_calculate_perceptual_hash(self, image_processor, sample_image_data):
        """Test perceptual hash calculation"""
        hash_value = image_processor.calculate_perceptual_hash(sample_image_data)

        assert isinstance(hash_value, str)
        assert len(hash_value) > 0

        # Same image should produce same hash
        hash_value2 = image_processor.calculate_perceptual_hash(sample_image_data)
        assert hash_value == hash_value2

    def test_optimize_rgba_image(self, image_processor):
        """Test optimization of RGBA image"""
        # Create RGBA image with transparency
        img = Image.new('RGBA', (100, 100), color=(255, 0, 0, 128))
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        rgba_data = buffer.getvalue()

        optimized_data, _, metadata = image_processor.optimize_image(rgba_data)

        assert isinstance(optimized_data, bytes)
        assert len(optimized_data) > 0

    def test_optimize_grayscale_image(self, image_processor):
        """Test optimization of grayscale image"""
        img = Image.new('L', (100, 100), color=128)
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        gray_data = buffer.getvalue()

        optimized_data, _, metadata = image_processor.optimize_image(gray_data)

        assert isinstance(optimized_data, bytes)
        assert len(optimized_data) > 0

    def test_thumbnail_maintains_aspect_ratio(self, image_processor):
        """Test that thumbnail maintains aspect ratio"""
        # Create rectangular image
        img = Image.new('RGB', (400, 200), color='green')
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        rect_data = buffer.getvalue()

        thumbnail_data = image_processor.create_thumbnail(
            rect_data,
            max_width=200
        )

        thumb_img = Image.open(BytesIO(thumbnail_data))

        # Check aspect ratio is maintained
        original_ratio = 400 / 200
        thumb_ratio = thumb_img.width / thumb_img.height

        assert abs(original_ratio - thumb_ratio) < 0.1  # Allow small difference
