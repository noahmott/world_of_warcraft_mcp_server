"""
Base functionality for MCP tools including decorators and shared utilities
"""

import functools
import time
import uuid
from typing import Any, Dict, Callable, Optional

from ..utils.logging_utils import get_logger
from ..utils.datetime_utils import utc_now_iso

logger = get_logger(__name__)

# Global service references
mcp = None
supabase_client = None


def set_mcp_instance(mcp_instance):
    """Set the global MCP instance for tools to use"""
    global mcp
    mcp = mcp_instance


def set_service_instances(supabase=None):
    """Set global service instances for tools to use"""
    global supabase_client
    if supabase:
        supabase_client = supabase


def mcp_tool(*args, **kwargs):
    """Wrapper for mcp.tool() decorator that uses the global mcp instance"""
    def decorator(func):
        if mcp is None:
            raise RuntimeError("MCP instance not set. Call set_mcp_instance() first.")
        return mcp.tool(*args, **kwargs)(func)
    
    if args and callable(args[0]):
        return decorator(args[0])
    return decorator


def with_error_handling(func: Callable) -> Callable:
    """Decorator to add standard error handling to tool functions"""
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            logger.error(f"Error in {func.__name__}: {str(e)}", exc_info=True)
            return {"error": f"Tool execution failed: {str(e)}"}
    return wrapper


def with_supabase_logging(func: Callable) -> Callable:
    """Decorator to add Supabase activity logging to MCP tools with OAuth user tracking"""
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        start_time = time.time()
        error_message = None
        response_data = None

        # Extract OAuth user information from HTTP headers (same as 795b2c3)
        user_info = None
        oauth_provider = None
        oauth_user_id = None
        db_user_id = None

        try:
            from fastmcp.server.dependencies import get_http_headers
            import httpx

            # Get HTTP headers to extract the Authorization token
            headers = get_http_headers(include_all=True)
            auth_header = headers.get("authorization", "")

            if auth_header.startswith("Bearer "):
                token = auth_header[7:]  # Remove "Bearer " prefix

                # Call Discord API directly to get user info
                try:
                    async with httpx.AsyncClient() as client:
                        response = await client.get(
                            "https://discord.com/api/v10/users/@me",
                            headers={"Authorization": f"Bearer {token}"},
                            timeout=10.0
                        )
                        if response.status_code == 200:
                            user_data = response.json()
                            oauth_user_id = user_data.get("id")
                            oauth_provider = "discord"
                            user_info = user_data

                            logger.info(f"Authenticated user: {oauth_provider}/{oauth_user_id}")

                            # Look up the db user_id from Supabase
                            if supabase_client:
                                try:
                                    result = await supabase_client.client.table("users").select("id").eq("oauth_provider", oauth_provider).eq("oauth_user_id", oauth_user_id).execute()
                                    if result.data and len(result.data) > 0:
                                        db_user_id = result.data[0]['id']
                                        logger.info(f"Found db user_id: {db_user_id}")
                                except Exception as e:
                                    logger.warning(f"Failed to lookup user in database: {e}")
                except Exception as e:
                    logger.warning(f"Failed to verify token with Discord API: {e}")
        except Exception as e:
            logger.debug(f"Failed to extract user context: {e}")

        request_data = {}
        import inspect
        sig = inspect.signature(func)
        bound_args = sig.bind(*args, **kwargs)
        bound_args.apply_defaults()

        for param_name, param_value in bound_args.arguments.items():
            if param_name not in ['self', 'cls', 'ctx']:
                request_data[param_name] = param_value

        try:
            result = await func(*args, **kwargs)
            response_data = result

            await log_to_supabase(
                tool_name=func.__name__,
                request_data=request_data,
                response_data=response_data,
                duration_ms=(time.time() - start_time) * 1000,
                oauth_provider=oauth_provider,
                oauth_user_id=oauth_user_id,
                user_info=user_info,
                db_user_id=db_user_id
            )

            return result

        except Exception as e:
            error_message = str(e)

            await log_to_supabase(
                tool_name=func.__name__,
                request_data=request_data,
                error_message=error_message,
                duration_ms=(time.time() - start_time) * 1000,
                oauth_provider=oauth_provider,
                oauth_user_id=oauth_user_id,
                user_info=user_info,
                db_user_id=db_user_id
            )

            raise

    return wrapper


async def log_to_supabase(tool_name: str, request_data: Dict[str, Any],
                         response_data: Optional[Dict[str, Any]] = None,
                         error_message: Optional[str] = None,
                         duration_ms: Optional[float] = None,
                         oauth_provider: Optional[str] = None,
                         oauth_user_id: Optional[str] = None,
                         user_info: Optional[Dict[str, Any]] = None,
                         db_user_id: Optional[str] = None):
    """Log activity to Supabase with OAuth user tracking"""
    try:
        if not supabase_client:
            logger.debug("Supabase client not available - skipping log")
            return

        from ..services.supabase_client import ActivityLogEntry

        # Use provided db_user_id directly (already looked up in decorator)
        user_id = db_user_id

        # Create activity log entry with user tracking
        log_entry = ActivityLogEntry(
            id=str(uuid.uuid4()),
            session_id="fastmcp-direct",
            activity_type="tool_call" if not error_message else "tool_error",
            timestamp=utc_now_iso(),
            tool_name=tool_name,
            request_data=request_data,
            response_data=response_data,
            error_message=error_message,
            duration_ms=duration_ms,
            user_id=user_id,
            metadata={
                "source": "fastmcp",
                "direct_logging": True,
                "authenticated": user_id is not None,
                "oauth_provider": oauth_provider
            }
        )

        # Stream to Supabase
        success = await supabase_client.stream_activity_log(log_entry)
        if success:
            logger.debug(f"Successfully logged {tool_name} to Supabase with user_id: {user_id}")
        else:
            logger.warning(f"Failed to log {tool_name} to Supabase - no error thrown")

    except Exception as e:
        logger.error(f"Failed to log to Supabase: {e}")
        pass


async def get_or_initialize_services():
    """Get or initialize required services"""
    from ..core.service_manager import get_service_manager

    service_mgr = await get_service_manager()

    global supabase_client
    supabase_client = service_mgr.supabase_client

    return service_mgr