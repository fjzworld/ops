"""
Token blacklist using Redis for server-side JWT invalidation.
Tokens are blacklisted on logout with a TTL matching their remaining lifetime.
"""
import logging
from app.core.config import settings

logger = logging.getLogger(__name__)

BLACKLIST_PREFIX = "token_blacklist:"


def _get_redis_client():
    """Lazy import to avoid circular dependencies with rate_limit module."""
    from app.core.rate_limit import redis_client
    return redis_client


def blacklist_token(token: str, ttl_seconds: int) -> bool:
    """
    Add a token to the blacklist with TTL matching remaining token lifetime.

    Args:
        token: The JWT token string
        ttl_seconds: Time-to-live in seconds (remaining token lifetime)

    Returns:
        True if successfully blacklisted, False otherwise
    """
    try:
        client = _get_redis_client()
        key = f"{BLACKLIST_PREFIX}{token}"
        client.setex(key, ttl_seconds, "1")
        return True
    except Exception as e:
        logger.error(f"Failed to blacklist token: {e}")
        return False


def is_token_blacklisted(token: str) -> bool:
    """
    Check if a token has been blacklisted (i.e. user logged out).

    Args:
        token: The JWT token string

    Returns:
        True if token is blacklisted, False otherwise
    """
    try:
        client = _get_redis_client()
        key = f"{BLACKLIST_PREFIX}{token}"
        return client.exists(key) > 0
    except Exception as e:
        # Fail open: if Redis is down, allow the request but log warning
        logger.warning(f"Redis unavailable for token blacklist check: {e}. Allowing request.")
        return False
