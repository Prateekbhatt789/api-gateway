import os

DATABASE_URL = os.getenv("DATABASE_URL","sqlite:///./gateway.db")
# Header name clients must use to pass their key
API_KEY_HEADER = "x-api-key"

# Redis
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")

RATE_LIMIT_WINDOW = int(os.getenv("RATE_LIMIT_WINDOW",60))
RATE_LIMIT_REQUESTS = int(os.getenv("RATE_LIMIT_REQUESTS",5))