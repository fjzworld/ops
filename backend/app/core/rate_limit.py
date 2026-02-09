"""
Rate limiting configuration for API endpoints
Uses Redis as storage backend for distributed rate limiting
"""
import logging
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from app.core.config import settings
from functools import wraps
from fastapi import Request, HTTPException
import redis

logger = logging.getLogger(__name__)

# Initialize Redis client for rate limiting
redis_client = redis.from_url(
    settings.REDIS_URL,
    decode_responses=True,
    socket_connect_timeout=5,
    socket_timeout=5,
    health_check_interval=30
)

# Initialize Limiter with Redis storage
limiter = Limiter(
    key_func=get_remote_address,
    storage_uri=settings.REDIS_URL,
    default_limits=["200 per minute", "1000 per hour"]
)


def auth_rate_limit():
    """
    Decorator for authentication endpoints (login, register)
    More strict limits to prevent brute force attacks
    """
    return limiter.limit("5 per minute")


def api_rate_limit():
    """
    Decorator for general API endpoints
    Standard rate limiting for authenticated users
    """
    return limiter.limit("60 per minute")


def sensitive_operation_limit():
    """
    Decorator for sensitive operations (delete, update)
    Stricter limits for destructive operations
    """
    return limiter.limit("10 per minute")


def check_rate_limit(request: Request, max_requests: int = 60, window: int = 60):
    """
    Manual rate limit check for custom endpoints
    
    Args:
        request: FastAPI request object
        max_requests: Maximum requests allowed in window
        window: Time window in seconds
    
    Raises:
        HTTPException: If rate limit exceeded
    """
    client_ip = get_remote_address(request)
    key = f"ratelimit:{client_ip}:{request.url.path}"
    
    try:
        current = redis_client.get(key)
        if current is None:
            redis_client.setex(key, window, 1)
        elif int(current) >= max_requests:
            raise HTTPException(
                status_code=429,
                detail=f"Rate limit exceeded. Try again in {window} seconds."
            )
        else:
            redis_client.incr(key)
    except redis.RedisError as e:
        # If Redis is down, allow the request (fail open) but log warning
        logger.warning(f"Redis unavailable for rate limiting: {e}. Allowing request.")


# Exception handler for rate limit exceeded
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    """Custom handler for rate limit exceeded"""
    return HTTPException(
        status_code=429,
        detail="Too many requests. Please slow down."
    )
