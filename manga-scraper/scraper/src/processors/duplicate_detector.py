"""
Duplicate Detector
==================

Hash-based duplicate detection for images and content.
"""

import hashlib
import logging
from typing import Set, Dict, Optional, List
from collections import defaultdict

logger = logging.getLogger(__name__)


class DuplicateDetector:
    """
    Detects duplicate images using hash-based comparison

    Features:
    - MD5 hash-based exact duplicate detection
    - Perceptual hash-based similar image detection
    - In-memory and persistent storage options
    - Batch duplicate checking
    """

    def __init__(self, enable_perceptual_hashing: bool = False):
        """
        Initialize duplicate detector

        Args:
            enable_perceptual_hashing: Enable perceptual hash comparison
                                      for near-duplicate detection
        """
        self.exact_hashes: Set[str] = set()
        self.perceptual_hashes: Dict[str, List[str]] = defaultdict(list)
        self.enable_perceptual_hashing = enable_perceptual_hashing
        self.duplicate_count = 0
        self.total_checked = 0

    def add_hash(self, exact_hash: str, perceptual_hash: Optional[str] = None) -> None:
        """
        Add hash to tracking sets

        Args:
            exact_hash: MD5 or SHA256 hash of image
            perceptual_hash: Optional perceptual hash for similarity detection
        """
        self.exact_hashes.add(exact_hash)

        if self.enable_perceptual_hashing and perceptual_hash:
            self.perceptual_hashes[perceptual_hash].append(exact_hash)

        logger.debug(f"Added hash to detector: {exact_hash[:8]}...")

    def is_duplicate(
        self,
        exact_hash: str,
        perceptual_hash: Optional[str] = None,
        similarity_threshold: int = 5
    ) -> bool:
        """
        Check if hash represents a duplicate

        Args:
            exact_hash: MD5 or SHA256 hash of image
            perceptual_hash: Optional perceptual hash
            similarity_threshold: Hamming distance threshold for perceptual hashes

        Returns:
            True if duplicate detected
        """
        self.total_checked += 1

        # Check for exact duplicate
        if exact_hash in self.exact_hashes:
            self.duplicate_count += 1
            logger.info(f"Exact duplicate detected: {exact_hash[:8]}...")
            return True

        # Check for similar images using perceptual hashing
        if (self.enable_perceptual_hashing and perceptual_hash and
                self.perceptual_hashes):
            for existing_phash, existing_hashes in self.perceptual_hashes.items():
                distance = self._hamming_distance(perceptual_hash, existing_phash)
                if distance <= similarity_threshold:
                    self.duplicate_count += 1
                    logger.info(
                        f"Similar image detected (distance: {distance}): "
                        f"{exact_hash[:8]}... matches {existing_phash[:8]}..."
                    )
                    return True

        return False

    def check_and_add(
        self,
        exact_hash: str,
        perceptual_hash: Optional[str] = None,
        similarity_threshold: int = 5
    ) -> bool:
        """
        Check for duplicate and add if unique

        Args:
            exact_hash: MD5 or SHA256 hash of image
            perceptual_hash: Optional perceptual hash
            similarity_threshold: Hamming distance threshold

        Returns:
            True if duplicate, False if unique (and added)
        """
        if self.is_duplicate(exact_hash, perceptual_hash, similarity_threshold):
            return True

        self.add_hash(exact_hash, perceptual_hash)
        return False

    def remove_hash(self, exact_hash: str) -> bool:
        """
        Remove hash from tracking

        Args:
            exact_hash: Hash to remove

        Returns:
            True if hash was present and removed
        """
        if exact_hash in self.exact_hashes:
            self.exact_hashes.remove(exact_hash)

            # Also remove from perceptual hashes
            if self.enable_perceptual_hashing:
                for phash, hashes in list(self.perceptual_hashes.items()):
                    if exact_hash in hashes:
                        hashes.remove(exact_hash)
                        if not hashes:
                            del self.perceptual_hashes[phash]

            logger.debug(f"Removed hash: {exact_hash[:8]}...")
            return True

        return False

    def clear(self) -> None:
        """Clear all tracked hashes"""
        self.exact_hashes.clear()
        self.perceptual_hashes.clear()
        logger.info("Duplicate detector cleared")

    def get_statistics(self) -> Dict[str, int]:
        """
        Get duplicate detection statistics

        Returns:
            Dictionary with statistics
        """
        return {
            'total_unique_hashes': len(self.exact_hashes),
            'total_perceptual_hashes': len(self.perceptual_hashes),
            'duplicate_count': self.duplicate_count,
            'total_checked': self.total_checked,
            'duplicate_rate': (
                round(self.duplicate_count / self.total_checked * 100, 2)
                if self.total_checked > 0 else 0.0
            ),
        }

    @staticmethod
    def calculate_md5(data: bytes) -> str:
        """
        Calculate MD5 hash of data

        Args:
            data: Bytes to hash

        Returns:
            Hexadecimal hash string
        """
        return hashlib.md5(data).hexdigest()

    @staticmethod
    def calculate_sha256(data: bytes) -> str:
        """
        Calculate SHA256 hash of data

        Args:
            data: Bytes to hash

        Returns:
            Hexadecimal hash string
        """
        return hashlib.sha256(data).hexdigest()

    @staticmethod
    def _hamming_distance(hash1: str, hash2: str) -> int:
        """
        Calculate Hamming distance between two hashes

        Args:
            hash1: First hash string
            hash2: Second hash string

        Returns:
            Hamming distance (number of differing bits)
        """
        if len(hash1) != len(hash2):
            return float('inf')

        try:
            # Convert hex strings to integers
            int1 = int(hash1, 16)
            int2 = int(hash2, 16)

            # XOR the integers and count set bits
            xor = int1 ^ int2
            return bin(xor).count('1')

        except ValueError:
            logger.error("Invalid hash format for Hamming distance calculation")
            return float('inf')

    def export_hashes(self) -> Dict[str, any]:
        """
        Export hashes for persistent storage

        Returns:
            Dictionary with all tracked hashes
        """
        return {
            'exact_hashes': list(self.exact_hashes),
            'perceptual_hashes': dict(self.perceptual_hashes),
            'statistics': self.get_statistics(),
        }

    def import_hashes(self, data: Dict[str, any]) -> None:
        """
        Import hashes from persistent storage

        Args:
            data: Dictionary with hash data from export_hashes()
        """
        self.exact_hashes = set(data.get('exact_hashes', []))
        self.perceptual_hashes = defaultdict(
            list,
            data.get('perceptual_hashes', {})
        )

        logger.info(
            f"Imported {len(self.exact_hashes)} exact hashes and "
            f"{len(self.perceptual_hashes)} perceptual hashes"
        )

    def find_duplicates_in_batch(
        self,
        hashes: List[str]
    ) -> Dict[str, List[str]]:
        """
        Find duplicates within a batch of hashes

        Args:
            hashes: List of hashes to check

        Returns:
            Dictionary mapping each duplicate hash to list of its duplicates
        """
        duplicates = defaultdict(list)
        seen = {}

        for hash_val in hashes:
            if hash_val in seen:
                duplicates[seen[hash_val]].append(hash_val)
            else:
                seen[hash_val] = hash_val

        return dict(duplicates)
