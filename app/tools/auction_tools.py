"""
Auction house and economy analysis tools for WoW Guild MCP Server
"""

import json
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional

from .base import mcp_tool, with_supabase_logging, get_or_initialize_services
from ..api.blizzard_client import BlizzardAPIClient, BlizzardAPIError
from ..services.auction_aggregator import AuctionAggregatorService
from ..utils.namespace_utils import get_connected_realm_id
from ..utils.logging_utils import get_logger
from ..utils.datetime_utils import utc_now_iso
from ..utils.response_utils import success_response, error_response, api_error_response

# Create auction aggregator instance
auction_aggregator = AuctionAggregatorService()

logger = get_logger(__name__)


@mcp_tool()
@with_supabase_logging
async def get_market_data(
    market_type: str = "commodities",
    realm: Optional[str] = None,
    item_ids: Any = None,
    include_trends: bool = False,
    trend_hours: int = 24,
    max_results: int = 100,
    game_version: str = "retail"
) -> Dict[str, Any]:
    """
    Get current market prices for WoW items (commodities or auction house)

    IMPORTANT: For commodities (ore, herbs, reagents), use market_type='commodities' - NO REALM NEEDED.
    For auction house (gear, pets), use market_type='auction_house' and specify realm.

    Returns current market snapshot with prices. Optionally includes historical trends.

    Args:
        market_type: 'commodities' (region-wide: ore, herbs - DEFAULT) or 'auction_house' (realm-specific: gear, pets)
        realm: Server realm (e.g., 'stormrage'). ONLY required if market_type='auction_house', otherwise leave empty
        item_ids: Filter to specific items by ID. Can be: list of integers [1,2,3], string "[1,2,3]", or None (top items by market value)
        include_trends: Add historical price data from stored snapshots
        trend_hours: Hours of history (if include_trends=True, max 720/30 days)
        max_results: Max items to return (if item_ids=None)
        game_version: WoW version ('retail' or 'classic')

    Returns:
        Current market snapshot + optional trend data:
        {
            "success": true,
            "realm": "stormrage" (or "region-wide" for commodities),
            "market_type": "auction_house" or "commodities",
            "timestamp": "2025-11-06T...",
            "market_data": {
                "123": {
                    "min_price": 1000,
                    "max_price": 5000,
                    "mean_price": 3000,
                    "auction_count": 42,
                    "total_quantity": 150
                }
            },
            "trends": {  // Only if include_trends=True
                "123": [
                    {"timestamp": "...", "mean_price": 2950, ...},
                    ...
                ]
            }
        }
    """
    try:
        # Normalize item_ids parameter (handle string representations)
        if item_ids is not None:
            if isinstance(item_ids, str):
                import json
                try:
                    parsed = json.loads(item_ids)
                    if isinstance(parsed, list):
                        if not all(isinstance(x, int) for x in parsed):
                            return error_response("All item IDs must be integers")
                        item_ids = parsed
                    else:
                        return error_response("item_ids string must parse to a list of integers")
                except json.JSONDecodeError:
                    return error_response(f"item_ids string is not valid JSON: {item_ids}")
            elif not isinstance(item_ids, list):
                return error_response(f"item_ids must be a list of integers, got {type(item_ids).__name__}")
            elif not all(isinstance(x, int) for x in item_ids):
                return error_response("All item IDs must be integers")

        logger.info(f"Getting {market_type} market data ({game_version})")

        async with BlizzardAPIClient(game_version=game_version) as client:
            # Determine which endpoint to use
            if market_type == "commodities":
                # Commodities are region-wide, no realm needed
                logger.info("Fetching region-wide commodity auction data")
                ah_data = await client.get_commodity_auctions()
                realm_display = "region-wide"
                connected_realm_id = None
            else:
                # Auction house is realm-specific
                if not realm:
                    return error_response("realm parameter is required for auction_house market type")

                logger.info(f"Fetching auction house data for realm {realm}")
                # Get connected realm ID
                connected_realm_id = await get_connected_realm_id(realm, game_version, client)

                if not connected_realm_id:
                    return error_response(f"Could not find connected realm ID for realm {realm}")

                # Get current auction data
                ah_data = await client.get_auction_house_data(connected_realm_id)
                realm_display = realm

            if not ah_data or 'auctions' not in ah_data:
                return error_response("No auction data available")

            # Aggregate auction data (returns Dict[int, Dict[str, Any]])
            aggregated_raw = auction_aggregator.aggregate_auction_data(ah_data['auctions'])

            # Convert to string keys for JSON serialization and consistency
            aggregated: Dict[str, Any] = {str(k): v for k, v in aggregated_raw.items()}

            # Filter to specific items if requested
            if item_ids:
                filtered: Dict[str, Any] = {}
                for item_id in item_ids:
                    item_id_str = str(item_id)
                    if item_id_str in aggregated:
                        filtered[item_id_str] = aggregated[item_id_str]
                aggregated = filtered
            else:
                # Sort by total market value and limit results
                sorted_items = sorted(
                    aggregated.items(),
                    key=lambda x: x[1]['total_market_value'],
                    reverse=True
                )[:max_results]
                aggregated = dict(sorted_items)

            response = {
                "success": True,
                "realm": realm_display,
                "market_type": market_type,
                "connected_realm_id": connected_realm_id,
                "timestamp": utc_now_iso(),
                "total_items": len(ah_data['auctions']),
                "items_returned": len(aggregated),
                "market_data": aggregated
            }

            # Add historical trends if requested
            if include_trends:
                item_ids_for_trends: List[str] = list(aggregated.keys()) if item_ids is None else [str(i) for i in item_ids]
                # For commodities, use "commodities" as realm identifier
                realm_for_trends = "commodities" if market_type == "commodities" else realm
                trends = await _get_historical_trends(
                    realm_for_trends,
                    item_ids_for_trends,
                    trend_hours,
                    game_version
                )
                if trends:
                    response["trends"] = trends
                    response["trend_hours_analyzed"] = trend_hours

            return response

    except BlizzardAPIError as e:
        logger.error(f"Blizzard API error: {e.message}")
        return api_error_response(e)
    except Exception as e:
        logger.error(f"Error getting market data: {str(e)}")
        return error_response(f"Market data failed: {str(e)}")


