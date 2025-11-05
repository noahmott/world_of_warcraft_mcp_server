"""
OAuth authentication configuration for MCP server

This module provides OAuth authentication using FastMCP's OAuthProxy,
which automatically handles the complete OAuth flow including:
- Authorization and token exchange
- Callback handling and redirects
- Token encryption and storage
- Token refresh and validation
- PKCE support
- Protected resource metadata endpoints

Supported providers:
- Discord: User authentication via Discord OAuth2
- Google: User authentication via Google OAuth2
"""

import logging
import os
from typing import Optional

from fastmcp.server.auth import OAuthProxy

from .config import settings

logger = logging.getLogger(__name__)


def create_discord_auth() -> OAuthProxy:
    """
    Create Discord OAuth provider configuration

    Discord OAuth Configuration:
    - Register your application at: https://discord.com/developers/applications
    - Add redirect URI: {OAUTH_BASE_URL}/oauth/callback
    - Required scopes: identify, email
    - OAuth endpoints:
        - Authorization: https://discord.com/api/oauth2/authorize
        - Token: https://discord.com/api/oauth2/token

    Returns:
        OAuthProxy configured for Discord authentication

    Raises:
        ValueError: If Discord credentials are not configured
    """
    if not settings.discord_client_id or not settings.discord_client_secret:
        raise ValueError(
            "Discord OAuth credentials not configured. "
            "Set DISCORD_CLIENT_ID and DISCORD_CLIENT_SECRET environment variables."
        )

    logger.info("Configuring Discord OAuth authentication")

    return OAuthProxy(
        upstream_authorization_endpoint="https://discord.com/api/oauth2/authorize",
        upstream_token_endpoint="https://discord.com/api/oauth2/token",
        upstream_client_id=settings.discord_client_id,
        upstream_client_secret=settings.discord_client_secret,
        base_url=settings.oauth_base_url,
        scopes=["identify", "email"]
    )


def create_google_auth() -> OAuthProxy:
    """
    Create Google OAuth provider configuration

    Google OAuth Configuration:
    - Register your application at: https://console.cloud.google.com
    - Configure OAuth consent screen
    - Create OAuth 2.0 Client ID (Web application)
    - Add redirect URI: {OAUTH_BASE_URL}/oauth/callback
    - Required scopes: openid, email, profile
    - OAuth endpoints:
        - Authorization: https://accounts.google.com/o/oauth2/v2/auth
        - Token: https://oauth2.googleapis.com/token

    Returns:
        OAuthProxy configured for Google authentication

    Raises:
        ValueError: If Google credentials are not configured
    """
    if not settings.google_client_id or not settings.google_client_secret:
        raise ValueError(
            "Google OAuth credentials not configured. "
            "Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET environment variables."
        )

    logger.info("Configuring Google OAuth authentication")

    return OAuthProxy(
        upstream_authorization_endpoint="https://accounts.google.com/o/oauth2/v2/auth",
        upstream_token_endpoint="https://oauth2.googleapis.com/token",
        upstream_client_id=settings.google_client_id,
        upstream_client_secret=settings.google_client_secret,
        base_url=settings.oauth_base_url,
        scopes=["openid", "email", "profile"]
    )


def create_oauth_provider() -> Optional[OAuthProxy]:
    """
    Factory function to create the configured OAuth provider

    Reads the OAUTH_PROVIDER environment variable to determine which
    provider to use. If not set or set to empty string, returns None
    and the server will run without authentication.

    Supported providers:
    - 'discord': Discord OAuth authentication
    - 'google': Google OAuth authentication
    - None or empty: No authentication (public access)

    Returns:
        OAuthProxy instance for the configured provider, or None if
        authentication is disabled

    Raises:
        ValueError: If an unsupported provider is specified or if
                   credentials are missing for the selected provider

    Example:
        # In your MCP server initialization:
        auth = create_oauth_provider()
        mcp = FastMCP("My Server", auth=auth)
    """
    provider = settings.oauth_provider

    if not provider:
        logger.info("No OAuth provider configured - server will run without authentication")
        return None

    provider = provider.lower().strip()

    if provider == "discord":
        return create_discord_auth()
    elif provider == "google":
        return create_google_auth()
    else:
        raise ValueError(
            f"Unsupported OAuth provider: {provider}. "
            f"Supported providers: discord, google"
        )


def get_auth_info() -> dict:
    """
    Get information about the current authentication configuration

    Returns:
        Dictionary containing authentication status and configuration details

    Example:
        >>> info = get_auth_info()
        >>> print(info)
        {
            'enabled': True,
            'provider': 'discord',
            'base_url': 'https://your-server.com',
            'scopes': ['identify', 'email']
        }
    """
    provider = settings.oauth_provider

    if not provider:
        return {
            'enabled': False,
            'provider': None,
            'message': 'Authentication is disabled'
        }

    provider = provider.lower().strip()

    if provider == "discord":
        return {
            'enabled': True,
            'provider': 'discord',
            'base_url': settings.oauth_base_url,
            'scopes': ['identify', 'email'],
            'authorization_endpoint': 'https://discord.com/api/oauth2/authorize',
            'token_endpoint': 'https://discord.com/api/oauth2/token'
        }
    elif provider == "google":
        return {
            'enabled': True,
            'provider': 'google',
            'base_url': settings.oauth_base_url,
            'scopes': ['openid', 'email', 'profile'],
            'authorization_endpoint': 'https://accounts.google.com/o/oauth2/v2/auth',
            'token_endpoint': 'https://oauth2.googleapis.com/token'
        }
    else:
        return {
            'enabled': False,
            'provider': provider,
            'error': f'Unsupported provider: {provider}'
        }
