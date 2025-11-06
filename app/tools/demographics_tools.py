"""
Guild demographics analysis tools for WoW Guild MCP Server
"""

from typing import Dict, Any, List
from collections import Counter

from .base import mcp_tool, with_supabase_logging, get_or_initialize_services
from ..api.blizzard_client import BlizzardAPIClient, BlizzardAPIError
from ..utils.logging_utils import get_logger
from ..utils.datetime_utils import utc_now_iso
from ..utils.response_utils import success_response, error_response

logger = get_logger(__name__)


@mcp_tool()
@with_supabase_logging
async def get_guild_demographics(
    realm: str,
    guild_name: str,
    game_version: str = "retail",
    max_level_only: bool = True
) -> Dict[str, Any]:
    """
    Get comprehensive demographic breakdown of a guild's players

    Args:
        realm: Server realm
        guild_name: Guild name
        game_version: WoW version ('retail' or 'classic')
        max_level_only: Only include max level characters (default: True)

    Returns:
        JSON with detailed demographic information for each player including:
        - Character name, level, class, race, spec
        - Item level (equipped and average)
        - Achievement points
        - Last login timestamp
        - Guild rank
        - Aggregated statistics by class, race, spec, and faction
    """
    try:
        logger.info(f"Getting demographics for {guild_name} on {realm} ({game_version})")

        # Determine max level based on game version
        if game_version == "retail":
            max_level = 80  # Current retail max level (The War Within)
        elif game_version == "classic":
            max_level = 60  # Classic max level
        else:
            max_level = 80  # Default to retail

        async with BlizzardAPIClient(game_version=game_version) as client:
            # Get guild roster
            roster = await client.get_guild_roster(realm, guild_name)

            if not roster.get("members"):
                return error_response("No members found or guild not found")

            # Filter members by level if requested
            members = roster["members"]
            if max_level_only:
                members = [m for m in members if m.get("character", {}).get("level", 0) >= max_level]
                logger.info(f"Filtered to {len(members)} max level characters")

            # Collect detailed character information
            player_details = []
            errors = []

            for i, member in enumerate(members):
                character = member.get("character", {})
                character_name = character.get("name", "Unknown")
                character_realm = character.get("realm", {}).get("slug", realm)

                try:
                    # Get character profile for detailed info
                    profile = await client.get_character_profile(character_realm, character_name)

                    # Extract race info
                    race_data = profile.get("race", {})
                    if isinstance(race_data, dict):
                        race_name = race_data.get("name")
                        if isinstance(race_name, dict):
                            race_name = race_name.get("en_US", "Unknown")
                        elif not race_name:
                            race_name = "Unknown"
                    else:
                        race_name = str(race_data) if race_data else "Unknown"

                    # Extract class info
                    class_data = profile.get("character_class", {})
                    if isinstance(class_data, dict):
                        class_name = class_data.get("name")
                        if isinstance(class_name, dict):
                            class_name = class_name.get("en_US", "Unknown")
                        elif not class_name:
                            class_name = "Unknown"
                    else:
                        class_name = str(class_data) if class_data else "Unknown"

                    # Extract spec info
                    spec_data = profile.get("active_spec", {})
                    if isinstance(spec_data, dict):
                        spec_name = spec_data.get("name")
                        if isinstance(spec_name, dict):
                            spec_name = spec_name.get("en_US", "Unknown")
                        elif not spec_name:
                            spec_name = "Unknown"
                    else:
                        spec_name = str(spec_data) if spec_data else "Unknown"

                    # Extract faction info
                    faction_data = profile.get("faction", {})
                    if isinstance(faction_data, dict):
                        faction_name = faction_data.get("name", "Unknown")
                    else:
                        faction_name = str(faction_data) if faction_data else "Unknown"

                    # Extract guild info
                    guild_data = profile.get("guild")
                    guild_name_from_profile = guild_data.get("name") if isinstance(guild_data, dict) else None

                    player_info = {
                        "name": profile.get("name", character_name),
                        "realm": character_realm,
                        "level": profile.get("level", 0),
                        "race": race_name,
                        "class": class_name,
                        "active_spec": spec_name,
                        "faction": faction_name,
                        "guild": guild_name_from_profile,
                        "guild_rank": member.get("rank", 999),
                        "equipped_item_level": profile.get("equipped_item_level", 0),
                        "average_item_level": profile.get("average_item_level", 0),
                        "achievement_points": profile.get("achievement_points", 0),
                        "last_login": profile.get("last_login_timestamp")
                    }

                    player_details.append(player_info)
                    logger.info(f"Collected data for {character_name} ({i+1}/{len(members)})")

                except BlizzardAPIError as e:
                    error_msg = f"{character_name}: {str(e)}"
                    errors.append(error_msg)
                    logger.warning(f"Failed to get profile for {character_name}: {e.message}")
                except Exception as e:
                    error_msg = f"{character_name}: {str(e)}"
                    errors.append(error_msg)
                    logger.error(f"Unexpected error for {character_name}: {str(e)}")

            # Calculate demographic statistics
            demographics = calculate_demographics(player_details)

            return {
                "success": True,
                "guild_name": guild_name,
                "realm": realm,
                "game_version": game_version,
                "max_level_only": max_level_only,
                "max_level": max_level,
                "total_members": len(roster["members"]),
                "analyzed_members": len(player_details),
                "players": player_details,
                "demographics": demographics,
                "errors": errors if errors else None,
                "timestamp": utc_now_iso()
            }

    except BlizzardAPIError as e:
        logger.error(f"Blizzard API error: {e.message}")
        return error_response(f"Blizzard API error: {e.message}")
    except Exception as e:
        logger.error(f"Error getting guild demographics: {str(e)}")
        return error_response(str(e))


