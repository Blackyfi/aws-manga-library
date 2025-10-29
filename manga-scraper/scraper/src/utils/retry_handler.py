"""
Retry Handler
=============

Implements retry logic with exponential backoff and jitter.
"""

import time
import random
import logging
from typing import Callable, Any, Optional, Type, Tuple
from functools import wraps

logger = logging.getLogger(__name__)


class RetryHandler:
    """
    Handles retry logic with exponential backoff

    Features:
    - Exponential backoff with configurable base
    - Jitter to prevent thundering herd
    - Selective retry based on exception types
    - Callback hooks for retry events
    """

    def __init__(
        self,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        jitter: bool = True,
        retryable_exceptions: Optional[Tuple[Type[Exception], ...]] = None
    ):
        """
        Initialize retry handler

        Args:
            max_retries: Maximum number of retry attempts
            base_delay: Base delay for exponential backoff (seconds)
            max_delay: Maximum delay between retries (seconds)
            exponential_base: Base for exponential calculation
            jitter: Whether to add random jitter to delays
            retryable_exceptions: Tuple of exception types to retry
                                 (None = retry all exceptions)
        """
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter
        self.retryable_exceptions = retryable_exceptions

        # Statistics
        self.total_attempts = 0
        self.total_retries = 0
        self.total_failures = 0

        logger.info(
            f"RetryHandler initialized: max_retries={max_retries}, "
            f"base_delay={base_delay}s, max_delay={max_delay}s"
        )

    def execute_with_retry(
        self,
        func: Callable,
        *args,
        **kwargs
    ) -> Any:
        """
        Execute function with retry logic

        Args:
            func: Function to execute
            *args: Positional arguments for function
            **kwargs: Keyword arguments for function

        Returns:
            Function result

        Raises:
            Exception: Last exception if all retries exhausted
        """
        last_exception = None

        for attempt in range(self.max_retries):
            self.total_attempts += 1

            try:
                result = func(*args, **kwargs)

                # Log retry success if this was a retry
                if attempt > 0:
                    logger.info(f"Retry successful on attempt {attempt + 1}")

                return result

            except Exception as e:
                last_exception = e

                # Check if exception is retryable
                if not self._is_retryable(e):
                    logger.error(f"Non-retryable exception: {e}")
                    raise

                # Last attempt - don't retry
                if attempt >= self.max_retries - 1:
                    self.total_failures += 1
                    logger.error(f"All {self.max_retries} retry attempts exhausted")
                    break

                # Calculate delay and retry
                self.total_retries += 1
                delay = self._calculate_delay(attempt)

                logger.warning(
                    f"Attempt {attempt + 1}/{self.max_retries} failed: {e}. "
                    f"Retrying in {delay:.2f}s..."
                )

                time.sleep(delay)

        # All retries exhausted
        raise last_exception

    def _calculate_delay(self, attempt: int) -> float:
        """
        Calculate delay for given attempt using exponential backoff

        Args:
            attempt: Attempt number (0-indexed)

        Returns:
            Delay in seconds
        """
        # Exponential backoff
        delay = min(
            self.base_delay * (self.exponential_base ** attempt),
            self.max_delay
        )

        # Add jitter if enabled (±25% of delay)
        if self.jitter:
            jitter_range = delay * 0.25
            delay += random.uniform(-jitter_range, jitter_range)

        # Ensure non-negative
        return max(0, delay)

    def _is_retryable(self, exception: Exception) -> bool:
        """
        Check if exception is retryable

        Args:
            exception: Exception to check

        Returns:
            True if should retry
        """
        if self.retryable_exceptions is None:
            return True

        return isinstance(exception, self.retryable_exceptions)

    def get_statistics(self) -> dict:
        """
        Get retry statistics

        Returns:
            Dictionary with statistics
        """
        success_rate = (
            (self.total_attempts - self.total_failures) / self.total_attempts * 100
            if self.total_attempts > 0 else 0.0
        )

        return {
            'total_attempts': self.total_attempts,
            'total_retries': self.total_retries,
            'total_failures': self.total_failures,
            'success_rate': round(success_rate, 2),
            'average_retries_per_call': (
                round(self.total_retries / (self.total_attempts - self.total_retries), 2)
                if (self.total_attempts - self.total_retries) > 0 else 0.0
            ),
        }

    def reset_statistics(self) -> None:
        """Reset statistics counters"""
        self.total_attempts = 0
        self.total_retries = 0
        self.total_failures = 0
        logger.info("Retry statistics reset")


