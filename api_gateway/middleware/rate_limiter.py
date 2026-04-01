# middleware/rate_limiter.py
from fastapi import Request, HTTPException
from redis import Redis
from config import RATE_LIMIT_REQUESTS, RATE_LIMIT_WINDOW

def build_rate_limit_key(user_id: int, path: str) -> str:
    """
    Scoped per user AND per endpoint.
    A user can hit /search 5x and /register 5x — independent windows.
    e.g. "rate:1:/me"
    """
    return f"rate:{user_id}:{path}"

def check_rate_limit(request: Request, redis: Redis):
    user    = request.state.user          # set by auth middleware
    key     = build_rate_limit_key(user.id, request.url.path)

    # INCR is atomic — no race condition even under concurrent requests
    count   = redis.incr(key)

    if count == 1:
        # First request in this window — start the expiry clock
        redis.expire(key, RATE_LIMIT_WINDOW)

    if count > RATE_LIMIT_REQUESTS:
        ttl = redis.ttl(key)              # seconds until window resets
        raise HTTPException(
            status_code=429,
            detail={
                "error":       "Rate limit exceeded.",
                "limit":       RATE_LIMIT_REQUESTS,
                "window_sec":  RATE_LIMIT_WINDOW,
                "retry_after": ttl
            }
        )

    # Attach counts to request state — useful for adding headers later
    request.state.rate_limit_count     = count
    request.state.rate_limit_remaining = RATE_LIMIT_REQUESTS - count