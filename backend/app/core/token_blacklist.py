"""
Token blacklist using Redis for server-side JWT invalidation.
Tokens are blacklisted on logout with a TTL matching their remaining lifetime.
"""

import logging
from cachetools import TTLCache

logger = logging.getLogger(__name__)

BLACKLIST_PREFIX = "token_blacklist:"

# 本地短期缓存，Redis 不可用时兜底（5 分钟 TTL）
_local_blacklist = TTLCache(maxsize=10000, ttl=300)


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
    key = f"{BLACKLIST_PREFIX}{token}"
    try:
        client = _get_redis_client()
        client.setex(key, ttl_seconds, "1")
        _local_blacklist[key] = True  # 同时写本地缓存
        return True
    except Exception as e:
        logger.error(f"Failed to blacklist token in Redis: {e}")
        _local_blacklist[key] = True
        return False


def is_token_blacklisted(token: str) -> bool:
    """
    Check if a token has been blacklisted (i.e. user logged out).

    Args:
        token: The JWT token string

    Returns:
        True if token is blacklisted, False otherwise
    """
    key = f"{BLACKLIST_PREFIX}{token}"

    # 先查本地缓存（快速路径）
    if key in _local_blacklist:
        return True

    try:
        client = _get_redis_client()
        exists = client.exists(key) > 0
        if exists:
            _local_blacklist[key] = True
        return exists
    except Exception as e:
        logger.warning(
            f"Redis unavailable for token blacklist check: {e}. "
            f"Falling back to local cache."
        )
        return key in _local_blacklist
