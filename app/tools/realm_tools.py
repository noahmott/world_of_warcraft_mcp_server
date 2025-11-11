"""
Realm status and information tools for WoW Guild MCP Server
"""

from typing import Dict, Any

from .base import mcp_tool, with_supabase_logging
from ..api.blizzard_client import BlizzardAPIClient, BlizzardAPIError
from ..core.constants import KNOWN_CLASSIC_REALMS, KNOWN_RETAIL_REALMS
from ..utils.logging_utils import get_logger
from ..utils.response_utils import error_response

logger = get_logger(__name__)


@mcp_tool()
@with_supabase_logging
async def get_realm_info(
    realm: str,
    game_version: str = "retail",
    include_status: bool = True
) -> Dict[str, Any]:
    """
    Get WoW realm information (server details and connected realm ID)

    IMPORTANT: This tool is ONLY needed for realm-specific auction house queries.
    DO NOT call this tool for commodities market queries - commodities are region-wide and don't need a realm.

    Use this to get the connected_realm_id for a specific server before querying its auction house.

    Args:
        realm: Server realm name - REQUIRED (e.g., 'stormrage', 'area-52', 'mankrik'). User must specify which realm.
        game_version: WoW version ('retail' or 'classic')
        include_status: Include detailed status info (population, timezone, type)

    Returns:
        Realm information including connected_realm_id and optional status details
    """
    try:
        logger.info(f"Getting realm info for {realm} ({game_version})")

        # Check if it's a known realm (prefer hardcoded IDs for reliability)
        realm_lower = realm.lower()
        known_id = None

        if game_version == "classic" and realm_lower in KNOWN_CLASSIC_REALMS:
            known_id = KNOWN_CLASSIC_REALMS[realm_lower]
            logger.info(f"Using known Classic realm ID for {realm}: {known_id}")
        elif game_version == "retail" and realm_lower in KNOWN_RETAIL_REALMS:
            known_id = KNOWN_RETAIL_REALMS[realm_lower]
            logger.info(f"Using known Retail realm ID for {realm}: {known_id}")

        # If we have a known ID and don't need status, return immediately
        if known_id and not include_status:
            return {
                "success": True,
                "realm": realm,
                "connected_realm_id": known_id,
                "game_version": game_version,
                "source": "hardcoded"
            }

        # Get realm info from API (for status or if no known ID)
        async with BlizzardAPIClient(game_version=game_version) as client:
            try:
                # Get realm information
                realm_info = await client._get_realm_info(realm)

                # Extract connected realm ID
                connected_realm = realm_info.get('connected_realm', {})
                connected_realm_id = known_id  # Prefer known ID if we have it

                if not connected_realm_id:
                    # Try to extract from API response
                    if isinstance(connected_realm, dict) and 'id' in connected_realm:
                        connected_realm_id = connected_realm['id']
                    elif isinstance(connected_realm, int):
                        connected_realm_id = connected_realm
                    else:
                        # Try to extract ID from href if available
                        href = connected_realm.get('href', '') if isinstance(connected_realm, dict) else ''
                        if 'connected-realm/' in href:
                            connected_realm_id = int(href.split('connected-realm/')[-1].split('?')[0])

                # Build base response
                response = {
                    "success": True,
                    "realm": realm,
                    "connected_realm_id": connected_realm_id,
                    "game_version": game_version,
                    "source": "api" if not known_id else "hardcoded"
                }

                # Add detailed status if requested
                if include_status:
                    # Get status info
                    status = realm_info.get('status', {})
                    status_type = status.get('type', 'UNKNOWN') if isinstance(status, dict) else 'UNKNOWN'

                    response.update({
                        "status": status_type.lower(),
                        "population": realm_info.get('population', {}).get('name', 'Unknown'),
                        "timezone": realm_info.get('timezone', 'Unknown'),
                        "type": realm_info.get('type', {}).get('name', 'Unknown'),
                        "is_tournament": realm_info.get('is_tournament', False)
                    })

                return response

            except BlizzardAPIError as e:
                logger.warning(f"API error for realm {realm}: {str(e)}")

                # Fall back to hardcoded ID if API fails
                if known_id:
                    response = {
                        "success": True,
                        "realm": realm,
                        "connected_realm_id": known_id,
                        "game_version": game_version,
                        "source": "hardcoded",
                        "message": "API error, using hardcoded ID"
                    }

                    if include_status:
                        response["status"] = "unknown"

                    return response
                else:
                    return {
                        "success": False,
                        "error": f"Realm not found: {str(e)}",
                        "realm": realm,
                        "game_version": game_version
                    }

    except Exception as e:
        logger.error(f"Error getting realm info: {str(e)}")
        return error_response(f"Realm info lookup failed: {str(e)}")