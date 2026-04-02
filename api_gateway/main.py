# main.py
from fastapi import FastAPI, Request, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from services.sql_clients import init_db, get_db
from services.redis_clients import get_redis
from middleware.auth import authenticate_request
from middleware.rate_limiter import check_rate_limit
from router.register import router as register_router
from router.proxy import router as proxy_router

app = FastAPI(title="API Gateway")
app.include_router(register_router)
app.include_router(proxy_router)

@app.on_event("startup")
def on_startup():
    init_db()  # Creates tables if they don't exist

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

    # ── 3. Forward to route handler ──────────────────────────
    response = await call_next(request)
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
