"""
Centralized service management for WoW Guild MCP Server
"""

from typing import Optional

from ..services.supabase_client import SupabaseRealTimeClient
from ..core.config import settings
from ..utils.logging_utils import get_logger

logger = get_logger(__name__)


class ServiceManager:
    """Manages initialization and access to all application services"""

    def __init__(self):
        self.supabase_client: Optional[SupabaseRealTimeClient] = None
        self._initialized = False

    async def initialize(self):
        """Initialize all services"""
        if self._initialized:
            logger.debug("Services already initialized")
            return

        try:
            # Initialize Supabase services
            await self._initialize_supabase()

            self._initialized = True
            logger.info("All services initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize services: {e}")
            raise

    async def _initialize_supabase(self):
        """Initialize Supabase services"""
        supabase_url = settings.supabase_url
        supabase_key = settings.supabase_key

        if not supabase_url or not supabase_key:
            logger.warning("Supabase environment variables not set - logging to Supabase disabled")
            return

        try:
            # Initialize direct Supabase client
            self.supabase_client = SupabaseRealTimeClient(supabase_url, supabase_key)
            await self.supabase_client.initialize()
            logger.info("Supabase direct client initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize Supabase services: {e}")
            self.supabase_client = None

    async def close(self):
        """Close all service connections"""
        if self.supabase_client:
            # Supabase client cleanup if needed
            pass

        self._initialized = False
    
    def is_initialized(self) -> bool:
        """Check if services are initialized"""
        return self._initialized


# Global service manager instance
service_manager = ServiceManager()


async def get_service_manager() -> ServiceManager:
    """Get or initialize the global service manager"""
    if not service_manager.is_initialized():
        await service_manager.initialize()
    return service_manager