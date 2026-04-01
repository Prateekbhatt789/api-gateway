# services/sql_client.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator
from models.sql_models import Base
from config import DATABASE_URL

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}  # SQLite-specific, safe for FastAPI
)

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)

def init_db():
    """Create all tables on startup."""
    Base.metadata.create_all(bind=engine)

def get_db() -> Generator[Session,None,None]:
    """
    FastAPI dependency — yields a DB session per request,
    guaranteed to close even if an exception occurs.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()