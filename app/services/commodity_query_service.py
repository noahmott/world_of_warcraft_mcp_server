"""
Commodity Query Service for Supabase

Queries commodity auction data from Supabase instead of Blizzard API
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta, timezone

logger = logging.getLogger(__name__)


class CommodityQueryService:
    """Service for querying commodity auction data from Supabase"""

    def __init__(self, supabase_client: Any):
        """
        Initialize with Supabase AsyncClient

        Args:
            supabase_client: The AsyncClient from SupabaseRealTimeClient.client
        """
        self.client = supabase_client

    async def get_latest_commodity_prices(
        self,
        region: str = "us",
        item_ids: Optional[List[int]] = None,
        hours_lookback: int = 1,
        max_results: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get latest commodity prices from Supabase

        Args:
            region: Region (us, eu, etc.)
            item_ids: Optional list of item IDs to filter
            hours_lookback: How many hours back to look for data (default 1)
            max_results: Maximum results if no item_ids specified

        Returns:
            List of commodity auction records
        """
        try:
            # Calculate cutoff time
            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours_lookback)

            # Validate client
            if not self.client:
                logger.error("Supabase client is None")
                return []

            # Build query (case-insensitive region match)
            query = self.client.table("commodity_auctions").select("*")
            query = query.ilike("region", region)
            query = query.gte("captured_at", cutoff_time.isoformat())

            # Filter by item IDs if provided
            if item_ids:
                query = query.in_("item_id", item_ids)

            # Order by most recent first
            query = query.order("captured_at", desc=True)

            # Limit results if no specific items requested
            if not item_ids:
                query = query.limit(max_results * 10)  # Get more raw data to aggregate

            # Execute query
            response = await query.execute()

            if response.data:
                logger.info(f"Retrieved {len(response.data)} commodity auctions from Supabase")
                return response.data
            else:
                logger.warning(f"No commodity data found for region {region}")
                return []

        except AttributeError as e:
            logger.error(f"AttributeError in commodity query - client type: {type(self.client)}, error: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return []
        except Exception as e:
            logger.error(f"Error querying commodity prices from Supabase: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return []

    async def get_commodity_trends(
        self,
        item_ids: List[int],
        region: str = "us",
        hours: int = 24
    ) -> Dict[int, List[Dict[str, Any]]]:
        """
        Get historical price trends for specific items from pre-aggregated trends table

        Args:
            item_ids: List of item IDs to get trends for
            region: Region (us, eu, etc.)
            hours: Hours of historical data to retrieve

        Returns:
            Dict mapping item_id -> list of price points over time (one per snapshot)
        """
        try:
            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)

            # Query the pre-aggregated commodity_trends table
            response = self.client.table("commodity_trends").select(
                "item_id,captured_at,min_price,max_price,mean_price,median_price,auction_count,total_quantity"
            ).ilike(
                "region", region
            ).in_(
                "item_id", item_ids
            ).gte(
                "captured_at", cutoff_time.isoformat()
            ).order("item_id").order("captured_at").execute()

            if not response.data:
                logger.warning(f"No historical data found for {len(item_ids)} items")
                return {}

            # Group by item_id
            from collections import defaultdict
            aggregated_trends: Dict[int, List[Dict[str, Any]]] = defaultdict(list)

            for record in response.data:
                item_id = record["item_id"]
                aggregated_trends[item_id].append({
                    "timestamp": record["captured_at"],
                    "min_price": record["min_price"],
                    "max_price": record["max_price"],
                    "mean_price": float(record["mean_price"]),
                    "median_price": record["median_price"],
                    "auction_count": record["auction_count"],
                    "total_quantity": record["total_quantity"]
                })

            total_snapshots = max(len(v) for v in aggregated_trends.values()) if aggregated_trends else 0
            logger.info(f"Retrieved trends for {len(aggregated_trends)} items across {total_snapshots} snapshots")
            return dict(aggregated_trends)

        except Exception as e:
            logger.error(f"Error getting commodity trends: {e}")
            return {}

    async def check_data_freshness(self, region: str = "us") -> Dict[str, Any]:
        """
        Check how fresh the commodity data is

        Returns health status of data collection
        """
        try:
            # Validate client
            if not self.client:
                logger.error("Supabase client is None")
                return {
                    "healthy": False,
                    "error": "Supabase client not initialized"
                }

            # Get most recent record (case-insensitive region match)
            response = await self.client.table("commodity_auctions").select(
                "captured_at"
            ).ilike(
                "region", region
            ).order(
                "captured_at", desc=True
            ).limit(1).execute()

            if not response.data:
                return {
                    "healthy": False,
                    "last_update": None,
                    "minutes_old": None,
                    "message": "No commodity data found"
                }

            last_update = datetime.fromisoformat(response.data[0]["captured_at"].replace('Z', '+00:00'))
            age = datetime.now(timezone.utc) - last_update
            minutes_old = age.total_seconds() / 60
            hours_old = minutes_old / 60

            # Consider healthy if updated within last 6 hours (n8n runs every 6 hours)
            healthy = minutes_old < 360

            return {
                "healthy": healthy,
                "last_update": last_update.isoformat(),
                "hours_old": round(hours_old, 1),
                "message": f"Last update {round(hours_old, 1)} hours ago"
            }

        except AttributeError as e:
            logger.error(f"AttributeError in data freshness check - client type: {type(self.client)}, error: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return {
                "healthy": False,
                "error": f"AttributeError: {str(e)}"
            }
        except Exception as e:
            logger.error(f"Error checking data freshness: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return {
                "healthy": False,
                "error": str(e)
            }
