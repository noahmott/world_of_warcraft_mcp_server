"""
WoW Guild MCP Server using FastMCP 2.0 with HTTP transport for Heroku

A comprehensive World of Warcraft guild analytics MCP server that provides:
- Guild performance analysis and member statistics
- Auction house data aggregation and market insights
- Real-time activity logging to Supabase
- Chart generation for raid progress and member comparisons
- Classic and Retail WoW support with proper namespace handling
"""

# Standard library imports
import httpx
import json
import os
import functools
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional, Union

# Third-party imports
import redis.asyncio as aioredis
from dotenv import load_dotenv
from fastmcp import FastMCP
from fastmcp.server.dependencies import get_http_headers

# Local imports - API clients
from .api.blizzard_client import BlizzardAPIClient, BlizzardAPIError
from .api.guild_optimizations import OptimizedGuildFetcher

# Local imports - Services
from .services.activity_logger import ActivityLogger, initialize_activity_logger
from .services.auction_aggregator import AuctionAggregatorService
from .services.market_history import MarketHistoryService
from .services.supabase_client import SupabaseRealTimeClient
from .services.supabase_streaming import initialize_streaming_service

# Local imports - Visualization
from .visualization.chart_generator import ChartGenerator

# Local imports - Utils
from .utils.datetime_utils import utc_now, utc_now_iso, format_duration_ms
from .utils.logging_utils import setup_logging, get_logger

# Local imports - Core
from .core.constants import KNOWN_RETAIL_REALMS, KNOWN_CLASSIC_REALMS

# Load environment variables
load_dotenv()

# Configure logging
setup_logging()
logger = get_logger(__name__)

# Initialize OAuth authentication (if configured)
from .core.auth import create_oauth_provider, get_auth_info

auth_provider = create_oauth_provider()
auth_info = get_auth_info()

if auth_info['enabled']:
    logger.info(f"OAuth authentication enabled with provider: {auth_info['provider']}")
    logger.info(f"OAuth base URL: {auth_info['base_url']}")
    logger.info(f"OAuth scopes: {', '.join(auth_info['scopes'])}")
else:
    logger.info("OAuth authentication is disabled - server running in public mode")

# Create FastMCP server with OAuth authentication (if enabled)
mcp: FastMCP = FastMCP("WoW Guild Analytics MCP", auth=auth_provider)

# Initialize service instances
chart_generator = ChartGenerator()
auction_aggregator = AuctionAggregatorService()
market_history = MarketHistoryService()

# Global instances for Redis and logging
redis_client: Optional[aioredis.Redis] = None
activity_logger: Optional[ActivityLogger] = None
streaming_service = None
supabase_client: Optional[SupabaseRealTimeClient] = None


# ============================================================================
# SERVICE INITIALIZATION
# ============================================================================

async def get_or_initialize_services():
    """Lazy initialization of Redis, activity logger, and Supabase"""
    global redis_client, activity_logger, streaming_service, supabase_client

    # Return if Redis and activity logger already initialized
    if redis_client and activity_logger:
        return

    try:
        # Initialize Redis connection
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")

        # Configure SSL for Heroku Redis
        if redis_url.startswith("rediss://"):
            logger.info("Configuring Redis with TLS for Heroku")
            redis_client = await aioredis.from_url(
                redis_url,
                encoding="utf-8",
                decode_responses=False,
                max_connections=50,
                ssl_cert_reqs=None
            )
        else:
            redis_client = await aioredis.from_url(
                redis_url,
                encoding="utf-8",
                decode_responses=False,
                max_connections=50
            )

        # Test Redis connection
        await redis_client.ping()
        logger.info(f"Connected to Redis at {redis_url}")

        # Initialize activity logger
        activity_logger = await initialize_activity_logger(redis_client)
        logger.info("Activity logger initialized")

        # Initialize Supabase
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_SERVICE_KEY")

        if not supabase_key:
            raise ValueError("SUPABASE_SERVICE_KEY environment variable is required")

        if supabase_url and supabase_key:
            try:
                # Initialize direct Supabase client with service role key
                if not supabase_client:
                    supabase_client = SupabaseRealTimeClient(supabase_url, supabase_key)
                    await supabase_client.initialize()
                    logger.info("Supabase direct client initialized successfully")

                    # Set Supabase client for OAuth token verifier
                    from .core.discord_token_verifier import set_supabase_client
                    set_supabase_client(supabase_client)
                    logger.info("Supabase client set for OAuth user tracking")

                # Initialize streaming service
                streaming_service = await initialize_streaming_service(redis_client)
                logger.info("Supabase streaming service initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize Supabase services: {e}")
                streaming_service = None
                supabase_client = None
        else:
            logger.warning("Supabase environment variables not set - logging to Supabase disabled")

    except Exception as e:
        logger.error(f"Failed to initialize services: {e}")


