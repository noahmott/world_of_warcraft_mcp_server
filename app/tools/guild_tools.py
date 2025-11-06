"""
Guild analysis and management tools for WoW Guild MCP Server
"""

import json
from datetime import datetime, timezone
from typing import Dict, Any, List

from .base import mcp_tool, with_supabase_logging, get_or_initialize_services
from ..api.blizzard_client import BlizzardAPIClient
from ..core.constants import KNOWN_CLASSIC_REALMS
from ..utils.logging_utils import get_logger
from ..utils.datetime_utils import utc_now, utc_now_iso
from ..utils.response_utils import success_response, error_response

logger = get_logger(__name__)


@mcp_tool()
@with_supabase_logging
async def get_guild_member_list(
    realm: str,
    guild_name: str,
    sort_by: str = "guild_rank",
    limit: int = 50,
    quick_mode: bool = False,
    game_version: str = "retail"
) -> Dict[str, Any]:
    """
    Get detailed guild member list with sorting options
    
    Args:
        realm: Server realm
        guild_name: Guild name
        sort_by: Sort criteria ('guild_rank', 'level', 'name', 'last_login')
        limit: Maximum number of members to return
        quick_mode: Use optimized fetcher for faster results
        game_version: WoW version ('retail' or 'classic')
    
    Returns:
        Detailed member list with metadata
    """
    try:
        logger.info(f"Getting member list for {guild_name} on {realm} ({game_version})")
        
        # Initialize services if needed
        service_mgr = await get_or_initialize_services()
        redis_client = service_mgr.redis_client
        
        # Check Redis cache first
        cache_key = f"guild_roster:{game_version}:{realm}:{guild_name.lower()}"
        cached_data = None
        cache_age_days = None
        
        if redis_client:
            try:
                # Get cached data
                cached_json = await redis_client.get(cache_key)
                if cached_json:
                    cached_data = json.loads(cached_json.decode())  # Decode bytes to string
                    
                    # Check cache age
                    stored_date = datetime.fromisoformat(cached_data.get("cached_at", ""))
                    cache_age = utc_now() - stored_date
                    cache_age_days = cache_age.days
                    
                    # If cache is less than 15 days old, use it
                    if cache_age_days < 15:
                        logger.info(f"Using cached guild roster (age: {cache_age_days} days)")
                        
                        # Extract members and apply sorting/limit
                        members = cached_data["members"][:limit]
                        
                        # Sort members based on criteria
                        if sort_by == "guild_rank":
                            members.sort(key=lambda x: x.get("guild_rank", 999))
                        elif sort_by == "level":
                            members.sort(key=lambda x: x.get("level", 0), reverse=True)
                        elif sort_by == "name":
                            members.sort(key=lambda x: x.get("name", "").lower())
                        
                        return {
                            "success": True,
                            "guild_name": guild_name,
                            "realm": realm,
                            "members": members,
                            "members_returned": len(members),
                            "total_members": cached_data["total_members"],
                            "sorted_by": sort_by,
                            "quick_mode": quick_mode,
                            "guild_summary": cached_data.get("guild_info", {}),
                            "from_cache": True,
                            "cache_age_days": cache_age_days,
                            "timestamp": utc_now_iso()
                        }
                    else:
                        logger.info(f"Cache too old ({cache_age_days} days), fetching fresh data")
            except Exception as e:
                logger.warning(f"Error reading cache: {e}")
        
        # Default API-based fetching
        async with BlizzardAPIClient(game_version=game_version) as client:
            # Get guild roster
            roster = await client.get_guild_roster(realm, guild_name)
            
            if not roster.get("members"):
                return error_response("No members found or guild not found")
            
            # Sort and limit members
            members = roster["members"][:limit]
            
            # Sort members based on criteria
            if sort_by == "guild_rank":
                members.sort(key=lambda x: x.get("rank", 999))
            elif sort_by == "level":
                members.sort(key=lambda x: x.get("character", {}).get("level", 0), reverse=True)
            elif sort_by == "name":
                members.sort(key=lambda x: x.get("character", {}).get("name", "").lower())
            
            # Prepare member list with extracted info
            member_list = []
            for member in members:
                character = member.get("character", {})
                member_info = {
                    "name": character.get("name", "Unknown"),
                    "level": character.get("level", 0),
                    "class": character.get("playable_class", {}).get("name", "Unknown"),
                    "race": character.get("playable_race", {}).get("name", "Unknown"),
                    "guild_rank": member.get("rank", 999),
                    "realm": character.get("realm", {}).get("name", realm)
                }
                member_list.append(member_info)
            
            return {
                "success": True,
                "guild_name": guild_name,
                "realm": realm,
                "members": member_list,
                "members_returned": len(member_list),
                "total_members": len(roster["members"]),
                "sorted_by": sort_by,
                "quick_mode": quick_mode,
                "from_cache": False,
                "timestamp": utc_now_iso()
            }
            
    except Exception as e:
        logger.error(f"Error getting guild member list: {str(e)}")
        return error_response(str(e))