from fastapi import Request, HTTPException, Depends
from sqlalchemy.orm import Session
from services.sql_clients import get_db
from middleware.auth import get_user_by_key
from config import API_KEY_HEADER

async def require_admin(request: Request, db: Session = Depends(get_db)):
    """
    Dependency for admin-only routes.
    Reuses the same key lookup — but also checks is_admin flag.
    """
    raw_key = request.headers.get(API_KEY_HEADER)

    if not raw_key:
        raise HTTPException(
            status_code=401,
            detail="Missing API key."
        )

    user = get_user_by_key(raw_key, db)

    if not user:
        raise HTTPException(
            status_code=401,
            detail="Invalid or revoked API key."
        )

    if not user.is_admin:
        raise HTTPException(
            status_code=403,
            detail="Admin access required."
        )

    request.state.user = user
    return user