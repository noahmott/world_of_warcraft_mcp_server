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
redis_client = None
activity_logger = None
supabase_client = None
streaming_service = None


def set_mcp_instance(mcp_instance):
    """Set the global MCP instance for tools to use"""
    global mcp
    mcp = mcp_instance


def set_service_instances(redis=None, activity=None, supabase=None, streaming=None):
    """Set global service instances for tools to use"""
    global redis_client, activity_logger, supabase_client, streaming_service
    if redis:
        redis_client = redis
    if activity:
        activity_logger = activity
    if supabase:
        supabase_client = supabase
    if streaming:
        streaming_service = streaming


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

        # Extract OAuth user information using FastMCP's get_access_token()
        oauth_provider = None
        oauth_user_id = None
        user_info = None

        try:
            from fastmcp.server.dependencies import get_access_token

            # Get the access token from FastMCP
            access_token = get_access_token()

            if access_token and access_token.claims:
                user_info = access_token.claims

                # Extract provider and user ID from claims
                # Discord user structure: {id, username, email, ...}
                # Google user structure: {sub, email, name, ...}
                oauth_user_id = user_info.get('id') or user_info.get('sub')

                # Determine provider from issuer or audience in claims
                issuer = user_info.get('iss', '')
                audience = user_info.get('aud', '')

                if 'discord' in issuer or 'discord' in audience:
                    oauth_provider = 'discord'
                elif 'google' in issuer or 'google' in audience:
                    oauth_provider = 'google'

                logger.debug(f"Authenticated user: {oauth_provider}/{oauth_user_id}")
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
                user_info=user_info
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
                user_info=user_info
            )

            raise

    return wrapper


async def log_to_supabase(tool_name: str, request_data: Dict[str, Any],
                         response_data: Optional[Dict[str, Any]] = None,
                         error_message: Optional[str] = None,
                         duration_ms: Optional[float] = None,
                         oauth_provider: Optional[str] = None,
                         oauth_user_id: Optional[str] = None,
                         user_info: Optional[Dict[str, Any]] = None):
    """Log activity to Supabase with OAuth user tracking"""
    try:
        if not supabase_client:
            logger.debug("Supabase client not available - skipping log")
            return

        from ..services.supabase_client import ActivityLogEntry

        # Track user if OAuth info is available
        user_id = None

        if oauth_provider and oauth_user_id and user_info:
            try:
                # Upsert user in database
                user_data = {
                    "email": user_info.get('email'),
                    "username": user_info.get('username') or user_info.get('name'),
                    "display_name": user_info.get('global_name') or user_info.get('display_name') or user_info.get('name'),
                    "avatar_url": user_info.get('avatar')
                }

                user_id = await supabase_client.upsert_user(
                    oauth_provider=oauth_provider,
                    oauth_user_id=oauth_user_id,
                    user_data=user_data
                )

                if user_id:
                    logger.debug(f"Tracked user {user_id} ({oauth_provider}/{oauth_user_id})")
            except Exception as e:
                logger.error(f"Failed to track user: {e}")
                # Continue with logging even if user tracking fails

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
                "authenticated": user_id is not None
            }
        )

        # Stream to Supabase
        success = await supabase_client.stream_activity_log(log_entry)
        if success:
            logger.debug(f"Successfully logged {tool_name} to Supabase with user tracking")
        else:
            logger.warning(f"Failed to log {tool_name} to Supabase - no error thrown")

    except Exception as e:
        logger.error(f"Failed to log to Supabase: {e}")
        pass


async def get_or_initialize_services():
    """Get or initialize required services"""
    from ..core.service_manager import get_service_manager
    
    service_mgr = await get_service_manager()
    
    global redis_client, activity_logger, supabase_client, streaming_service
    redis_client = service_mgr.redis_client
    activity_logger = service_mgr.activity_logger
    supabase_client = service_mgr.supabase_client
    streaming_service = service_mgr.streaming_service
    
    return service_mgr