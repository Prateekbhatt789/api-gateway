import os

DATABASE_URL = os.getenv("DATABASE_URL","sqlite:///./gateway.db")
# Header name clients must use to pass their key
API_KEY_HEADER = "x-api-key"