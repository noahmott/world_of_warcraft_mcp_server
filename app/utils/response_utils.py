"""
Standardized response formatting utilities for MCP tools

Provides consistent response structure across all tool endpoints
"""

from typing import Any, Dict, Optional
from .datetime_utils import utc_now_iso


def success_response(data: Optional[Dict[str, Any]] = None, **kwargs) -> Dict[str, Any]:
    """
    Create a standardized success response

    Args:
        data: Optional data dictionary to include in response
        **kwargs: Additional fields to include in response

    Returns:
        Standardized success response dictionary

    Example:
        >>> success_response({"count": 5}, message="Data retrieved")
        {"success": True, "timestamp": "2024-01-01T00:00:00Z", "count": 5, "message": "Data retrieved"}
    """
    response = {
        "success": True,
        "timestamp": utc_now_iso()
    }

    if data:
        response.update(data)

    if kwargs:
        response.update(kwargs)

    return response


def error_response(error: str, **kwargs) -> Dict[str, Any]:
    """
    Create a standardized error response

    Args:
        error: Error message describing what went wrong
        **kwargs: Additional fields to include in response

    Returns:
        Standardized error response dictionary

    Example:
        >>> error_response("Item not found", item_id=123)
        {"success": False, "error": "Item not found", "timestamp": "2024-01-01T00:00:00Z", "item_id": 123}
    """
    response = {
        "success": False,
        "error": error,
        "timestamp": utc_now_iso()
    }

    if kwargs:
        response.update(kwargs)

    return response


def api_error_response(exception: Exception, **kwargs) -> Dict[str, Any]:
    """
    Create a standardized API error response from an exception

    Args:
        exception: Exception that occurred
        **kwargs: Additional fields to include in response

    Returns:
        Standardized API error response dictionary

    Example:
        >>> api_error_response(BlizzardAPIError("Rate limited"))
        {"success": False, "error": "API Error: Rate limited", "timestamp": "..."}
    """
    error_msg = f"API Error: {str(exception)}"
    return error_response(error_msg, **kwargs)


def validation_error_response(field: str, message: str, **kwargs) -> Dict[str, Any]:
    """
    Create a standardized validation error response

    Args:
        field: Field that failed validation
        message: Validation error message
        **kwargs: Additional fields to include in response

    Returns:
        Standardized validation error response dictionary

    Example:
        >>> validation_error_response("realm", "Realm name cannot be empty")
        {"success": False, "error": "Validation error: realm - Realm name cannot be empty", ...}
    """
    error_msg = f"Validation error: {field} - {message}"
    return error_response(error_msg, field=field, **kwargs)


def not_found_response(resource: str, identifier: str, **kwargs) -> Dict[str, Any]:
    """
    Create a standardized "not found" error response

    Args:
        resource: Type of resource that wasn't found (e.g., "Guild", "Character")
        identifier: Identifier used to look up the resource
        **kwargs: Additional fields to include in response

    Returns:
        Standardized not found response dictionary

    Example:
        >>> not_found_response("Guild", "MyGuild on Stormrage")
        {"success": False, "error": "Guild not found: MyGuild on Stormrage", ...}
    """
    error_msg = f"{resource} not found: {identifier}"
    return error_response(error_msg, resource=resource, identifier=identifier, **kwargs)


def paginated_response(
    items: list,
    total_count: int,
    page: int = 1,
    page_size: int = 100,
    **kwargs
) -> Dict[str, Any]:
    """
    Create a standardized paginated response

    Args:
        items: List of items for current page
        total_count: Total number of items across all pages
        page: Current page number (1-indexed)
        page_size: Number of items per page
        **kwargs: Additional fields to include in response

    Returns:
        Standardized paginated response dictionary

    Example:
        >>> paginated_response([{"id": 1}, {"id": 2}], total_count=50, page=1, page_size=10)
        {
            "success": True,
            "timestamp": "...",
            "items": [...],
            "pagination": {
                "page": 1,
                "page_size": 10,
                "total_items": 50,
                "total_pages": 5,
                "has_next": True,
                "has_previous": False
            }
        }
    """
    total_pages = (total_count + page_size - 1) // page_size  # Ceiling division
    has_next = page < total_pages
    has_previous = page > 1

    response = success_response(
        {
            "items": items,
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total_items": total_count,
                "total_pages": total_pages,
                "has_next": has_next,
                "has_previous": has_previous
            }
        },
        **kwargs
    )

    return response