async def log_to_supabase(
    tool_name: str,
    request_data: Dict[str, Any],
    response_data: Optional[Dict[str, Any]] = None,
    error_message: Optional[str] = None,
    duration_ms: Optional[int] = None,
    oauth_provider: Optional[str] = None,
    oauth_user_id: Optional[str] = None,
    user_info: Optional[Dict[str, Any]] = None,
    db_user_id: Optional[str] = None
):
    """Log tool usage to Supabase with user tracking"""
    try:
        if not supabase_client or not supabase_client.client:
            return

        from .services.supabase_client import ActivityLogEntry
        import uuid

        log_entry = ActivityLogEntry(
            id=str(uuid.uuid4()),
            session_id=db_user_id or "anonymous",
            activity_type="mcp_tool_call",
            timestamp=utc_now_iso(),
            tool_name=tool_name,
            request_data=request_data,
            response_data=response_data or {},
            metadata={
                "oauth_provider": oauth_provider,
                "oauth_user_id": oauth_user_id,
                "db_user_id": db_user_id,
                "duration_ms": duration_ms,
                "error": error_message,
                "user_info": user_info
            }
        )

        success = await supabase_client.stream_activity_log(log_entry)

        if success:
            logger.debug(f"Successfully logged {tool_name} to Supabase with user tracking")
        else:
            logger.warning(f"Failed to log {tool_name} to Supabase - no error thrown")

    except Exception as e:
        logger.error(f"Failed to log to Supabase: {e}")


def with_supabase_logging(func):
    """Decorator to automatically log tool calls to Supabase with user tracking"""

    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        logger.info(f"=== with_supabase_logging wrapper called for {func.__name__} ===")

        start_time = utc_now()
        tool_name = func.__name__

        # Extract OAuth user information from HTTP headers
        user_info = None
        oauth_provider = None
        oauth_user_id = None
        db_user_id = None

        try:
            headers = get_http_headers()
            auth_header = headers.get("authorization", "")

            if auth_header.startswith("Bearer "):
                token = auth_header[7:]
                logger.info("Found Bearer token in Authorization header")

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
                            await get_or_initialize_services()
                            if supabase_client and supabase_client.client:
                                try:
                                    result = await supabase_client.client.table("users").select("id").eq("oauth_provider", oauth_provider).eq("oauth_user_id", oauth_user_id).execute()
                                    if result.data and len(result.data) > 0:
                                        user_record = result.data[0]
                                        if isinstance(user_record, dict) and 'id' in user_record:
                                            db_user_id = str(user_record['id'])
                                            logger.info(f"Found db user_id: {db_user_id}")
                                except Exception as e:
                                    logger.warning(f"Failed to lookup user in database: {e}")
                except Exception as e:
                    logger.warning(f"Failed to verify token with Discord API: {e}")
        except Exception as e:
            logger.warning(f"Failed to extract user context: {e}", exc_info=True)

        # Try to initialize services and log
        try:
            await get_or_initialize_services()
            await log_to_supabase(
                tool_name=tool_name,
                request_data=kwargs,
                oauth_provider=oauth_provider,
                oauth_user_id=oauth_user_id,
                user_info=user_info,
                db_user_id=db_user_id
            )
        except Exception as e:
            logger.debug(f"Failed to initialize services or log request for {tool_name}: {e}")

        try:
            # Call the actual function
            result = await func(*args, **kwargs)

            # Try to log successful response
            try:
                duration_ms = format_duration_ms(start_time)
                await log_to_supabase(
                    tool_name=tool_name,
                    request_data=kwargs,
                    response_data={"success": True},
                    duration_ms=duration_ms,
                    oauth_provider=oauth_provider,
                    oauth_user_id=oauth_user_id,
                    user_info=user_info,
                    db_user_id=db_user_id
                )
            except Exception as e:
                logger.debug(f"Failed to log success for {tool_name}: {e}")

            return result

        except Exception as e:
            # Try to log error
            try:
                await log_to_supabase(
                    tool_name=tool_name,
                    request_data=kwargs,
                    error_message=str(e),
                    oauth_provider=oauth_provider,
                    oauth_user_id=oauth_user_id,
                    db_user_id=db_user_id,
                    user_info=user_info
                )
            except Exception as log_error:
                logger.debug(f"Failed to log error for {tool_name}: {log_error}")
            raise

    return wrapper


# ============================================================================
# MCP TOOL DEFINITIONS - 8 CONSOLIDATED TOOLS
# ============================================================================

# Set MCP instance for tool modules before importing
from .tools.base import set_mcp_instance
set_mcp_instance(mcp)

# Import tool implementations from modules
from .tools import guild_tools, member_tools, realm_tools, item_tools, auction_tools, visualization_tools


# 1. GUILD TOOL
@mcp.tool()
@with_supabase_logging
async def get_guild_member_list(
    realm: str,
    guild_name: str,
    sort_by: str = "guild_rank",
    limit: int = 50,
    quick_mode: bool = False,
    game_version: str = "retail"
) -> Dict[str, Any]:
    """Get list of guild members with their basic information"""
    return await guild_tools.get_guild_member_list(
        realm=realm,
        guild_name=guild_name,
        sort_by=sort_by,
        limit=limit,
        quick_mode=quick_mode,
        game_version=game_version
    )


