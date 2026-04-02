import json
from redis import Redis
from fastapi import Request
from fastapi.responses import Response
from config import CACHE_TTL

def build_cache_key(request: Request) -> str:
    """
    Cache key must include full path + query string.
    /users?page=1 and /users?page=2 must be separate cache entries.
    e.g. "cache:GET:/services/users/1"
         "cache:GET:/services/users?page=2&limit=10"
    """
    path = request.url.path
    qs   = request.url.query
    key  = f"cache:GET:{path}"
    if qs:
        key += f"?{qs}"
    return key

def get_cached_response(request: Request, redis: Redis) -> Response | None:
    """
    Returns a Response if cache hit, None if miss.
    Only attempts cache on GET requests.
    """
    if request.method != "GET":
        return None

    key  = build_cache_key(request)
    data = redis.get(key)

    if not data:
        request.state.cache_hit = False
        return None

    # Deserialize stored response
    cached = json.loads(data)
    request.state.cache_hit = True

    return Response(
        content     = cached["body"],
        status_code = cached["status_code"],
        media_type  = "application/json",
        headers     = {"X-Cache": "HIT"}
    )

def store_response(request: Request, body: bytes, status_code: int, redis: Redis):
    """
    Store backend response in Redis.
    Only cache successful GET responses (2xx).
    Never cache errors — a 500 today might be 200 tomorrow.
    """
    if request.method != "GET":
        return

    if not (200 <= status_code < 300):
        return

    key  = build_cache_key(request)
    data = json.dumps({
        "body":        body.decode("utf-8"),
        "status_code": status_code,
    })
    redis.setex(key, CACHE_TTL, data)