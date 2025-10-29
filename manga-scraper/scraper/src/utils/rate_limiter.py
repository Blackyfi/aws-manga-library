"""
Rate Limiter
============

Implements rate limiting and politeness delays for web scraping.
"""

import time
import logging
from typing import Optional
from threading import Lock
from collections import deque
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class RateLimiter:
    """
    Rate limiter with multiple strategies

    Features:
    - Simple delay-based rate limiting
    - Token bucket algorithm
    - Sliding window rate limiting
    - Thread-safe operations
    """

    def __init__(
        self,
        requests_per_second: float = 1.0,
        base_delay: float = 0.0,
        burst_size: Optional[int] = None
    ):
        """
        Initialize rate limiter

        Args:
            requests_per_second: Maximum requests per second
            base_delay: Additional base delay between requests (seconds)
            burst_size: Maximum burst size (None = no bursting)
        """
        self.requests_per_second = requests_per_second
        self.min_interval = 1.0 / requests_per_second
        self.base_delay = base_delay
        self.burst_size = burst_size or 1

        # Tracking
        self.last_request_time = 0.0
        self.request_times = deque(maxlen=100)  # Track last 100 requests
        self.total_requests = 0
        self.total_wait_time = 0.0

        # Thread safety
        self.lock = Lock()

        logger.info(
            f"RateLimiter initialized: {requests_per_second} req/s, "
            f"base_delay={base_delay}s, burst={burst_size}"
        )

    def wait(self) -> float:
        """
        Wait appropriate amount of time before next request

        Returns:
            Time waited in seconds
        """
        with self.lock:
            current_time = time.time()
            time_since_last = current_time - self.last_request_time

            # Calculate required wait time
            wait_time = max(0, self.min_interval - time_since_last) + self.base_delay

            if wait_time > 0:
                logger.debug(f"Rate limiting: waiting {wait_time:.2f}s")
                time.sleep(wait_time)
                waited = wait_time
            else:
                waited = 0.0

            # Update tracking
            self.last_request_time = time.time()
            self.request_times.append(self.last_request_time)
            self.total_requests += 1
            self.total_wait_time += waited

            return waited

    def wait_with_token_bucket(self) -> float:
        """
        Wait using token bucket algorithm (allows bursting)

        Returns:
            Time waited in seconds
        """
        with self.lock:
            current_time = time.time()

            # Initialize token bucket on first call
            if not hasattr(self, 'tokens'):
                self.tokens = float(self.burst_size)
                self.last_refill_time = current_time

            # Refill tokens based on time passed
            time_passed = current_time - self.last_refill_time
            tokens_to_add = time_passed * self.requests_per_second
            self.tokens = min(self.burst_size, self.tokens + tokens_to_add)
            self.last_refill_time = current_time

            # If we have tokens, consume one
            if self.tokens >= 1.0:
                self.tokens -= 1.0
                waited = 0.0

                # Apply base delay if configured
                if self.base_delay > 0:
                    time.sleep(self.base_delay)
                    waited = self.base_delay

            else:
                # Wait until we have a token
                wait_time = (1.0 - self.tokens) / self.requests_per_second
                wait_time += self.base_delay

                logger.debug(f"Token bucket: waiting {wait_time:.2f}s")
                time.sleep(wait_time)
                waited = wait_time

                # Refill after waiting
                self.tokens = 0.0
                self.last_refill_time = time.time()

            # Update tracking
            self.request_times.append(time.time())
            self.total_requests += 1
            self.total_wait_time += waited

            return waited

    def get_current_rate(self) -> float:
        """
        Calculate current request rate

        Returns:
            Requests per second (average over last requests)
        """
        if len(self.request_times) < 2:
            return 0.0

        time_span = self.request_times[-1] - self.request_times[0]
        if time_span == 0:
            return 0.0

        return (len(self.request_times) - 1) / time_span

    def get_statistics(self) -> dict:
        """
        Get rate limiter statistics

        Returns:
            Dictionary with statistics
        """
        return {
            'total_requests': self.total_requests,
            'total_wait_time': round(self.total_wait_time, 2),
            'average_wait_time': (
                round(self.total_wait_time / self.total_requests, 3)
                if self.total_requests > 0 else 0.0
            ),
            'current_rate': round(self.get_current_rate(), 2),
            'configured_rate': self.requests_per_second,
            'base_delay': self.base_delay,
        }

    def reset(self) -> None:
        """Reset rate limiter state"""
        with self.lock:
            self.last_request_time = 0.0
            self.request_times.clear()
            self.total_requests = 0
            self.total_wait_time = 0.0

            # Reset token bucket if it exists
            if hasattr(self, 'tokens'):
                self.tokens = float(self.burst_size)
                self.last_refill_time = time.time()

        logger.info("Rate limiter reset")

    def __enter__(self):
        """Context manager entry"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - log statistics"""
        stats = self.get_statistics()
        logger.info(f"Rate limiter stats: {stats}")


