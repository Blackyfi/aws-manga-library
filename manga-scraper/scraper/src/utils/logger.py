"""
Logger Configuration
====================

Centralized logging configuration for the manga scraper.
"""

import logging
import sys
from typing import Optional
from logging.handlers import RotatingFileHandler
import os


def setup_logger(
    name: str = 'manga_scraper',
    level: str = 'INFO',
    log_file: Optional[str] = None,
    log_to_console: bool = True,
    log_format: Optional[str] = None,
    max_file_size: int = 10 * 1024 * 1024,  # 10 MB
    backup_count: int = 5
) -> logging.Logger:
    """
    Setup and configure logger

    Args:
        name: Logger name
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional file path for file logging
        log_to_console: Whether to log to console
        log_format: Custom log format string
        max_file_size: Maximum log file size before rotation (bytes)
        backup_count: Number of backup files to keep

    Returns:
        Configured logger instance
    """
    # Create logger
    logger = logging.getLogger(name)

    # Clear existing handlers to avoid duplicates
    logger.handlers.clear()

    # Set level
    log_level = getattr(logging, level.upper(), logging.INFO)
    logger.setLevel(log_level)

    # Default format
    if log_format is None:
        log_format = (
            '%(asctime)s - %(name)s - %(levelname)s - '
            '%(filename)s:%(lineno)d - %(message)s'
        )

    formatter = logging.Formatter(log_format)

    # Console handler
    if log_to_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(log_level)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    # File handler with rotation
    if log_file:
        # Create directory if it doesn't exist
        log_dir = os.path.dirname(log_file)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir)

        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=max_file_size,
            backupCount=backup_count
        )
        file_handler.setLevel(log_level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    # Prevent propagation to root logger
    logger.propagate = False

    logger.info(f"Logger '{name}' initialized with level {level}")

    return logger


def get_logger(name: str = 'manga_scraper') -> logging.Logger:
    """
    Get existing logger or create new one with default settings

    Args:
        name: Logger name

    Returns:
        Logger instance
    """
    logger = logging.getLogger(name)

    # If logger has no handlers, set it up with defaults
    if not logger.handlers:
        setup_logger(name)

    return logger


def set_log_level(logger: logging.Logger, level: str) -> None:
    """
    Change log level for logger and all its handlers

    Args:
        logger: Logger instance
        level: New log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    log_level = getattr(logging, level.upper(), logging.INFO)
    logger.setLevel(log_level)

    for handler in logger.handlers:
        handler.setLevel(log_level)

    logger.info(f"Log level changed to {level}")


class LoggerContext:
    """
    Context manager for temporary log level changes

    Example:
        with LoggerContext(logger, 'DEBUG'):
            # Code with DEBUG logging
            pass
        # Back to original level
    """

    def __init__(self, logger: logging.Logger, level: str):
        """
        Initialize logger context

        Args:
            logger: Logger instance
            level: Temporary log level
        """
        self.logger = logger
        self.new_level = getattr(logging, level.upper(), logging.INFO)
        self.original_level = logger.level

    def __enter__(self):
        """Enter context - set new level"""
        self.logger.setLevel(self.new_level)
        for handler in self.logger.handlers:
            handler.setLevel(self.new_level)
        return self.logger

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context - restore original level"""
        self.logger.setLevel(self.original_level)
        for handler in self.logger.handlers:
            handler.setLevel(self.original_level)


class StructuredLogger:
    """
    Structured logging wrapper for JSON-formatted logs

    Useful for log aggregation systems (CloudWatch, ELK, etc.)
    """

    def __init__(self, logger: logging.Logger):
        """
        Initialize structured logger

        Args:
            logger: Base logger instance
        """
        self.logger = logger

    def log(
        self,
        level: str,
        message: str,
        **kwargs
    ) -> None:
        """
        Log structured message

        Args:
            level: Log level
            message: Log message
            **kwargs: Additional structured fields
        """
        import json

        log_data = {
            'message': message,
            **kwargs
        }

        log_level = getattr(logging, level.upper(), logging.INFO)
        self.logger.log(log_level, json.dumps(log_data))

    def info(self, message: str, **kwargs) -> None:
        """Log info message"""
        self.log('INFO', message, **kwargs)

    def debug(self, message: str, **kwargs) -> None:
        """Log debug message"""
        self.log('DEBUG', message, **kwargs)

    def warning(self, message: str, **kwargs) -> None:
        """Log warning message"""
        self.log('WARNING', message, **kwargs)

    def error(self, message: str, **kwargs) -> None:
        """Log error message"""
        self.log('ERROR', message, **kwargs)

    def critical(self, message: str, **kwargs) -> None:
        """Log critical message"""
        self.log('CRITICAL', message, **kwargs)


# CloudWatch Logs handler for AWS Lambda
try:
    import watchtower

    def setup_cloudwatch_logger(
        logger_name: str,
        log_group: str,
        log_stream: Optional[str] = None,
        region: str = 'eu-west-3',
        level: str = 'INFO'
    ) -> logging.Logger:
        """
        Setup logger with CloudWatch Logs handler

        Args:
            logger_name: Logger name
            log_group: CloudWatch log group name
            log_stream: CloudWatch log stream name (auto-generated if None)
            region: AWS region
            level: Log level

        Returns:
            Logger with CloudWatch handler
        """
        logger = get_logger(logger_name)

        # Add CloudWatch handler
        cloudwatch_handler = watchtower.CloudWatchLogHandler(
            log_group=log_group,
            stream_name=log_stream,
            use_queues=True,
            create_log_group=True
        )

        log_level = getattr(logging, level.upper(), logging.INFO)
        cloudwatch_handler.setLevel(log_level)

        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        cloudwatch_handler.setFormatter(formatter)

        logger.addHandler(cloudwatch_handler)
        logger.info(f"CloudWatch logging enabled for log group: {log_group}")

        return logger

except ImportError:
    # watchtower not available
    def setup_cloudwatch_logger(*args, **kwargs):
        """Fallback when watchtower is not installed"""
        logger = get_logger(kwargs.get('logger_name', 'manga_scraper'))
        logger.warning("watchtower not installed, CloudWatch logging unavailable")
        return logger


# Configure default logger for the package
default_logger = setup_logger(
    name='manga_scraper',
    level=os.environ.get('LOG_LEVEL', 'INFO'),
    log_to_console=True
)
