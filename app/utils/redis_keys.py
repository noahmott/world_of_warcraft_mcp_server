"""
Redis key builder utilities for consistent cache key formatting

Provides standardized key generation functions for all Redis cache operations
"""

from typing import Optional


def guild_roster_key(realm: str, guild_name: str, game_version: str = "retail") -> str:
    """
    Build Redis key for guild roster cache

    Args:
        realm: Server realm name
        guild_name: Guild name
        game_version: WoW version (retail or classic)

    Returns:
        Formatted Redis key

    Example:
        >>> guild_roster_key("stormrage", "MyGuild", "retail")
        "guild:roster:retail:stormrage:myguild"
    """
    return f"guild:roster:{game_version.lower()}:{realm.lower()}:{guild_name.lower()}"


def economy_snapshot_key(realm: str, timestamp: str) -> str:
    """
    Build Redis key for economy snapshot cache

    Args:
        realm: Server realm name
        timestamp: Timestamp for the snapshot

    Returns:
        Formatted Redis key

    Example:
        >>> economy_snapshot_key("stormrage", "2024-01-01T12:00:00")
        "economy:snapshot:stormrage:2024-01-01T12:00:00"
    """
    return f"economy:snapshot:{realm.lower()}:{timestamp}"


def economy_latest_key(realm: str, game_version: str = "retail") -> str:
    """
    Build Redis key for latest economy snapshot

    Args:
        realm: Server realm name
        game_version: WoW version (retail or classic)

    Returns:
        Formatted Redis key

    Example:
        >>> economy_latest_key("stormrage")
        "economy:latest:retail:stormrage"
    """
    return f"economy:latest:{game_version.lower()}:{realm.lower()}"


def connected_realm_key(realm_slug: str, game_version: str = "retail") -> str:
    """
    Build Redis key for connected realm ID cache

    Args:
        realm_slug: Realm slug/name
        game_version: WoW version (retail or classic)

    Returns:
        Formatted Redis key

    Example:
        >>> connected_realm_key("area-52")
        "realm:connected:retail:area-52"
    """
    return f"realm:connected:{game_version.lower()}:{realm_slug.lower()}"


def auction_house_key(
    connected_realm_id: int,
    game_version: str = "retail",
    timestamp: Optional[str] = None
) -> str:
    """
    Build Redis key for auction house data cache

    Args:
        connected_realm_id: Connected realm ID
        game_version: WoW version (retail or classic)
        timestamp: Optional timestamp for historical data

    Returns:
        Formatted Redis key

    Example:
        >>> auction_house_key(3676, "retail")
        "auction:house:retail:3676"
        >>> auction_house_key(3676, "retail", "2024-01-01T12:00:00")
        "auction:house:retail:3676:2024-01-01T12:00:00"
    """
    base_key = f"auction:house:{game_version.lower()}:{connected_realm_id}"
    if timestamp:
        return f"{base_key}:{timestamp}"
    return base_key


def character_profile_key(realm: str, character_name: str, game_version: str = "retail") -> str:
    """
    Build Redis key for character profile cache

    Args:
        realm: Server realm name
        character_name: Character name
        game_version: WoW version (retail or classic)

    Returns:
        Formatted Redis key

    Example:
        >>> character_profile_key("stormrage", "Playerone")
        "character:profile:retail:stormrage:playerone"
    """
    return f"character:profile:{game_version.lower()}:{realm.lower()}:{character_name.lower()}"


def item_details_key(item_id: int, game_version: str = "retail") -> str:
    """
    Build Redis key for item details cache

    Args:
        item_id: Item ID
        game_version: WoW version (retail or classic)

    Returns:
        Formatted Redis key

    Example:
        >>> item_details_key(12345)
        "item:details:retail:12345"
    """
    return f"item:details:{game_version.lower()}:{item_id}"


def market_history_key(realm: str, item_id: int, game_version: str = "retail") -> str:
    """
    Build Redis key for market price history cache

    Args:
        realm: Server realm name
        item_id: Item ID
        game_version: WoW version (retail or classic)

    Returns:
        Formatted Redis key

    Example:
        >>> market_history_key("stormrage", 12345)
        "market:history:retail:stormrage:12345"
    """
    return f"market:history:{game_version.lower()}:{realm.lower()}:{item_id}"


def session_lock_key(session_id: str) -> str:
    """
    Build Redis key for session lock

    Args:
        session_id: Session identifier

    Returns:
        Formatted Redis key

    Example:
        >>> session_lock_key("snapshot_scheduler")
        "lock:session:snapshot_scheduler"
    """
    return f"lock:session:{session_id}"


def rate_limit_key(identifier: str) -> str:
    """
    Build Redis key for rate limiting

    Args:
        identifier: Unique identifier for rate limit tracking

    Returns:
        Formatted Redis key

    Example:
        >>> rate_limit_key("blizzard_api")
        "ratelimit:blizzard_api"
    """
    return f"ratelimit:{identifier}"