def retry_with_backoff(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    jitter: bool = True,
    retryable_exceptions: Optional[Tuple[Type[Exception], ...]] = None
):
    """
    Decorator for retrying functions with exponential backoff

    Args:
        max_retries: Maximum number of retry attempts
        base_delay: Base delay for exponential backoff (seconds)
        max_delay: Maximum delay between retries (seconds)
        exponential_base: Base for exponential calculation
        jitter: Whether to add random jitter to delays
        retryable_exceptions: Tuple of exception types to retry

    Example:
        @retry_with_backoff(max_retries=3, base_delay=1.0)
        def fetch_data():
            # Function that might fail
            pass
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            handler = RetryHandler(
                max_retries=max_retries,
                base_delay=base_delay,
                max_delay=max_delay,
                exponential_base=exponential_base,
                jitter=jitter,
                retryable_exceptions=retryable_exceptions
            )
            return handler.execute_with_retry(func, *args, **kwargs)

        return wrapper

    return decorator


class CircuitBreaker:
    """
    Circuit breaker pattern implementation

    Prevents repeated calls to failing services by "opening the circuit"
    after a threshold of failures.

    States:
    - CLOSED: Normal operation, requests pass through
    - OPEN: Circuit is open, requests fail immediately
    - HALF_OPEN: Testing if service recovered
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        expected_exception: Type[Exception] = Exception
    ):
        """
        Initialize circuit breaker

        Args:
            failure_threshold: Number of failures before opening circuit
            recovery_timeout: Time to wait before attempting recovery (seconds)
            expected_exception: Exception type to count as failure
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception

        # State
        self.failure_count = 0
        self.last_failure_time: Optional[float] = None
        self.state = 'CLOSED'  # CLOSED, OPEN, HALF_OPEN

        logger.info(
            f"CircuitBreaker initialized: threshold={failure_threshold}, "
            f"timeout={recovery_timeout}s"
        )

    def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute function with circuit breaker protection

        Args:
            func: Function to execute
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            Function result

        Raises:
            Exception: If circuit is open or function fails
        """
        # Check if we should attempt recovery
        if self.state == 'OPEN':
            if self._should_attempt_reset():
                self.state = 'HALF_OPEN'
                logger.info("Circuit breaker entering HALF_OPEN state")
            else:
                raise Exception(
                    f"Circuit breaker is OPEN. Service unavailable. "
                    f"Retry after {self.recovery_timeout}s"
                )

        try:
            result = func(*args, **kwargs)

            # Success - reset on HALF_OPEN
            if self.state == 'HALF_OPEN':
                self._reset()
                logger.info("Circuit breaker reset to CLOSED after successful call")

            return result

        except self.expected_exception as e:
            self._record_failure()
            raise

    def _record_failure(self) -> None:
        """Record a failure and potentially open circuit"""
        self.failure_count += 1
        self.last_failure_time = time.time()

        if self.failure_count >= self.failure_threshold:
            self.state = 'OPEN'
            logger.warning(
                f"Circuit breaker OPENED after {self.failure_count} failures"
            )

    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt reset"""
        if self.last_failure_time is None:
            return False

        return (time.time() - self.last_failure_time) >= self.recovery_timeout

    def _reset(self) -> None:
        """Reset circuit breaker to closed state"""
        self.failure_count = 0
        self.state = 'CLOSED'
        self.last_failure_time = None

    def get_state(self) -> dict:
        """
        Get current circuit breaker state

        Returns:
            Dictionary with state information
        """
        return {
            'state': self.state,
            'failure_count': self.failure_count,
            'failure_threshold': self.failure_threshold,
            'last_failure_time': self.last_failure_time,
        }