def calculate_demographics(player_details: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Calculate demographic statistics from player details

    Args:
        player_details: List of player information dictionaries

    Returns:
        Dictionary containing aggregated demographic statistics
    """
    if not player_details:
        return {}

    # Count by class
    class_counts = Counter(player["class"] for player in player_details)

    # Count by race
    race_counts = Counter(player["race"] for player in player_details)

    # Count by spec
    spec_counts = Counter(player["active_spec"] for player in player_details)

    # Count by faction
    faction_counts = Counter(player["faction"] for player in player_details)

    # Calculate average item levels
    equipped_ilevels = [p["equipped_item_level"] for p in player_details if p["equipped_item_level"] > 0]
    avg_equipped_ilevel = sum(equipped_ilevels) / len(equipped_ilevels) if equipped_ilevels else 0

    average_ilevels = [p["average_item_level"] for p in player_details if p["average_item_level"] > 0]
    avg_average_ilevel = sum(average_ilevels) / len(average_ilevels) if average_ilevels else 0

    # Calculate average achievement points
    achievement_points = [p["achievement_points"] for p in player_details if p["achievement_points"] > 0]
    avg_achievement_points = sum(achievement_points) / len(achievement_points) if achievement_points else 0

    # Count by guild rank
    rank_counts = Counter(player["guild_rank"] for player in player_details)

    return {
        "total_analyzed": len(player_details),
        "by_class": dict(class_counts.most_common()),
        "by_race": dict(race_counts.most_common()),
        "by_spec": dict(spec_counts.most_common()),
        "by_faction": dict(faction_counts.most_common()),
        "by_guild_rank": dict(sorted(rank_counts.items())),
        "item_levels": {
            "average_equipped": round(avg_equipped_ilevel, 1),
            "average_bag": round(avg_average_ilevel, 1),
            "min_equipped": min(equipped_ilevels) if equipped_ilevels else 0,
            "max_equipped": max(equipped_ilevels) if equipped_ilevels else 0
        },
        "achievement_points": {
            "average": round(avg_achievement_points, 0),
            "min": min(achievement_points) if achievement_points else 0,
            "max": max(achievement_points) if achievement_points else 0
        }
    }
