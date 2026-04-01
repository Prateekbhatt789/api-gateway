api_gateway/
│
├── main.py                  # FastAPI app init, middleware registration
├── config.py                # Settings (env vars, service map, limits)
│
├── middleware/
│   ├── auth.py              # API key validation
│   ├── rate_limiter.py      # Redis INCR/EXPIRE logic
│   └── logger.py            # Async MongoDB write
│
├── routers/
│   └── proxy.py             # Catch-all route → httpx forwarding
│
├── services/
│   ├── redis_client.py      # Redis connection + helpers
│   ├── mongo_client.py      # MongoDB connection + log schema
│   └── sql_client.py        # SQLAlchemy setup + User/APIKey models
│
├── models/
│   ├── sql_models.py        # SQLAlchemy ORM models
│   └── log_schema.py        # Pydantic model for log documents
│
└── tests/
    ├── test_auth.py
    ├── test_rate_limit.py
    └── test_proxy.py


SQL-lite schema
Users: id, email, created_at
APIKeys: id, user_id (FK), key_hash, is_active, created_at


Key:   rate:{user_id}:{endpoint}
Op:    INCR → if result == 1, SET EXPIRE (e.g., 60s)
Check: if current count > limit → 429


ConcernIssue
Your Answer
Redis downRate limiter and cache both failFail open on rate limit; 
log the Redis errorSQL downAuth fails for all requestsReturn 503; consider brief in-memory key cacheLarge request bodyBuffering kills memoryStream the body via httpx, don't load it allClock skewRate limit windows behave oddly across restartsRedis TTL handles this correctlyConcurrent requestsRace condition in INCRRedis INCR is atomic — no race conditionAPI key rotationOld key still cached in RedisKeep Redis TTL short (60s); acceptable lagCircular routingGateway routes to itselfStatic service map prevents this by design


