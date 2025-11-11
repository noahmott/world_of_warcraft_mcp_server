"""
Configuration management for WoW Guild MCP Server
"""

from functools import lru_cache
from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class Settings(BaseSettings):
    """Application settings with environment variable support"""
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False)

    # Blizzard API Settings
    blizzard_client_id: str = Field(..., validation_alias="BLIZZARD_CLIENT_ID")
    blizzard_client_secret: str = Field(..., validation_alias="BLIZZARD_CLIENT_SECRET")
    blizzard_region: str = Field(default="us", validation_alias="BLIZZARD_REGION")
    blizzard_locale: str = Field(default="en_US", validation_alias="BLIZZARD_LOCALE")
    wow_version: str = Field(default="retail", validation_alias="WOW_VERSION")

    # Supabase Settings
    supabase_url: Optional[str] = Field(default=None, validation_alias="SUPABASE_URL")
    supabase_key: Optional[str] = Field(default=None, validation_alias="SUPABASE_KEY")

    # Server Settings
    port: int = Field(default=8000, validation_alias="PORT")
    host: str = Field(default="0.0.0.0", validation_alias="HOST")

    # API Timeout Settings
    api_timeout_total: int = Field(default=300, validation_alias="API_TIMEOUT_TOTAL")
    api_timeout_connect: int = Field(default=10, validation_alias="API_TIMEOUT_CONNECT")
    api_timeout_read: int = Field(default=60, validation_alias="API_TIMEOUT_READ")

    # OAuth Authentication Settings
    oauth_provider: Optional[str] = Field(default=None, validation_alias="OAUTH_PROVIDER")
    oauth_base_url: str = Field(default="http://localhost:8000", validation_alias="OAUTH_BASE_URL")

    # Discord OAuth
    discord_client_id: Optional[str] = Field(default=None, validation_alias="DISCORD_CLIENT_ID")
    discord_client_secret: Optional[str] = Field(default=None, validation_alias="DISCORD_CLIENT_SECRET")

    # Feature Flags
    enable_supabase_logging: bool = Field(default=True, validation_alias="ENABLE_SUPABASE_LOGGING")
    enable_ai_analysis: bool = Field(default=True, validation_alias="ENABLE_AI_ANALYSIS")


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached settings instance

    Returns:
        Singleton Settings instance

    Note:
        Uses lru_cache to ensure only one instance is created
    """
    return Settings()  # type: ignore[call-arg]


# Global settings instance - use this for imports
settings = get_settings()