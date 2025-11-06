"""
Centralized datetime utilities for consistent timestamp handling across the application
"""

from datetime import datetime, timezone, timedelta
from typing import Optional


def utc_now() -> datetime:
    """
    Get current UTC datetime

    Returns:
        Current datetime in UTC timezone
    """
    return datetime.now(timezone.utc)


def utc_now_iso() -> str:
    """
    Get current UTC datetime as ISO 8601 string

    Returns:
        Current UTC datetime formatted as ISO string
    """
    return datetime.now(timezone.utc).isoformat()


def days_ago(days: int) -> datetime:
    """
    Get datetime N days ago from now in UTC

    Args:
        days: Number of days to subtract from current time

    Returns:
        UTC datetime N days in the past
    """
    return datetime.now(timezone.utc) - timedelta(days=days)


def hours_ago(hours: int) -> datetime:
    """
    Get datetime N hours ago from now in UTC

    Args:
        hours: Number of hours to subtract from current time

    Returns:
        UTC datetime N hours in the past
    """
    return datetime.now(timezone.utc) - timedelta(hours=hours)


def minutes_ago(minutes: int) -> datetime:
    """
    Get datetime N minutes ago from now in UTC

    Args:
        minutes: Number of minutes to subtract from current time

    Returns:
        UTC datetime N minutes in the past
    """
    return datetime.now(timezone.utc) - timedelta(minutes=minutes)


def to_iso(dt: datetime) -> str:
    """
    Convert datetime to ISO 8601 string

    Args:
        dt: Datetime object to convert

    Returns:
        ISO 8601 formatted string
    """
    return dt.isoformat()


def from_iso(iso_string: str) -> datetime:
    """
    Parse ISO 8601 string to datetime

    Args:
        iso_string: ISO formatted datetime string

    Returns:
        Parsed datetime object
    """
    return datetime.fromisoformat(iso_string)


def timestamp_ms() -> int:
    """
    Get current Unix timestamp in milliseconds

    Returns:
        Current time as milliseconds since epoch
    """
    return int(datetime.now(timezone.utc).timestamp() * 1000)


def format_duration_ms(start_time: datetime, end_time: Optional[datetime] = None) -> float:
    """
    Calculate duration in milliseconds between two datetimes

    Args:
        start_time: Start datetime
        end_time: End datetime (defaults to now if not provided)

    Returns:
        Duration in milliseconds
    """
    if end_time is None:
        end_time = utc_now()
    return (end_time - start_time).total_seconds() * 1000
