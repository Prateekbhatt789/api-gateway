# API Gateway

A production-ready API gateway built with FastAPI. Handles authentication, rate limiting, request proxying, caching, and observability — all in a single service sitting in front of your backend microservices.

---

## Architecture

```
Client
  │
  ▼
FastAPI Gateway  (this repo)
  ├── Auth middleware        → validates API key against PostgreSQL
  ├── Rate limiter           → per-user, per-endpoint via Redis
  ├── Proxy router           → forwards to backend services
  ├── Cache layer            → GET response caching via Redis
  ├── Request logger         → background write to MongoDB
  └── Admin router           → observability endpoints (admin key required)
```

---

## Features

- **API key authentication** — SHA-256 hashed keys stored in PostgreSQL, never in plaintext
- **Per-user rate limiting** — scoped per user AND per endpoint, atomic Redis `INCR` with sliding window
- **Reverse proxy** — forwards any HTTP method to backend services, strips hop-by-hop headers, injects tracing headers
- **Response caching** — GET-only, 2xx-only caching with Redis, configurable TTL
- **Request logging** — every request logged to MongoDB with latency, status, cache hit, upstream service, and user info
- **Admin observability** — separate admin key, protected endpoints for stats and user management
- **TTL log expiry** — MongoDB TTL index auto-deletes logs after 30 days

---

## Stack

| Layer | Technology |
|---|---|
| Framework | FastAPI |
| Auth store | PostgreSQL (via SQLAlchemy) |
| Cache + Rate limiting | Redis |
| Request logs | MongoDB (via Motor async) |
| HTTP proxy | httpx async |

---

## Project Structure

```
.
├── main.py                    # App entry point, HTTP middleware chain
├── config.py                  # All env vars and constants
├── router/
│   ├── proxy.py               # Catch-all proxy route /services/{path}
│   ├── register.py            # User + admin registration
│   └── admin.py               # Admin observability endpoints
├── middleware/
│   ├── auth.py                # API key authentication
│   ├── admin_auth.py          # Admin key guard (require_admin dependency)
│   ├── rate_limiter.py        # Redis-backed rate limiting
│   └── cache.py               # Redis response cache
├── models/
│   ├── sql_models.py          # SQLAlchemy User model
│   └── log_schema.py          # Pydantic RequestLog schema
├── services/
│   ├── sql_clients.py         # PostgreSQL session management
│   ├── redis_clients.py       # Redis client
│   └── mongo_clients.py       # MongoDB client + indexes
└── schema/
    └── schema.py              # Pydantic request/response schemas
```

---

## Getting Started

### Prerequisites

- Python 3.11+
- PostgreSQL
- Redis
- MongoDB

### Installation

```bash
git clone https://github.com/your-username/api-gateway.git
cd api-gateway
pip install -r requirements.txt
```

### Configuration

Create a `.env` file or export these environment variables:

```env
DATABASE_URL=postgresql://user:password@localhost/gateway
REDIS_URL=redis://localhost:6379
MONGO_URL=mongodb://localhost:27017
MONGO_DB=gateway
MONGO_COLLECTION=logs
API_KEY_HEADER=x-api-key
RATE_LIMIT_REQUESTS=100
RATE_LIMIT_WINDOW=60
CACHE_TTL=300
PROXY_TIMEOUT=10
```

`SERVICE_MAP` maps path prefixes to backend URLs. Configure in `config.py`:

```python
SERVICE_MAP = {
    "/users":   "http://localhost:8001",
    "/orders":  "http://localhost:8002",
    "/products":"http://localhost:8003",
}
```

### Run

```bash
uvicorn main:app --reload
```

---

## API Reference

### Public endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | Health check |
| `POST` | `/register` | Register a new user, returns API key |
| `POST` | `/register/admin` | Register an admin user |

### Authenticated endpoints

Pass your API key as `x-api-key` header on every request.

| Method | Path | Description |
|---|---|---|
| `GET` | `/me` | Current user info + rate limit status |
| `ANY` | `/services/{path}` | Proxy to backend service |

### Admin endpoints

Requires an admin API key (`is_admin=True`). Returns `403` for regular user keys.

| Method | Path | Description |
|---|---|---|
| `GET` | `/admin/stats/overview` | Request volume, error rate, avg latency |
| `GET` | `/admin/users` | List all users |

---

## Usage

### Register a user

```bash
curl -X POST http://localhost:8000/register \
  -H "Content-Type: application/json" \
  -d '{"name": "alice"}'

# → {"api_key": "abc123...", "user_id": 1, "message": "..."}
# Store the api_key — it is only shown once
```

### Make an authenticated request

```bash
curl http://localhost:8000/me \
  -H "x-api-key: abc123..."
```

### Proxy to a backend service

```bash
# Forwards to SERVICE_MAP["/users"] + /users/1
curl http://localhost:8000/services/users/1 \
  -H "x-api-key: abc123..."
```

### Register an admin

```bash
curl -X POST http://localhost:8000/register/admin \
  -H "Content-Type: application/json" \
  -d '{"name": "admin"}'
```

### Hit an admin endpoint

```bash
curl http://localhost:8000/admin/stats/overview \
  -H "x-api-key: <admin_key>"
```

---

## How It Works

### Middleware chain

Every non-public request passes through this chain in order:

1. **Auth** — hashes the incoming `x-api-key`, looks up the user in PostgreSQL, attaches `request.state.user`
2. **Rate limiter** — atomically increments a Redis counter scoped to `rate:{user_id}:{path}`, raises `429` if over limit
3. **Request ID** — generates a UUID and starts a latency timer
4. **Route handler** — proxy, cache check, or local handler
5. **Logger** — builds a `RequestLog` and writes to MongoDB in a background task (non-blocking)

### Caching

Only `GET` requests with `2xx` responses are cached. Cache keys include the full path and query string so `/users?page=1` and `/users?page=2` are separate entries.

### Rate limiting

Windows are per-user and per-endpoint independently. A user hitting `/services/users` and `/services/orders` has two separate counters, each with their own window.

### API key security

Raw API keys are never stored. On registration, the key is hashed with SHA-256 and only the hash is persisted. The raw key is returned once at registration and cannot be recovered.

---

## Notes

- On first run, `init_db()` creates the `users` table automatically
- If you add columns to `sql_models.py` on an existing database, run `ALTER TABLE` manually or delete the SQLite file in development
- MongoDB logs expire automatically after 30 days via a TTL index created at startup
- If Redis is unavailable, the gateway fails open on rate limiting (requests are allowed through) to avoid a Redis outage taking down the gateway