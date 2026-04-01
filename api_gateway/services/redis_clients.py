import redis
from config import REDIS_URL

# decode_responses=True → values come back as str, not bytes
redis_client = redis.from_url(REDIS_URL, decode_responses=True)

def get_redis():
    """
    Simple accessor. Mirrors get_db() pattern for consistency.
    Redis connections are thread-safe and reused from the pool.
    """
    return redis_client