# 2. CHARACTER TOOL
@mcp.tool()
@with_supabase_logging
async def get_character_details(
    realm: str,
    character_name: str,
    sections: List[str] = ["profile", "equipment", "specializations"],
    game_version: str = "retail"
) -> Dict[str, Any]:
    """Get detailed character information"""
    return await member_tools.get_character_details(
        realm=realm,
        character_name=character_name,
        sections=sections,
        game_version=game_version
    )


# 3. REALM TOOL
@mcp.tool()
@with_supabase_logging
async def get_realm_info(
    realm: str,
    game_version: str = "retail",
    include_status: bool = True
) -> Dict[str, Any]:
    """Get realm information including connected realm ID"""
    return await realm_tools.get_realm_info(
        realm=realm,
        game_version=game_version,
        include_status=include_status
    )


# 4. ITEM TOOL
@mcp.tool()
@with_supabase_logging
async def lookup_items(
    item_ids: Union[int, List[int]],
    game_version: str = "retail",
    detailed: bool = True
) -> Dict[str, Any]:
    """Look up WoW item details by ID(s)"""
    return await item_tools.lookup_items(
        item_ids=item_ids,
        game_version=game_version,
        detailed=detailed
    )


# 5-6. AUCTION/MARKET TOOLS
@mcp.tool()
@with_supabase_logging
async def get_market_data(
    realm: str,
    item_ids: Optional[List[int]] = None,
    include_trends: bool = False,
    trend_hours: int = 24,
    max_results: int = 100,
    game_version: str = "retail"
) -> Dict[str, Any]:
    """Get current auction house data with optional historical trends"""
    return await auction_tools.get_market_data(
        realm=realm,
        item_ids=item_ids,
        include_trends=include_trends,
        trend_hours=trend_hours,
        max_results=max_results,
        game_version=game_version
    )


@mcp.tool()
@with_supabase_logging
async def analyze_market(
    realm: Optional[str] = None,
    min_profit_margin: float = 20.0,
    operation: str = "opportunities",
    check_hours: int = 24,
    realms: Optional[List[str]] = None,
    max_results: int = 20,
    game_version: str = "retail"
) -> Dict[str, Any]:
    """Perform market analysis operations (opportunities or health checks)"""
    return await auction_tools.analyze_market(
        realm=realm,
        min_profit_margin=min_profit_margin,
        operation=operation,
        check_hours=check_hours,
        realms=realms,
        max_results=max_results,
        game_version=game_version
    )


# 7-8. VISUALIZATION TOOLS
@mcp.tool()
@with_supabase_logging
async def generate_raid_progress_chart(
    realm: str,
    guild_name: str,
    raid_tier: str = "current",
    game_version: str = "retail"
) -> str:
    """Generate visual raid progression charts"""
    return await visualization_tools.generate_raid_progress_chart(
        realm=realm,
        guild_name=guild_name,
        raid_tier=raid_tier,
        game_version=game_version
    )


@mcp.tool()
@with_supabase_logging
async def compare_member_performance(
    realm: str,
    guild_name: str,
    member_names: List[str],
    metric: str = "item_level",
    game_version: str = "retail"
) -> Dict[str, Any]:
    """Compare performance metrics across guild members"""
    return await visualization_tools.compare_member_performance(
        realm=realm,
        guild_name=guild_name,
        member_names=member_names,
        metric=metric,
        game_version=game_version
    )


# ============================================================================
# SERVER STARTUP AND CONFIGURATION
# ============================================================================

def main():
    """Main entry point for FastMCP server"""
    try:
        # Check for required environment variables
        blizzard_client_id = os.getenv("BLIZZARD_CLIENT_ID")
        blizzard_client_secret = os.getenv("BLIZZARD_CLIENT_SECRET")

        if not blizzard_client_id or not blizzard_client_secret:
            raise ValueError("Blizzard API credentials not found in environment variables")

        port = int(os.getenv("PORT", "8000"))

        logger.info("WoW Guild MCP Server with FastMCP 2.0")
        logger.info("Tools: Guild analysis, visualization, and auction house")
        logger.info(f"Registered tools: {len(mcp._tool_manager._tools)}")
        logger.info(f"HTTP Server: 0.0.0.0:{port}")

        # Initialize services before starting server
        logger.info("Initializing services...")
        import asyncio as aio
        aio.run(get_or_initialize_services())
        logger.info("Services initialized")

        logger.info("Starting server...")

        # Run server using FastMCP 2.0 HTTP transport
        mcp.run(
            transport="http",
            host="0.0.0.0",
            port=port,
            path="/mcp"
        )

    except Exception as e:
        logger.error(f"Error starting server: {e}")
        import sys
        sys.exit(1)


if __name__ == "__main__":
    main()
