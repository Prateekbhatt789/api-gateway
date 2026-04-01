# middleware/auth.py
import hashlib
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from models.sql_models import User
from config import API_KEY_HEADER

def hash_key(raw_key: str) -> str:
    """Deterministic SHA-256 hash. Same input always → same output."""
    return hashlib.sha256(raw_key.encode()).hexdigest()

def get_user_by_key(raw_key: str, db: Session):
    """
    Hash the incoming key, look it up in DB.
    Returns User or None.
    """
    hashed = hash_key(raw_key)
    return db.query(User).filter(
        User.key_hash == hashed,
        User.is_active == True
    ).first()

async def authenticate_request(request: Request, db: Session) -> User:
    """
    Core auth function — call this from middleware or as a dependency.
    Raises 401 if key is missing, invalid, or belongs to inactive user.
    """
    raw_key = request.headers.get(API_KEY_HEADER)

    if not raw_key:
        raise HTTPException(
            status_code=401,
            detail="Missing API key. Pass it as 'x-api-key' header."
        )

    user = get_user_by_key(raw_key, db)

    if not user:
        raise HTTPException(
            status_code=401,
            detail="Invalid or revoked API key."
        )

    # Attach user to request state so downstream handlers can access it
    # without re-querying the DB
    request.state.user = user
    return user