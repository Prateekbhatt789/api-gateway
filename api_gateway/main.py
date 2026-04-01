# main.py
from fastapi import FastAPI, Request, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from services.sql_clients import init_db, get_db
from middleware.auth import authenticate_request
from router.register import router

app = FastAPI(title="API Gateway")
app.include_router(router)

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

    return await call_next(request)

# Test route — after auth passes, user is available
@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/me")
async def who_am_i(request: Request):
    user = request.state.user
    return {"id": user.id, "name": user.name}
