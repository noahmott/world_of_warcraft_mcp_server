"""
Custom Discord Token Verifier for FastMCP OAuth

Discord uses opaque tokens (not JWTs), so we need to validate them
by calling Discord's API to verify the token and get user info.
"""

import logging
from typing import Optional, Dict, Any
import httpx
from fastmcp.server.auth.token_verifier import TokenVerifier, TokenVerificationResult

logger = logging.getLogger(__name__)


class DiscordTokenVerifier(TokenVerifier):
    """
    Token verifier for Discord OAuth tokens

    Discord doesn't use JWT tokens, so we validate by calling their
    /users/@me endpoint with the token. If it works, the token is valid.
    """

    def __init__(self):
        """Initialize the Discord token verifier"""
        self.discord_api_base = "https://discord.com/api/v10"
        self.user_info_endpoint = f"{self.discord_api_base}/users/@me"

    async def verify(self, token: str) -> TokenVerificationResult:
        """
        Verify a Discord access token by calling Discord's API

        Args:
            token: The Discord OAuth access token to verify

        Returns:
            TokenVerificationResult with user claims if valid, or error if invalid
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

                    # Extract user information
                    claims = {
                        "sub": user_data.get("id"),  # subject - user ID
                        "id": user_data.get("id"),  # Discord user ID
                        "username": user_data.get("username"),
                        "discriminator": user_data.get("discriminator"),
                        "global_name": user_data.get("global_name"),
                        "avatar": user_data.get("avatar"),
                        "email": user_data.get("email"),
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

                    logger.info(f"Successfully verified Discord token for user {user_data.get('username')} (ID: {user_data.get('id')})")

                    return TokenVerificationResult(
                        valid=True,
                        claims=claims,
                        error=None
                    )

                # Token is invalid
                elif response.status_code == 401:
                    logger.warning("Discord token verification failed: 401 Unauthorized")
                    return TokenVerificationResult(
                        valid=False,
                        claims=None,
                        error="Invalid or expired token"
                    )

                # Some other error
                else:
                    logger.error(f"Discord API returned unexpected status: {response.status_code}")
                    return TokenVerificationResult(
                        valid=False,
                        claims=None,
                        error=f"Discord API error: {response.status_code}"
                    )

        except httpx.TimeoutException:
            logger.error("Discord API request timed out")
            return TokenVerificationResult(
                valid=False,
                claims=None,
                error="Token verification timed out"
            )

        except Exception as e:
            logger.error(f"Error verifying Discord token: {e}", exc_info=True)
            return TokenVerificationResult(
                valid=False,
                claims=None,
                error=f"Token verification failed: {str(e)}"
            )

    async def refresh(self, refresh_token: str) -> Optional[Dict[str, Any]]:
        """
        Refresh a Discord access token using a refresh token

        Args:
            refresh_token: The Discord OAuth refresh token

        Returns:
            Dict with new access_token and refresh_token if successful, None otherwise
        """
        # Note: Token refresh is typically handled by the OAuthProxy automatically
        # This method is here for completeness but may not be called
        logger.warning("Discord token refresh should be handled by OAuthProxy")
        return None
