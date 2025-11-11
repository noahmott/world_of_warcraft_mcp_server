"""
Commodity market analysis tools for WoW Guild MCP Server
"""

import json
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional

from .base import mcp_tool, with_supabase_logging, get_or_initialize_services
from ..services.auction_aggregator import AuctionAggregatorService
from ..services.commodity_query_service import CommodityQueryService
from ..services.supabase_client import get_supabase_client
from ..utils.logging_utils import get_logger
from ..utils.datetime_utils import utc_now_iso
from ..utils.response_utils import success_response, error_response

# Create auction aggregator instance
auction_aggregator = AuctionAggregatorService()

logger = get_logger(__name__)


@mcp_tool()
@with_supabase_logging
async def get_market_data(
    item_ids: Any = None,
    include_trends: bool = False,
    trend_hours: int = 24,
    max_results: int = 100,
    region: str = "us"
) -> Dict[str, Any]:
    """
    Get current commodity market prices from Supabase

    Returns current market snapshot with prices for region-wide commodities (ore, herbs, reagents, etc).
    Optionally includes historical price trends.

    Args:
        item_ids: Filter to specific items by ID. Can be: list of integers [1,2,3], string "[1,2,3]", or None (top items by market value)
        include_trends: Add historical price data
        trend_hours: Hours of history (if include_trends=True, max 168/7 days recommended)
        max_results: Max items to return (if item_ids=None)
        region: Region ('us' or 'eu')

    Returns:
        Current market snapshot + optional trend data:
        {
            "success": true,
            "region": "us",
            "timestamp": "2025-11-11T...",
            "market_data": {
                "123": {
                    "min_price": 1000,
                    "max_price": 5000,
                    "avg_price": 3000,
                    "median_price": 3100,
                    "auction_count": 42,
                    "total_quantity": 150,
                    "total_market_value": 450000
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
        # Normalize item_ids parameter
        if item_ids is not None:
            if isinstance(item_ids, int):
                item_ids = [item_ids]
            elif isinstance(item_ids, str):
                try:
                    parsed = json.loads(item_ids)
                    if isinstance(parsed, list):
                        if not all(isinstance(x, int) for x in parsed):
                            return error_response("All item IDs must be integers")
                        item_ids = parsed
                    elif isinstance(parsed, int):
                        item_ids = [parsed]
                    else:
                        return error_response("item_ids string must parse to an integer or list of integers")
                except json.JSONDecodeError:
                    return error_response(f"item_ids string is not valid JSON: {item_ids}")
            elif isinstance(item_ids, list):
                if not all(isinstance(x, int) for x in item_ids):
                    return error_response("All item IDs must be integers")
            else:
                return error_response(f"item_ids must be an integer, list of integers, or JSON string")

        logger.info(f"Getting commodity market data from Supabase ({region})")

        # Get Supabase client
        supabase_client = await get_supabase_client()
        if not supabase_client.client:
            return error_response("Supabase client not initialized")
        commodity_service = CommodityQueryService(supabase_client.client)

        # Get latest commodity data
        commodity_data = await commodity_service.get_latest_commodity_prices(
            region=region,
            item_ids=item_ids,
            hours_lookback=1,
            max_results=max_results
        )

        if not commodity_data:
            return error_response("No commodity data available. Check that n8n workflow is running.")

        # Aggregate the data (convert to format expected by aggregator)
        auctions_format = []
        for record in commodity_data:
            auctions_format.append({
                'id': record['auction_id'],
                'item': {'id': record['item_id']},
                'quantity': record['quantity'],
                'unit_price': record['unit_price'],
                'time_left': record['time_left']
            })

        # Aggregate auction data
        aggregated_raw = auction_aggregator.aggregate_auction_data(auctions_format)
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
            "region": region,
            "timestamp": utc_now_iso(),
            "total_auctions": len(commodity_data),
            "items_returned": len(aggregated),
            "market_data": aggregated
        }

        # Add historical trends if requested
        if include_trends and aggregated:
            item_ids_for_trends = [int(k) for k in aggregated.keys()]
            trends = await commodity_service.get_commodity_trends(
                item_ids=item_ids_for_trends,
                region=region,
                hours=trend_hours
            )
            if trends:
                # Convert to string keys
                response["trends"] = {str(k): v for k, v in trends.items()}
                response["trend_hours_analyzed"] = trend_hours

        return response

    except Exception as e:
        logger.error(f"Error getting market data: {str(e)}")
        return error_response(f"Market data failed: {str(e)}")


@mcp_tool()
@with_supabase_logging
async def analyze_market(
    operation: str = "opportunities",
    min_profit_margin: float = 20.0,
    max_results: int = 20,
    region: str = "us"
) -> Dict[str, Any]:
    """
    Analyze commodity markets from Supabase data

    Supports two operations:
    - "opportunities": Find items with high profit margins (profitable deals)
    - "health_check": Check data collection system health

    Args:
        operation: 'opportunities' (find deals) or 'health_check' (system status)
        min_profit_margin: Minimum profit % for opportunities (default 20%)
        max_results: Max opportunities to return
        region: Region ('us' or 'eu')

    Returns:
        For operation='opportunities':
        {
            "success": true,
            "region": "us",
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
            "healthy": true,
            "last_update": "2025-11-11T...",
            "minutes_old": 15.3
        }
    """
    try:
        if operation == "opportunities":
            return await _find_commodity_opportunities(
                region, min_profit_margin, max_results
            )
        elif operation == "health_check":
            return await _check_data_health(region)
        else:
            return error_response(f"Unknown operation: {operation}. Use 'opportunities' or 'health_check'")

    except Exception as e:
        logger.error(f"Error in market analysis: {str(e)}")
        return error_response(f"Market analysis failed: {str(e)}")


# Helper functions for commodity market analysis

async def _find_commodity_opportunities(
    region: str,
    min_profit_margin: float,
    max_results: int
) -> Dict[str, Any]:
    """Find commodity items with high profit margins from Supabase"""
    try:
        logger.info(f"Finding commodity opportunities ({region})")

        # Get Supabase client
        supabase_client = await get_supabase_client()
        if not supabase_client.client:
            return error_response("Supabase client not initialized")
        commodity_service = CommodityQueryService(supabase_client.client)

        # Get latest commodity data
        commodity_data = await commodity_service.get_latest_commodity_prices(
            region=region,
            item_ids=None,
            hours_lookback=1,
            max_results=1000  # Get more data to find opportunities
        )

        if not commodity_data:
            return error_response("No commodity data available")

        # Aggregate the data
        auctions_format = []
        for record in commodity_data:
            auctions_format.append({
                'id': record['auction_id'],
                'item': {'id': record['item_id']},
                'quantity': record['quantity'],
                'unit_price': record['unit_price'],
                'time_left': record['time_left']
            })

        aggregated_raw = auction_aggregator.aggregate_auction_data(auctions_format)
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
                        'profit_margin_pct': round(margin_pct, 2),
                        'auction_count': data['auction_count'],
                        'total_quantity': data['total_quantity'],
                        'potential_profit': price_range
                    })

        # Sort by profit margin
        opportunities.sort(key=lambda x: x['profit_margin_pct'], reverse=True)

        return {
            "success": True,
            "region": region,
            "opportunities_found": len(opportunities),
            "opportunities": opportunities[:max_results],
            "min_profit_margin": min_profit_margin,
            "timestamp": utc_now_iso()
        }

    except Exception as e:
        logger.error(f"Error finding opportunities: {str(e)}")
        return error_response(f"Opportunity search failed: {str(e)}")


async def _check_data_health(region: str) -> Dict[str, Any]:
    """Check health of commodity data collection from Supabase"""
    try:
        logger.info(f"Checking commodity data health ({region})")

        supabase_client = await get_supabase_client()
        if not supabase_client.client:
            return error_response("Supabase client not initialized")
        commodity_service = CommodityQueryService(supabase_client.client)

        health = await commodity_service.check_data_freshness(region=region)

        return {
            "success": True,
            **health
        }

    except Exception as e:
        logger.error(f"Error checking data health: {str(e)}")
        return error_response(f"Health check failed: {str(e)}")

