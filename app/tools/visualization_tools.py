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
async def generate_raid_progress_chart(
    realm: str,
    guild_name: str,
    raid_tier: str = "current",
    game_version: str = "retail"
) -> str:
    """
    Generate visual raid progression charts and upload to Supabase Storage

    Args:
        realm: Server realm
        guild_name: Guild name
        raid_tier: Raid tier ('current', 'dragonflight', 'shadowlands')
        game_version: WoW version ('retail' or 'classic')

    Returns:
        Public URL to the chart image in Supabase Storage (click to view/download)
    """
    try:
        logger.info(f"Generating raid chart for {guild_name} on {realm} ({game_version})")
        
        async with BlizzardAPIClient(game_version=game_version) as client:
            guild_data = await client.get_comprehensive_guild_data(realm, guild_name)
            
            # Generate raid progression chart
            chart_data = await chart_generator.create_raid_progress_chart(
                guild_data, raid_tier
            )
            
            return chart_data  # Supabase Storage URL
            
    except BlizzardAPIError as e:
        logger.error(f"Blizzard API error: {e.message}")
        return await chart_generator._create_error_chart(f"API Error: {e.message}")
    except Exception as e:
        logger.error(f"Error generating chart: {str(e)}")
        return await chart_generator._create_error_chart(f"Chart generation failed: {str(e)}")


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