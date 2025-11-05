"""
Supabase Client for Real-time Data Streaming

Handles authentication and real-time streaming of WoW guild data and activity logs to Supabase.
"""

import os
import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict

from supabase import acreate_client, AsyncClient
from supabase.lib.client_options import ClientOptions

logger = logging.getLogger(__name__)


@dataclass
class ActivityLogEntry:
    """Activity log entry for Supabase"""
    id: str
    session_id: str
    activity_type: str
    timestamp: str
    tool_name: Optional[str] = None
    request_data: Optional[Dict[str, Any]] = None
    response_data: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    duration_ms: Optional[float] = None
    reasoning: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    # OAuth user tracking fields
    user_id: Optional[str] = None
    session_id_ref: Optional[str] = None
    oauth_provider: Optional[str] = None
    oauth_user_id: Optional[str] = None


# Removed GuildDataEntry - keeping guild data in Redis for performance


class SupabaseRealTimeClient:
    """Supabase client for real-time data streaming"""
    
    def __init__(self, url: str = None, key: str = None):
        self.url = url or os.getenv("SUPABASE_URL")
        # Use service role key for server-side operations (bypasses RLS)
        self.key = key or os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_KEY")
        self.client: Optional[AsyncClient] = None
        self.channels = {}

        if not self.url or not self.key:
            raise ValueError("SUPABASE_URL and SUPABASE_KEY environment variables are required")
    
    async def initialize(self) -> None:
        """Initialize the Supabase client"""
        try:
            self.client = await acreate_client(
                self.url, 
                self.key,
                options=ClientOptions(
                    auto_refresh_token=True,
                    persist_session=True
                )
            )
            logger.info("Supabase client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Supabase client: {e}")
            raise
    
    async def authenticate_service(self) -> bool:
        """Authenticate as service user"""
        try:
            # For service-to-service communication, we use the service role key
            # The client is already authenticated with the provided key
            logger.info("Supabase service authentication successful")
            return True
        except Exception as e:
            logger.error(f"Supabase authentication failed: {e}")
            return False
    
    async def stream_activity_log(self, log_entry: ActivityLogEntry) -> bool:
        """Stream activity log entry to Supabase"""
        try:
            if not self.client:
                await self.initialize()
            
            # Insert activity log into Supabase table
            result = await self.client.table("activity_logs").insert(asdict(log_entry)).execute()
            
            if result.data:
                logger.debug(f"Activity log streamed successfully: {log_entry.id}")
                return True
            else:
                logger.error(f"Failed to stream activity log: {result}")
                return False
                
        except Exception as e:
            logger.error(f"Error streaming activity log: {e}")
            return False
    
    # Removed stream_guild_data - keeping guild data in Redis for performance

    async def upsert_user(self, oauth_provider: str, oauth_user_id: str,
                         user_data: Dict[str, Any]) -> Optional[str]:
        """
        Create or update user in Supabase users table

        Args:
            oauth_provider: OAuth provider name ('discord' or 'google')
            oauth_user_id: User ID from OAuth provider
            user_data: Dict with optional keys: email, username, display_name, avatar_url

        Returns:
            User UUID from database, or None if failed
        """
        try:
            if not self.client:
                await self.initialize()

            # Check if user exists
            existing = await self.client.table("users").select("id").eq(
                "oauth_provider", oauth_provider
            ).eq("oauth_user_id", oauth_user_id).execute()

            if existing.data:
                # User exists, update their info and last_seen_at
                user_id = existing.data[0]['id']
                update_data = {
                    "last_seen_at": datetime.now(timezone.utc).isoformat(),
                    **{k: v for k, v in user_data.items() if v is not None}
                }

                await self.client.table("users").update(update_data).eq("id", user_id).execute()
                logger.debug(f"Updated existing user {user_id}")
                return user_id
            else:
                # Create new user
                insert_data = {
                    "oauth_provider": oauth_provider,
                    "oauth_user_id": oauth_user_id,
                    **user_data
                }

                result = await self.client.table("users").insert(insert_data).execute()
                if result.data:
                    user_id = result.data[0]['id']
                    logger.info(f"Created new user {user_id} from {oauth_provider}")
                    return user_id
                else:
                    logger.error(f"Failed to create user: {result}")
                    return None

        except Exception as e:
            logger.error(f"Error upserting user: {e}")
            return None

    async def create_user_session(self, user_id: str, session_data: Dict[str, Any]) -> Optional[str]:
        """
        Create a new user session

        Args:
            user_id: User UUID from users table
            session_data: Dict with optional keys: client_type, client_version, ip_address, user_agent

        Returns:
            Session UUID from database, or None if failed
        """
        try:
            if not self.client:
                await self.initialize()

            insert_data = {
                "user_id": user_id,
                "is_active": True,
                **session_data
            }

            result = await self.client.table("user_sessions").insert(insert_data).execute()
            if result.data:
                session_id = result.data[0]['id']
                logger.info(f"Created new session {session_id} for user {user_id}")

                # Increment user's total_sessions count
                await self.client.table("users").update({
                    "total_sessions": self.client.table("users").select("total_sessions").eq("id", user_id)
                }).eq("id", user_id).execute()

                return session_id
            else:
                logger.error(f"Failed to create session: {result}")
                return None

        except Exception as e:
            logger.error(f"Error creating user session: {e}")
            return None

    async def end_user_session(self, session_id: str) -> bool:
        """Mark a user session as ended"""
        try:
            if not self.client:
                await self.initialize()

            await self.client.table("user_sessions").update({
                "is_active": False,
                "session_end": datetime.now(timezone.utc).isoformat()
            }).eq("id", session_id).execute()

            logger.info(f"Ended session {session_id}")
            return True

        except Exception as e:
            logger.error(f"Error ending session: {e}")
            return False

    async def create_activity_channel(self) -> None:
        """Create real-time channel for activity logs"""
        try:
            if not self.client:
                await self.initialize()
            
            channel = self.client.channel(
                "activity-logs",
                {"config": {"broadcast": {"ack": True, "self": False}}}
            )
            
            # Subscribe to database changes
            await channel.on(
                'postgres_changes',
                {
                    'event': 'INSERT',
                    'schema': 'public',
                    'table': 'activity_logs'
                },
                self._handle_activity_change
            ).subscribe()
            
            self.channels["activity"] = channel
            logger.info("Activity logs real-time channel created")
            
        except Exception as e:
            logger.error(f"Error creating activity channel: {e}")
    
    # Removed guild data channel - keeping guild data in Redis for performance
    
    async def broadcast_activity_update(self, message: Dict[str, Any]) -> bool:
        """Broadcast activity update via real-time channel"""
        try:
            if "activity" in self.channels:
                await self.channels["activity"].send_broadcast("activity-update", message)
                return True
            return False
        except Exception as e:
            logger.error(f"Error broadcasting activity update: {e}")
            return False
    
    # Removed guild data broadcasting - keeping guild data in Redis for performance
    
    def _handle_activity_change(self, payload):
        """Handle real-time activity log changes"""
        logger.info(f"Activity log change detected: {payload}")
    
    # Removed guild data change handler - keeping guild data in Redis for performance
    
    async def close(self) -> None:
        """Close all channels and connections"""
        try:
            for channel_name, channel in self.channels.items():
                await channel.unsubscribe()
                logger.info(f"Closed {channel_name} channel")
            
            if self.client:
                await self.client.auth.sign_out()
                logger.info("Supabase client closed")
                
        except Exception as e:
            logger.error(f"Error closing Supabase client: {e}")


# Global Supabase client instance
_supabase_client: Optional[SupabaseRealTimeClient] = None


async def get_supabase_client() -> SupabaseRealTimeClient:
    """Get or create Supabase client instance"""
    global _supabase_client
    if _supabase_client is None:
        _supabase_client = SupabaseRealTimeClient()
        await _supabase_client.initialize()
        await _supabase_client.authenticate_service()
    return _supabase_client


async def initialize_supabase_client() -> SupabaseRealTimeClient:
    """Initialize the Supabase client for activity monitoring only"""
    logger.info("Initializing Supabase client for activity logs and events")
    client = await get_supabase_client()
    await client.create_activity_channel()
    # Guild data remains in Redis for performance
    return client