# main.py
import time,uuid
from fastapi import FastAPI, Request, Depends
from fastapi.responses import JSONResponse
from fastapi.background import BackgroundTasks
from sqlalchemy.orm import Session
from services.sql_clients import init_db, get_db
from services.redis_clients import get_redis
from services.mongo_clients import init_mongo, write_log
from models.log_schema import RequestLog
from middleware.auth import authenticate_request
from middleware.rate_limiter import check_rate_limit
from router.register import router as register_router
from router.proxy import router as proxy_router

app = FastAPI(title="API Gateway")
app.include_router(register_router)
app.include_router(proxy_router)

@app.on_event("startup")
async def on_startup():
    init_db()  # Creates tables if they don't exist
    await init_mongo()

@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    """
    Runs before every request.
    Skips auth for health check so infra monitors still work.
    """
    PUBLIC_PATHS = {"/health","/register","/docs","/openapi.json"}
    if request.url.path in PUBLIC_PATHS:
        return await call_next(request)

    # ── 1. Auth ─────────────────────────────────────────────
    # Grab a DB session manually (middleware can't use Depends)
    db: Session = next(get_db())
    try:
        await authenticate_request(request, db)
    except Exception as exc:
        # Re-raise HTTPExceptions as proper JSON responses
        from fastapi import HTTPException
        if isinstance(exc, HTTPException):
            return JSONResponse(
                status_code=exc.status_code,
                content={"error": exc.detail}
            )
        return JSONResponse(status_code=500, content={"error": "Internal error"})
    finally:
        db.close()
    
    # ── 2. Rate limit ─────────────────────────────────────────────
    try:
        redis = get_redis()
        check_rate_limit(request, redis)
    except Exception as exc:
        from fastapi import HTTPException
        if isinstance(exc, HTTPException):
            return JSONResponse(status_code=exc.status_code,
                                content={"error": exc.detail})
        # Redis is down → fail open (let request through)
        # Log this in production
        pass

    # ── 3. Start request timer + assign request ID ────────────
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    start_time = time.monotonic()

    # ── 4. Forward to route handler ───────────────────────────
    response = await call_next(request)

    # ── 5. Calculate latency ──────────────────────────────────
    latency_ms = (time.monotonic() - start_time) * 1000
    
    # ── 6. Build and write log (background — non-blocking) ────
    user = request.state.user
    log  = RequestLog(
        request_id       = request_id,
        user_id          = user.id,
        user_name        = user.name,
        method           = request.method,
        path             = request.url.path,
        status_code      = response.status_code,
        latency_ms       = round(latency_ms, 2),
        upstream_service = getattr(request.state, "upstream_service", None),
        cache_hit        = getattr(request.state, "cache_hit", False),
    )
    # BackgroundTasks runs AFTER response is sent to client
    background = BackgroundTasks()
    background.add_task(write_log, log.to_dict())
    response.background = background

    return response


# Test route — after auth passes, user is available
@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/me")
async def who_am_i(request: Request):
    user = request.state.user
    return {"id": user.id, 
            "name": user.name,
            "request_used":request.state.rate_limit_count,
            "request_remaining": request.state.rate_limit_remaining}
