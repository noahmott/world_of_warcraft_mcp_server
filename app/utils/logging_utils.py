"""
Centralized logging utilities for consistent logging configuration across the application
"""

import logging
from typing import Optional


def get_logger(name: str, level: Optional[int] = None) -> logging.Logger:
    """
    Get a configured logger instance

    Args:
        name: Logger name (typically __name__ from calling module)
        level: Optional logging level (defaults to None to use root logger level)

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    if level is not None:
        logger.setLevel(level)
    return logger


def setup_logging(level: int = logging.INFO, format_string: Optional[str] = None):
    """
    Configure application-wide logging

    Args:
        level: Logging level (default: INFO)
        format_string: Custom format string (optional)
    """
    if format_string is None:
        format_string = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

    logging.basicConfig(
        level=level,
        format=format_string,
        force=True  # Override any existing configuration
    )


# Convenience functions for common log levels
def get_debug_logger(name: str) -> logging.Logger:
    """Get logger with DEBUG level"""
    return get_logger(name, logging.DEBUG)


def get_info_logger(name: str) -> logging.Logger:
    """Get logger with INFO level"""
    return get_logger(name, logging.INFO)


def get_warning_logger(name: str) -> logging.Logger:
    """Get logger with WARNING level"""
    return get_logger(name, logging.WARNING)


def get_error_logger(name: str) -> logging.Logger:
    """Get logger with ERROR level"""
    return get_logger(name, logging.ERROR)
