# routers/register.py
import secrets
import hashlib
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from services.sql_clients import get_db
from models.sql_models import User
from schema.schema import RegisterRequest,RegisterResponse
router = APIRouter()

def generate_api_key() -> str:
    """
    secrets.token_hex is cryptographically secure.
    Produces a 64-char hex string (32 bytes of entropy).
    Never use random.random() or uuid4() for secrets.
    """
    return secrets.token_hex(32)

def hash_key(raw_key: str) -> str:
    return hashlib.sha256(raw_key.encode()).hexdigest()

@router.post("/register", response_model=RegisterResponse, status_code=201)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    if not payload.name.strip():
        raise HTTPException(status_code=400, detail="Name cannot be empty.")

    # Check for duplicate name (optional but good hygiene)
    existing = db.query(User).filter(User.name == payload.name).first()
    if existing:
        raise HTTPException(status_code=409, detail="Name already registered.")

    raw_key = generate_api_key()
    hashed  = hash_key(raw_key)

    user = User(name=payload.name, key_hash=hashed)
    db.add(user)
    db.commit()
    db.refresh(user)

    return RegisterResponse(
        message="Registration successful. Store your API key — it won't be shown again.",
        api_key=raw_key,       # ← raw key returned here, one time only
        user_id=user.id
    )



@router.post("/register/admin", response_model=RegisterResponse, status_code=201)
def register_admin(payload: RegisterRequest, db: Session = Depends(get_db)):
    """
    Creates an admin user. In production, protect this with an
    internal secret header or remove it entirely after first use.
    """
    if not payload.name.strip():
        raise HTTPException(status_code=400, detail="Name cannot be empty.")

    existing = db.query(User).filter(User.name == payload.name).first()
    if existing:
        raise HTTPException(status_code=409, detail="Name already registered.")

    raw_key = generate_api_key()
    hashed  = hash_key(raw_key)

    user = User(name=payload.name, key_hash=hashed, is_admin=True)  # ← is_admin=True
    db.add(user)
    db.commit()
    db.refresh(user)

    return RegisterResponse(
        message="Admin registered. Store your API key — it won't be shown again.",
        api_key=raw_key,
        user_id=user.id
    )