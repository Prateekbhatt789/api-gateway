import os

DATABASE_URL = os.getenv("DATABASE_URL","sqlite:///./gateway.db")
# Header name clients must use to pass their key
API_KEY_HEADER = "x-api-key"

# Redis
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")

RATE_LIMIT_WINDOW = int(os.getenv("RATE_LIMIT_WINDOW",60))
RATE_LIMIT_REQUESTS = int(os.getenv("RATE_LIMIT_REQUESTS",5))

# Longest prefix should be matched first (handled in proxy.py)
SERVICE_MAP = {
    "/users":   "http://localhost:8001",
    "/orders":  "http://localhost:8002",   # placeholder
    "/products":"http://localhost:8003",   # placeholder
}

# Timeout for forwarded requests (seconds)
PROXY_TIMEOUT = int(os.getenv("PROXY_TIMEOUT", 10))