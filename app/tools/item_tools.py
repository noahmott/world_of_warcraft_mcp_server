"""
Item lookup and information tools for WoW Guild MCP Server
"""

from typing import Dict, Any, List, Union

from .base import mcp_tool, with_supabase_logging
from ..api.blizzard_client import BlizzardAPIClient
from ..utils.logging_utils import get_logger
from ..utils.response_utils import error_response, api_error_response

logger = get_logger(__name__)


@mcp_tool()
@with_supabase_logging
async def lookup_items(
    item_ids: Union[int, List[int]],
    game_version: str = "retail",
    detailed: bool = True
) -> Dict[str, Any]:
    """
    Look up WoW item details by ID(s)

    Handles both single item lookups and batch lookups automatically.

    Args:
        item_ids: Single item ID (int) or list of item IDs
        game_version: WoW version ('retail' or 'classic')
        detailed: True for full details, False for name + basic info only

    Returns:
        For single item (item_ids=123):
        {
            "success": true,
            "item_id": 123,
            "name": "Item Name",
            "quality": "Epic",
            ... (if detailed=True)
        }

        For multiple items (item_ids=[123, 456]):
        {
            "success": true,
            "items": {
                123: {"name": "...", ...},
                456: {"name": "...", ...}
            },
            "items_found": 2,
            "failed_lookups": []
        }
    """
    try:
        # Normalize input to list
        if isinstance(item_ids, int):
            item_ids_list = [item_ids]
            single_item = True
        else:
            item_ids_list = item_ids
            single_item = False

        logger.info(f"Looking up {len(item_ids_list)} item(s) ({game_version})")

        results = {}
        failed_lookups = []

        async with BlizzardAPIClient(game_version=game_version) as client:
            for item_id in item_ids_list:
                try:
                    item_data = await client.get_item_data(item_id)

                    # Handle name format differences between Classic and Retail
                    name = item_data.get('name', 'Unknown Item')
                    if isinstance(name, dict):
                        # Retail format with localization
                        name = name.get('en_US', 'Unknown Item')

                    if detailed:
                        # Full details
                        result = {
                            "name": name,
                            "quality": item_data.get('quality', {}).get('name', 'Unknown'),
                            "item_class": item_data.get('item_class', {}).get('name', 'Unknown'),
                            "item_subclass": item_data.get('item_subclass', {}).get('name', 'Unknown'),
                            "inventory_type": item_data.get('inventory_type', {}).get('name', 'Unknown'),
                            "purchase_price": item_data.get('purchase_price', 0),
                            "sell_price": item_data.get('sell_price', 0),
                            "level": item_data.get('level', 0),
                            "required_level": item_data.get('required_level', 0),
                            "max_count": item_data.get('max_count', 0)
                        }

                        # Add preview URL if available
                        if 'preview_item' in item_data:
                            result["preview_url"] = item_data['preview_item'].get('item', {}).get('key', {}).get('href')
                    else:
                        # Summary only
                        result = {
                            "name": name,
                            "quality": item_data.get('quality', {}).get('name', 'Unknown'),
                            "item_class": item_data.get('item_class', {}).get('name', 'Unknown'),
                            "level": item_data.get('level', 0),
                            "sell_price": item_data.get('sell_price', 0)
                        }

                    results[item_id] = result

                except Exception as e:
                    logger.warning(f"Failed to lookup item {item_id}: {str(e)}")
                    failed_lookups.append(item_id)

        # Return format depends on whether single or multiple items requested
        if single_item:
            # Single item: return item data directly
            if results:
                item_id = item_ids_list[0]
                return {
                    "success": True,
                    "item_id": item_id,
                    "game_version": game_version,
                    **results[item_id]
                }
            else:
                return error_response(f"Item {item_ids_list[0]} not found")
        else:
            # Multiple items: return dictionary
            return {
                "success": True,
                "items": results,
                "items_found": len(results),
                "failed_lookups": failed_lookups,
                "game_version": game_version
            }

    except Exception as e:
        logger.error(f"Error looking up items: {str(e)}")
        return error_response(f"Item lookup failed: {str(e)}")