@mcp_tool()
@with_supabase_logging
async def analyze_market(
    operation: str = "opportunities",
    market_type: str = "commodities",
    realm: Optional[str] = None,
    min_profit_margin: float = 20.0,
    check_hours: int = 24,
    realms: Optional[List[str]] = None,
    max_results: int = 20,
    game_version: str = "retail"
) -> Dict[str, Any]:
    """
    Find profitable deals in WoW markets (commodities or auction house)

    IMPORTANT: For commodities market queries (ore, herbs, reagents), use market_type='commodities' - NO REALM NEEDED.
    For realm-specific auction house queries (gear, pets), use market_type='auction_house' and specify realm.

    Supports two operations:
    - "opportunities": Find items with high profit margins (profitable deals)
    - "health_check": Check economy snapshot system health

    Args:
        operation: 'opportunities' (find deals) or 'health_check' (system status)
        market_type: 'commodities' (region-wide: ore, herbs, etc - DEFAULT) or 'auction_house' (realm-specific: gear, pets)
        realm: Server realm name (ONLY required if market_type='auction_house', otherwise leave empty)
        min_profit_margin: Minimum profit % for opportunities (default 20%)
        check_hours: Hours to analyze for health check (default 24)
        realms: List of realms for health check (None = default set)
        max_results: Max opportunities to return
        game_version: WoW version ('retail' or 'classic')

    Returns:
        For operation='opportunities':
        {
            "success": true,
            "realm": "stormrage" (or "region-wide" for commodities),
            "market_type": "auction_house" or "commodities",
            "opportunities": [
                {
                    "item_id": 123,
                    "profit_margin_pct": 45.2,
                    "min_price": 1000,
                    "max_price": 1452,
                    "potential_profit": 452,
                    ...
                }
            ]
        }

        For operation='health_check':
        {
            "success": true,
            "overall_health": {
                "healthy": 8,
                "warning": 2,
                "unhealthy": 0
            },
            "realm_health": {...}
        }
    """
    try:
        if operation == "opportunities":
            return await _find_market_opportunities(
                realm, min_profit_margin, max_results, game_version, market_type
            )
        elif operation == "health_check":
            return await _check_snapshot_health(
                realms, check_hours, game_version
            )
        else:
            return error_response(f"Unknown operation: {operation}. Use 'opportunities' or 'health_check'")

    except Exception as e:
        logger.error(f"Error in market analysis: {str(e)}")
        return error_response(f"Market analysis failed: {str(e)}")


