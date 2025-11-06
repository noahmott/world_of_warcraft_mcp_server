"""
Visualization and chart generation tools for WoW Guild MCP Server
"""

from typing import Dict, Any, List

from .base import mcp_tool, with_supabase_logging
from ..api.blizzard_client import BlizzardAPIClient, BlizzardAPIError
from ..visualization.chart_generator import ChartGenerator
from ..utils.logging_utils import get_logger
from ..utils.response_utils import error_response, api_error_response

# Create chart generator instance
chart_generator = ChartGenerator()

logger = get_logger(__name__)


@mcp_tool()
@with_supabase_logging
async def get_guild_raid_progression(
    realm: str,
    guild_name: str,
    raid_tier: str = "current",
    game_version: str = "retail"
) -> Dict[str, Any]:
    """
    Get guild raid progression data from achievements

    Returns structured data about guild's raid progression including boss kills
    across different difficulty levels. More useful than charts for analysis.

    Args:
        realm: Server realm name (e.g., 'lightbringer', 'stormrage', 'illidan')
        guild_name: Guild name (e.g., 'legal-tender', 'Liquid', 'Echo')
        raid_tier: Raid tier to check. Options:
            - 'current' or 'war-within': The War Within (Nerub-ar Palace)
            - 'dragonflight': All Dragonflight raids (Amirdrassil, Aberrus, Vault)
            - 'shadowlands': All Shadowlands raids
            - 'bfa': Battle for Azeroth raids
            - 'legion': Legion raids
            - 'wod': Warlords of Draenor raids
            - 'mop': Mists of Pandaria raids
            - 'cataclysm': Cataclysm raids
        game_version: WoW version ('retail' or 'classic')

    Returns:
        Dictionary with raid progression data including:
        - raids: List of raids with boss kill counts per difficulty
        - summary: Overall progression statistics
        - guild_info: Basic guild information
    """
    try:
        logger.info(f"Getting raid progression for {guild_name} on {realm} ({game_version})")

        async with BlizzardAPIClient(game_version=game_version) as client:
            guild_data = await client.get_comprehensive_guild_data(realm, guild_name)

            # Extract raid progression using the chart generator's logic
            achievements = guild_data.get("guild_achievements", {})
            raid_progress = chart_generator._extract_raid_progress(achievements, raid_tier)

            if not raid_progress:
                return {
                    "success": True,
                    "guild_name": guild_name,
                    "realm": realm,
                    "tier": raid_tier,
                    "raids": [],
                    "message": f"No raid progression found for tier '{raid_tier}'"
                }

            # Calculate summary stats
            total_raids = len(raid_progress)
            total_bosses_killed = sum(
                d["bosses_killed"]
                for raid in raid_progress
                for d in raid.get("difficulties", [])
            )
            total_bosses_available = sum(
                d["total_bosses"]
                for raid in raid_progress
                for d in raid.get("difficulties", [])
            )

            return {
                "success": True,
                "guild_name": guild_name,
                "realm": realm,
                "tier": raid_tier,
                "raids": raid_progress,
                "summary": {
                    "total_raids": total_raids,
                    "total_bosses_killed": total_bosses_killed,
                    "total_bosses_available": total_bosses_available,
                    "completion_percentage": round((total_bosses_killed / total_bosses_available * 100), 1) if total_bosses_available > 0 else 0
                },
                "guild_info": {
                    "name": guild_data.get("guild_info", {}).get("name"),
                    "faction": guild_data.get("guild_info", {}).get("faction", {}).get("name"),
                    "member_count": guild_data.get("guild_info", {}).get("member_count")
                }
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
        Comparison results with chart_data as Supabase Storage URL (click to view/download)
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
            
            # Generate comparison chart
            chart_data = await chart_generator.create_member_comparison_chart(
                comparison_data, metric
            )
            
            return {
                "success": True,
                "member_data": comparison_data,
                "comparison_metric": metric,
                "chart_data": chart_data,
                "member_count": len(comparison_data)
            }
            
    except Exception as e:
        logger.error(f"Error comparing members: {str(e)}")
        return error_response(f"Comparison failed: {str(e)}")