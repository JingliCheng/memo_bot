# rate_limiter.py
"""
Rate limiting module for user-based rate limiting.
Uses slowapi with uid-based keys to prevent one user from affecting others.
"""
import os
from typing import Optional
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
import redis
from dotenv import load_dotenv

load_dotenv()

# Import monitoring
from monitoring import metrics

# Rate limit configuration per endpoint
RATE_LIMITS = {
    "/api/chat": "10/minute",           # Chat is most expensive (OpenAI calls)
    "/api/memory": "30/minute",          # Memory operations are lighter
    "/api/messages": "30/minute",        # Message retrieval is lightweight
    "/api/profile-card": "20/minute",    # Profile Card operations
    "/api/profile-card/history": "10/minute",  # Profile history is heavier
    "/api/profile-card/stats": "20/minute",    # Profile stats
    "/whoami": "60/minute",              # Auth check is very lightweight
}

# Default rate limit for unlisted endpoints
DEFAULT_RATE_LIMIT = "30/minute"

def get_user_identifier(request: Request) -> str:
    """
    Create a rate limiting key based on user UID and IP.
    This prevents one user from affecting others behind the same NAT.
    """
    # Try to get UID from the request (set by auth middleware)
    uid = getattr(request.state, 'uid', None)
    if uid:
        # Use UID + IP for better isolation
        ip = get_remote_address(request)
        return f"user:{uid}:{ip}"
    else:
        # Fallback to IP only (shouldn't happen with proper auth)
        return f"ip:{get_remote_address(request)}"

def create_limiter() -> Limiter:
    """
    Create and configure the rate limiter.
    Uses Redis if available, otherwise falls back to in-memory storage.
    """
    # Try to connect to Redis (optional)
    redis_url = os.getenv("REDIS_URL")
    if redis_url:
        try:
            redis_client = redis.from_url(redis_url)
            redis_client.ping()  # Test connection
            print(f"Rate limiter: Using Redis at {redis_url}")
            return Limiter(
                key_func=get_user_identifier,
                storage_uri=redis_url,
                default_limits=[DEFAULT_RATE_LIMIT]
            )
        except Exception as e:
            print(f"Redis connection failed: {e}, falling back to in-memory storage")
    
    # Fallback to in-memory storage
    print("Rate limiter: Using in-memory storage")
    return Limiter(
        key_func=get_user_identifier,
        default_limits=[DEFAULT_RATE_LIMIT]
    )

# Create the global limiter instance
limiter = create_limiter()

def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    """
    Custom handler for rate limit exceeded errors.
    Provides helpful information about the rate limit.
    """
    # Extract retry_after from the exception if available
    retry_after = getattr(exc, 'retry_after', None)
    
    # Record rate limit metrics
    uid = getattr(request.state, 'uid', 'unknown')
    endpoint = request.url.path
    
    # Get remaining quota (this would need to be implemented based on your rate limiter)
    remaining_quota = 0  # Placeholder
    
    metrics.record_rate_limit_metrics(
        user_id=uid,
        endpoint=endpoint,
        rate_limit_hit=True,
        remaining_quota=remaining_quota
    )
    
    response = JSONResponse(
        status_code=429,
        content={
            "error": "Rate limit exceeded",
            "message": f"Too many requests. Limit: {exc.detail}",
            "retry_after": retry_after,
            "endpoint": endpoint,
            "uid": uid
        }
    )
    
    # Add retry-after header if available
    if retry_after:
        response.headers["Retry-After"] = str(retry_after)
    return response

def get_rate_limit_for_endpoint(endpoint: str) -> str:
    """
    Get the rate limit string for a specific endpoint.
    Returns the configured limit or default.
    """
    return RATE_LIMITS.get(endpoint, DEFAULT_RATE_LIMIT)

def apply_rate_limit(endpoint: str):
    """
    Decorator factory for applying rate limits to endpoints.
    Usage: @apply_rate_limit("/api/chat")
    """
    limit = get_rate_limit_for_endpoint(endpoint)
    return limiter.limit(limit)
