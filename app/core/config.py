"""
Configuration management for WoW Guild MCP Server
"""

import os
from functools import lru_cache
from typing import Optional
try:
    from pydantic import BaseSettings, Field
except ImportError:
    from pydantic.v1 import BaseSettings, Field
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class Settings(BaseSettings):
    """Application settings with environment variable support"""
    
    # Blizzard API Settings
    blizzard_client_id: str = Field(..., env="BLIZZARD_CLIENT_ID")
    blizzard_client_secret: str = Field(..., env="BLIZZARD_CLIENT_SECRET")
    blizzard_region: str = Field("us", env="BLIZZARD_REGION")
    blizzard_locale: str = Field("en_US", env="BLIZZARD_LOCALE")
    wow_version: str = Field("retail", env="WOW_VERSION")
    
    # Redis Settings
    redis_url: Optional[str] = Field(None, env="REDIS_URL")
    
    # Supabase Settings
    supabase_url: Optional[str] = Field(None, env="SUPABASE_URL")
    supabase_key: Optional[str] = Field(None, env="SUPABASE_KEY")

    # Server Settings
    port: int = Field(8000, env="PORT")
    host: str = Field("0.0.0.0", env="HOST")
    
    # API Timeout Settings
    api_timeout_total: int = Field(300, env="API_TIMEOUT_TOTAL")
    api_timeout_connect: int = Field(10, env="API_TIMEOUT_CONNECT")
    api_timeout_read: int = Field(60, env="API_TIMEOUT_READ")
    
    # OAuth Authentication Settings
    oauth_provider: Optional[str] = Field(None, env="OAUTH_PROVIDER")
    oauth_base_url: str = Field("http://localhost:8000", env="OAUTH_BASE_URL")

    # Discord OAuth
    discord_client_id: Optional[str] = Field(None, env="DISCORD_CLIENT_ID")
    discord_client_secret: Optional[str] = Field(None, env="DISCORD_CLIENT_SECRET")

    # Google OAuth
    google_client_id: Optional[str] = Field(None, env="GOOGLE_CLIENT_ID")
    google_client_secret: Optional[str] = Field(None, env="GOOGLE_CLIENT_SECRET")

    # Feature Flags
    enable_redis_caching: bool = Field(True, env="ENABLE_REDIS_CACHING")
    enable_supabase_logging: bool = Field(True, env="ENABLE_SUPABASE_LOGGING")
    enable_ai_analysis: bool = Field(True, env="ENABLE_AI_ANALYSIS")

    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached settings instance

    Returns:
        Singleton Settings instance

    Note:
        Uses lru_cache to ensure only one instance is created
    """
    return Settings()


# Global settings instance - use this for imports
settings = get_settings()