# Internal function - not exposed via MCP
@with_supabase_logging
async def capture_economy_snapshot(
    realms: List[str],
    region: str = "us",
    game_version: str = "retail",
    force_update: bool = False
) -> Dict[str, Any]:
    """
    Capture hourly economy snapshots for specified realms

    NOTE: This is an internal/scheduler tool, not exposed via MCP.

    Args:
        realms: List of realm names to capture data for
        region: Region (us, eu, etc.)
        game_version: WoW version ('retail' or 'classic')
        force_update: Force update even if recent snapshot exists

    Returns:
        Snapshot capture results
    """
    try:
        logger.info(f"Capturing economy snapshots for {len(realms)} realms")

        # Initialize services if needed
        service_mgr = await get_or_initialize_services()
        redis_client = service_mgr.redis_client

        if not redis_client:
            return {
                "error": "Redis not available for economy snapshots",
                "message": "Redis connection required for storing economy data"
            }

        results = {}
        snapshots_created = 0
        snapshots_skipped = 0

        async with BlizzardAPIClient(game_version=game_version) as client:
            for realm in realms:
                try:
                    # Check if we have a recent snapshot (within last hour)
                    snapshot_key = f"economy_snapshot:{game_version}:{region}:{realm.lower()}"

                    if not force_update:
                        # Check last snapshot time
                        last_snapshot_time_key = f"{snapshot_key}:last_update"
                        last_update = await redis_client.get(last_snapshot_time_key)

                        if last_update:
                            last_time = datetime.fromisoformat(last_update.decode())
                            time_diff = datetime.now(timezone.utc) - last_time

                            if time_diff.total_seconds() < 3600:  # Less than 60 minutes (1 hour)
                                logger.info(f"Skipping {realm} - snapshot is {int(time_diff.total_seconds() / 60)} minutes old")
                                results[realm] = {"status": "skipped", "reason": "recent_snapshot_exists"}
                                snapshots_skipped += 1
                                continue

                    # Get connected realm ID
                    connected_realm_id = await get_connected_realm_id(realm, game_version, client)

                    if not connected_realm_id:
                        results[realm] = {"status": "error", "reason": "realm_not_found"}
                        continue

                    # Get auction data
                    ah_data = await client.get_auction_house_data(connected_realm_id)

                    if not ah_data or 'auctions' not in ah_data:
                        results[realm] = {"status": "error", "reason": "no_auction_data"}
                        continue

                    # Aggregate auction data
                    aggregated_raw = auction_aggregator.aggregate_auction_data(ah_data['auctions'])
                    aggregated = {str(k): v for k, v in aggregated_raw.items()}

                    # Create timestamped snapshot
                    timestamp = datetime.now(timezone.utc)
                    timestamp_key = f"{snapshot_key}:{timestamp.strftime('%Y%m%d_%H%M')}"

                    snapshot_data = {
                        "realm": realm,
                        "connected_realm_id": connected_realm_id,
                        "timestamp": timestamp.isoformat(),
                        "auction_count": len(ah_data['auctions']),
                        "unique_items": len(aggregated),
                        "market_data": aggregated
                    }

                    # Store snapshot with 30-day expiry
                    await redis_client.setex(
                        timestamp_key,
                        2592000,  # 30 days in seconds
                        json.dumps(snapshot_data)
                    )

                    # Update last snapshot time
                    await redis_client.set(last_snapshot_time_key, timestamp.isoformat())

                    results[realm] = {
                        "status": "success",
                        "auctions": str(len(ah_data['auctions'])),
                        "unique_items": str(len(aggregated)),
                        "timestamp": timestamp.isoformat()
                    }
                    snapshots_created += 1

                except Exception as e:
                    logger.error(f"Error capturing snapshot for {realm}: {str(e)}")
                    results[realm] = {"status": "error", "reason": str(e)}

        return {
            "success": True,
            "snapshots_created": snapshots_created,
            "snapshots_skipped": snapshots_skipped,
            "realm_results": results,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

    except Exception as e:
        logger.error(f"Error capturing economy snapshots: {str(e)}")
        return error_response(f"Economy snapshot capture failed: {str(e)}")


# Helper functions


async def _get_historical_trends(
    realm: str,
    item_ids: List[str],
    hours: int,
    game_version: str
) -> Dict[str, Any]:
    """Get historical price trends for items"""
    try:
        service_mgr = await get_or_initialize_services()
        redis_client = service_mgr.redis_client

        if not redis_client:
            logger.warning("Redis not available for trends")
            return {}

        # Limit hours to 30 days max
        hours = min(hours, 720)

        trends: Dict[str, Any] = {}
        snapshot_base_key = f"economy_snapshot:{game_version}:us:{realm.lower()}"

        # Get all snapshots for the time period
        current_time = datetime.now(timezone.utc)
        cutoff_time = current_time - timedelta(hours=hours)

        # Get all snapshot keys for this realm
        pattern = f"{snapshot_base_key}:*"
        all_keys = await redis_client.keys(pattern)

        # Filter keys to only include timestamps within our time range
        for key in all_keys:
            key_str = key.decode() if isinstance(key, bytes) else key
            key_parts = key_str.split(':')
            if len(key_parts) >= 5 and key_parts[-1].startswith('202'):
                timestamp_str = key_parts[-1]
                try:
                    # Handle both old (YYYYMMDD_HH) and new (YYYYMMDD_HHMM) formats
                    if len(timestamp_str) == 11:
                        ts_dt = datetime.strptime(timestamp_str, '%Y%m%d_%H').replace(tzinfo=timezone.utc)
                    else:
                        ts_dt = datetime.strptime(timestamp_str, '%Y%m%d_%H%M').replace(tzinfo=timezone.utc)

                    if ts_dt < cutoff_time or ts_dt > current_time:
                        continue

                    snapshot_data = await redis_client.get(key)
                    if snapshot_data:
                        snapshot = json.loads(snapshot_data.decode())

                        for item_id in item_ids:
                            if item_id in snapshot.get("market_data", {}):
                                if item_id not in trends:
                                    trends[item_id] = []

                                item_data = snapshot["market_data"][item_id]
                                trends[item_id].append({
                                    "timestamp": snapshot["timestamp"],
                                    "min_price": item_data["min_price"],
                                    "max_price": item_data["max_price"],
                                    "mean_price": item_data["mean_price"],
                                    "auction_count": item_data["auction_count"],
                                    "total_quantity": item_data["total_quantity"]
                                })
                except ValueError:
                    continue

        # Sort each trend by timestamp
        for item_id in trends:
            trends[item_id].sort(key=lambda x: x["timestamp"])

        return trends

    except Exception as e:
        logger.error(f"Error getting trends: {str(e)}")
        return {}


async def _find_market_opportunities(
    realm: Optional[str],
    min_profit_margin: float,
    max_results: int,
    game_version: str,
    market_type: str = "auction_house"
) -> Dict[str, Any]:
    """Find items with high profit margins"""
    try:
        logger.info(f"Finding market opportunities in {market_type} ({game_version})")

        async with BlizzardAPIClient(game_version=game_version) as client:
            # Determine which endpoint to use
            if market_type == "commodities":
                # Commodities are region-wide
                logger.info("Fetching region-wide commodity auction data")
                ah_data = await client.get_commodity_auctions()
                realm_display = "region-wide"
                connected_realm_id = None
            else:
                # Auction house is realm-specific
                if not realm:
                    return error_response("realm parameter required for auction_house opportunities")

                logger.info(f"Fetching auction house data for realm {realm}")
                # Get connected realm ID
                connected_realm_id = await get_connected_realm_id(realm, game_version, client)

                if not connected_realm_id:
                    return error_response("Could not find connected realm ID")

                # Get current auction data
                ah_data = await client.get_auction_house_data(connected_realm_id)
                realm_display = realm

            if not ah_data or 'auctions' not in ah_data:
                return error_response("No auction data available")

            # Aggregate auction data
            aggregated_raw = auction_aggregator.aggregate_auction_data(ah_data['auctions'])
            aggregated = {str(k): v for k, v in aggregated_raw.items()}

            # Find opportunities (items with high price variance)
            opportunities = []
            for item_id, data in aggregated.items():
                if data['auction_count'] < 2:
                    continue

                # Calculate potential profit margin
                price_range = data['max_price'] - data['min_price']
                if data['min_price'] > 0:
                    margin_pct = (price_range / data['min_price']) * 100

                    if margin_pct >= min_profit_margin:
                        opportunities.append({
                            'item_id': item_id,
                            'min_price': data['min_price'],
                            'max_price': data['max_price'],
                            'mean_price': data['avg_price'],
                            'profit_margin_pct': margin_pct,
                            'auction_count': data['auction_count'],
                            'total_quantity': data['total_quantity'],
                            'potential_profit': price_range
                        })

            # Sort by profit margin
            opportunities.sort(key=lambda x: x['profit_margin_pct'], reverse=True)

            return {
                "success": True,
                "realm": realm_display,
                "market_type": market_type,
                "connected_realm_id": connected_realm_id,
                "opportunities_found": len(opportunities),
                "opportunities": opportunities[:max_results],
                "min_profit_margin": min_profit_margin,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

    except BlizzardAPIError as e:
        logger.error(f"Blizzard API error: {e.message}")
        return api_error_response(e)
    except Exception as e:
        logger.error(f"Error finding opportunities: {str(e)}")
        return error_response(f"Opportunity search failed: {str(e)}")


async def _check_snapshot_health(
    realms: Optional[List[str]],
    check_hours: int,
    game_version: str
) -> Dict[str, Any]:
    """Check the health of economy snapshots"""
    try:
        logger.info(f"Checking economy snapshot health for {game_version}")

        service_mgr = await get_or_initialize_services()
        redis_client = service_mgr.redis_client

        if not redis_client:
            return {
                "error": "Redis not available",
                "message": "Redis connection required for health check"
            }

        # Default realms if none specified
        if not realms:
            realms = [
                "area-52", "stormrage", "illidan", "tichondrius",
                "mal'ganis", "zul'jin", "thrall", "lightbringer",
                "moonguard", "wyrmrest-accord"
            ]

        current_time = datetime.now(timezone.utc)
        cutoff_time = current_time - timedelta(hours=check_hours)
        health_results = {}

        for realm in realms:
            realm_lower = realm.lower()
            snapshot_base_key = f"economy_snapshot:{game_version}:us:{realm_lower}"

            # Get last update time
            last_update_key = f"{snapshot_base_key}:last_update"
            last_update = await redis_client.get(last_update_key)

            # Get all snapshot keys for this realm
            pattern = f"{snapshot_base_key}:*"
            all_keys = await redis_client.keys(pattern)

            # Filter and parse snapshot timestamps
            snapshots = []
            for key in all_keys:
                key_str = key.decode() if isinstance(key, bytes) else key
                key_parts = key_str.split(':')
                if len(key_parts) >= 5 and key_parts[-1].startswith('202'):
                    timestamp_str = key_parts[-1]
                    try:
                        if len(timestamp_str) == 11:
                            ts_dt = datetime.strptime(timestamp_str, '%Y%m%d_%H').replace(tzinfo=timezone.utc)
                        else:
                            ts_dt = datetime.strptime(timestamp_str, '%Y%m%d_%H%M').replace(tzinfo=timezone.utc)

                        if ts_dt >= cutoff_time:
                            snapshots.append(ts_dt)
                    except ValueError:
                        continue

            snapshots.sort()

            # Analyze health
            health_data: Dict[str, Any] = {
                "realm": realm,
                "status": "unknown",
                "last_update": None,
                "minutes_since_update": None,
                "snapshot_count": len(snapshots),
                "expected_snapshots": int(check_hours),
                "missing_percentage": 0,
                "issues": []
            }

            # Check last update
            if last_update:
                try:
                    last_time = datetime.fromisoformat(last_update.decode())
                    health_data["last_update"] = last_time.isoformat()
                    health_data["minutes_since_update"] = int((current_time - last_time).total_seconds() / 60)

                    if health_data["minutes_since_update"] > 75:
                        health_data["issues"].append(f"No update in {health_data['minutes_since_update']} minutes")
                except:
                    health_data["issues"].append("Invalid last_update timestamp")
            else:
                health_data["issues"].append("No last_update timestamp found")

            # Calculate missing percentage
            health_data["missing_percentage"] = round(
                (1 - health_data["snapshot_count"] / health_data["expected_snapshots"]) * 100, 1
            ) if health_data["expected_snapshots"] > 0 else 0

            # Determine status
            if not health_data["issues"] and health_data["missing_percentage"] < 10:
                health_data["status"] = "healthy"
            elif health_data["missing_percentage"] < 25 and len(health_data["issues"]) <= 1:
                health_data["status"] = "warning"
            else:
                health_data["status"] = "unhealthy"

            health_results[realm] = health_data

        # Overall health
        total_realms = len(health_results)
        healthy_realms = sum(1 for r in health_results.values() if r["status"] == "healthy")
        warning_realms = sum(1 for r in health_results.values() if r["status"] == "warning")
        unhealthy_realms = sum(1 for r in health_results.values() if r["status"] == "unhealthy")

        return {
            "success": True,
            "check_time": current_time.isoformat(),
            "hours_analyzed": check_hours,
            "overall_health": {
                "total_realms": total_realms,
                "healthy": healthy_realms,
                "warning": warning_realms,
                "unhealthy": unhealthy_realms,
                "health_percentage": round((healthy_realms / total_realms) * 100, 1) if total_realms > 0 else 0
            },
            "realm_health": health_results
        }

    except Exception as e:
        logger.error(f"Error checking snapshot health: {str(e)}")
        return {"error": f"Snapshot health check failed: {str(e)}"}
