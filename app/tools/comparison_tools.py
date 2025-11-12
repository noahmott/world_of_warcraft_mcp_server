"""
Guild data tools for WoW Guild MCP Server
"""

from typing import Dict, Any, List

from .base import mcp_tool, with_supabase_logging
from ..api.blizzard_client import BlizzardAPIClient, BlizzardAPIError
from ..utils.logging_utils import get_logger
from ..utils.response_utils import error_response

logger = get_logger(__name__)


@mcp_tool()
@with_supabase_logging
async def get_guild_raid_progression(
    realm: str,
    guild_name: str,
    game_version: str = "retail"
) -> Dict[str, Any]:
    """
    Get guild raid progression data from achievements

    Returns raw guild achievement data which includes all raid progression information.

    Args:
        realm: Server realm name (e.g., 'lightbringer', 'stormrage', 'illidan')
        guild_name: Guild name (e.g., 'legal-tender', 'Liquid', 'Echo')
        game_version: WoW version ('retail' or 'classic')

    Returns:
        Dictionary with guild achievement data including:
        - guild_info: Basic guild information
        - achievements: All guild achievements (includes raid progression)
        - total_achievements: Total achievement count
        - recent_achievements: Recently earned achievements
    """
    try:
        logger.info(f"Getting raid progression for {guild_name} on {realm} ({game_version})")

        async with BlizzardAPIClient(game_version=game_version) as client:
            guild_info = await client.get_guild_info(realm, guild_name)
            achievements = await client.get_guild_achievements(realm, guild_name)

            return {
                "success": True,
                "guild_name": guild_name,
                "realm": realm,
                "guild_info": {
                    "name": guild_info.get("name"),
                    "faction": guild_info.get("faction", {}).get("name"),
                    "member_count": guild_info.get("member_count"),
                    "achievement_points": guild_info.get("achievement_points", 0)
                },
                "achievements": achievements.get("achievements", []),
                "total_achievements": len(achievements.get("achievements", [])),
                "recent_achievements": achievements.get("achievements", [])[:10]
            }

    except BlizzardAPIError as e:
        logger.error(f"Blizzard API error: {e.message}")
        return error_response(f"API Error: {e.message}")
    except Exception as e:
        logger.error(f"Error getting raid progression: {str(e)}")
        return error_response(f"Failed to get raid progression: {str(e)}")


@mcp_tool()
@with_supabase_logging
async def compare_member_performance(
    realm: str,
    guild_name: str,
    member_names: List[str],
    metric: str = "item_level",
    game_version: str = "retail"
) -> Dict[str, Any]:
    """
    Compare performance metrics across guild members

    Args:
        realm: Server realm
        guild_name: Guild name
        member_names: List of character names to compare
        metric: Metric to compare ('item_level', 'achievement_points', 'guild_rank')
        game_version: WoW version ('retail' or 'classic')

    Returns:
        Comparison results with member data for the specified metric
    """
    try:
        logger.info(f"Comparing members {member_names} in {guild_name} ({game_version})")

        async with BlizzardAPIClient(game_version=game_version) as client:
            # Get data for specific members
            comparison_data = []

            for member_name in member_names:
                try:
                    char_data = await client.get_character_profile(realm, member_name)
                    if metric == "item_level":
                        equipment = await client.get_character_equipment(realm, member_name)
                        char_data["equipment_summary"] = client._summarize_equipment(equipment)
                    comparison_data.append(char_data)
                except BlizzardAPIError as e:
                    logger.warning(f"Failed to get data for {member_name}: {e.message}")

            # Extract comparison values
            comparison_values = []
            for char in comparison_data:
                if metric == "item_level":
                    value = char.get("equipment_summary", {}).get("average_item_level", 0)
                elif metric == "achievement_points":
                    value = char.get("achievement_points", 0)
                elif metric == "guild_rank":
                    value = char.get("guild_rank", 999)
                else:
                    value = 0

                comparison_values.append({
                    "name": char.get("name", "Unknown"),
                    "metric": metric,
                    "value": value
                })

            return {
                "success": True,
                "member_data": comparison_data,
                "comparison_metric": metric,
                "comparison_values": comparison_values,
                "member_count": len(comparison_data)
            }

    except Exception as e:
        logger.error(f"Error comparing members: {str(e)}")
        return error_response(f"Comparison failed: {str(e)}")