class AdaptiveRateLimiter(RateLimiter):
    """
    Rate limiter that adapts based on response times and errors

    Features:
    - Automatically slow down on errors
    - Speed up when responses are fast
    - Back off on rate limit errors
    """

    def __init__(
        self,
        initial_rate: float = 1.0,
        min_rate: float = 0.1,
        max_rate: float = 5.0,
        **kwargs
    ):
        """
        Initialize adaptive rate limiter

        Args:
            initial_rate: Initial requests per second
            min_rate: Minimum requests per second
            max_rate: Maximum requests per second
            **kwargs: Additional arguments for RateLimiter
        """
        super().__init__(requests_per_second=initial_rate, **kwargs)
        self.initial_rate = initial_rate
        self.min_rate = min_rate
        self.max_rate = max_rate

        # Adaptive tracking
        self.success_count = 0
        self.error_count = 0
        self.last_response_times = deque(maxlen=10)

    def on_success(self, response_time: Optional[float] = None) -> None:
        """
        Record successful request

        Args:
            response_time: Response time in seconds
        """
        with self.lock:
            self.success_count += 1
            self.error_count = max(0, self.error_count - 1)

            if response_time:
                self.last_response_times.append(response_time)

            # Speed up if consistently fast
            if self.success_count >= 10 and self._is_fast():
                self._increase_rate()
                self.success_count = 0

    def on_error(self, is_rate_limit: bool = False) -> None:
        """
        Record failed request

        Args:
            is_rate_limit: Whether error was due to rate limiting
        """
        with self.lock:
            self.error_count += 1
            self.success_count = 0

            # Slow down on errors
            if is_rate_limit:
                self._decrease_rate(factor=0.5)
            elif self.error_count >= 3:
                self._decrease_rate(factor=0.8)
                self.error_count = 0

    def _is_fast(self) -> bool:
        """Check if recent responses were fast"""
        if len(self.last_response_times) < 5:
            return False

        avg_time = sum(self.last_response_times) / len(self.last_response_times)
        return avg_time < 1.0  # Consider fast if under 1 second

    def _increase_rate(self, factor: float = 1.2) -> None:
        """Increase request rate"""
        old_rate = self.requests_per_second
        self.requests_per_second = min(self.max_rate, old_rate * factor)
        self.min_interval = 1.0 / self.requests_per_second

        logger.info(f"Rate increased: {old_rate:.2f} -> {self.requests_per_second:.2f} req/s")

    def _decrease_rate(self, factor: float = 0.8) -> None:
        """Decrease request rate"""
        old_rate = self.requests_per_second
        self.requests_per_second = max(self.min_rate, old_rate * factor)
        self.min_interval = 1.0 / self.requests_per_second

        logger.warning(f"Rate decreased: {old_rate:.2f} -> {self.requests_per_second:.2f} req/s")
