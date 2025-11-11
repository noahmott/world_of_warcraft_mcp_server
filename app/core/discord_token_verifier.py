"""
Custom Discord Token Verifier for FastMCP OAuth

Discord uses opaque tokens (not JWTs), so we need to validate them
by calling Discord's API to verify the token and get user info.
"""

import logging
from typing import Optional, Dict, Any
import httpx
from mcp.server.auth.provider import TokenVerifier, AccessToken
from contextvars import ContextVar

logger = logging.getLogger(__name__)

# Global reference to supabase client (will be set from main server)
_supabase_client = None

# Context variable to pass user info to tools
_user_context: ContextVar[Optional[Dict[str, Any]]] = ContextVar('user_context', default=None)

def set_supabase_client(client):
    """Set the global Supabase client for user tracking"""
    global _supabase_client
    _supabase_client = client

def get_user_context() -> Optional[Dict[str, Any]]:
    """Get the current user context"""
    return _user_context.get()

def set_user_context(user_info: Dict[str, Any]):
    """Set the current user context"""
    _user_context.set(user_info)


class DiscordTokenVerifier(TokenVerifier):
    """
    Token verifier for Discord OAuth tokens

    Discord doesn't use JWT tokens, so we validate by calling their
    /users/@me endpoint with the token. If it works, the token is valid.
    """

    def __init__(self, client_id: str):
        """Initialize the Discord token verifier

        Args:
            client_id: The Discord application client ID
        """
        self.discord_api_base = "https://discord.com/api/v10"
        self.user_info_endpoint = f"{self.discord_api_base}/users/@me"
        self.required_scopes = ["identify", "email"]  # Discord OAuth scopes
        self.client_id = client_id

    async def verify_token(self, token: str) -> Optional[AccessToken]:
        """
        Verify a Discord access token by calling Discord's API

        Args:
            token: The Discord OAuth access token to verify

        Returns:
            AccessToken with user claims if valid, None if invalid
        """
        try:
            # Call Discord API to verify token and get user info
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    self.user_info_endpoint,
                    headers={
                        "Authorization": f"Bearer {token}",
                        "Content-Type": "application/json"
                    },
                    timeout=10.0
                )

                # Token is valid if we get a 200 response
                if response.status_code == 200:
                    user_data = response.json()

                    # Extract user information for AccessToken
                    user_id = user_data.get("id")
                    email = user_data.get("email")
                    username = user_data.get("username")

                    logger.info(f"Successfully verified Discord token for user {username} (ID: {user_id})")

                    # Track user in Supabase if client is available
                    if _supabase_client:
                        try:
                            logger.info(f"Supabase client available for user tracking, key starts with: {_supabase_client.key[:20]}...")
                            user_tracking_data = {
                                "email": email,
                                "username": username,
                                "display_name": user_data.get("global_name") or username,
                                "avatar_url": f"https://cdn.discordapp.com/avatars/{user_id}/{user_data.get('avatar')}.png" if user_data.get('avatar') else None
                            }
                            db_user_id = await _supabase_client.upsert_user(
                                oauth_provider="discord",
                                oauth_user_id=user_id,
                                user_data=user_tracking_data
                            )
                            if db_user_id:
                                logger.info(f"Tracked user in Supabase: {db_user_id}")

                                # Store user context for tools to access
                                set_user_context({
                                    "db_user_id": db_user_id,
                                    "oauth_provider": "discord",
                                    "oauth_user_id": user_id,
                                    "user_info": user_data
                                })

                                # Check if user already has an active session
                                # Only create a new session if they don't have one yet
                                existing_sessions = await _supabase_client.client.table("user_sessions").select("id").eq("user_id", db_user_id).eq("is_active", True).execute()

                                if not existing_sessions.data:
                                    # Create a session for this user
                                    session_data = {
                                        "client_type": "mcp_client",
                                        "metadata": {
                                            "discord_username": username,
                                            "discord_id": user_id
                                        }
                                    }
                                    session_id = await _supabase_client.create_user_session(db_user_id, session_data)
                                    if session_id:
                                        logger.info(f"Created new session in Supabase: {session_id}")
                                else:
                                    logger.debug(f"User {db_user_id} already has {len(existing_sessions.data)} active session(s), not creating a new one")
                        except Exception as e:
                            logger.error(f"Failed to track user in Supabase: {e}")
                    else:
                        logger.warning("Supabase client not available for user tracking")

                    # Return AccessToken with user claims
                    return AccessToken(  # type: ignore[call-arg]
                        token=token,
                        client_id=self.client_id,
                        user_id=user_id,
                        scopes=["identify", "email"],  # Discord OAuth scopes
                        claims={
                            "sub": user_id,  # subject - user ID
                            "id": user_id,  # Discord user ID
                            "username": username,
                            "discriminator": user_data.get("discriminator"),
                            "global_name": user_data.get("global_name"),
                            "avatar": user_data.get("avatar"),
                            "email": email,
                            "verified": user_data.get("verified", False),
                            "mfa_enabled": user_data.get("mfa_enabled", False),
                            "locale": user_data.get("locale"),
                            "flags": user_data.get("flags", 0),
                            "premium_type": user_data.get("premium_type", 0),
                            "public_flags": user_data.get("public_flags", 0),
                            # Add issuer for consistency with JWT pattern
                            "iss": "https://discord.com",
                            "aud": "discord_oauth"
                        }
                    )

                # Token is invalid
                elif response.status_code == 401:
                    logger.warning("Discord token verification failed: 401 Unauthorized")
                    return None

                # Some other error
                else:
                    logger.error(f"Discord API returned unexpected status: {response.status_code}")
                    return None

        except httpx.TimeoutException:
            logger.error("Discord API request timed out")
            return None

        except Exception as e:
            logger.error(f"Error verifying Discord token: {e}", exc_info=True)
            return None

    async def refresh(self, _refresh_token: str) -> Optional[Dict[str, Any]]:
        """
        Refresh a Discord access token using a refresh token

        Args:
            _refresh_token: The Discord OAuth refresh token (unused - handled by OAuthProxy)

        Returns:
            Dict with new access_token and refresh_token if successful, None otherwise
        """
        # Note: Token refresh is typically handled by the OAuthProxy automatically
        # This method is here for completeness but may not be called
        logger.warning("Discord token refresh should be handled by OAuthProxy")
        return None
