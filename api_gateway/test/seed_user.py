# scripts/seed_user.py
import hashlib, sys
sys.path.append(".")

from services.sql_clients import SessionLocal, init_db
from models.sql_models import User

RAW_KEY = "my-secret-test-key-123"

def seed():
    init_db()
    db = SessionLocal()
    hashed = hashlib.sha256(RAW_KEY.encode()).hexdigest()

    user = User(name="Test User", key_hash=hashed)
    db.add(user)
    db.commit()
    print(f"Created user. Use this header to authenticate:")
    print(f"  x-api-key: {RAW_KEY}")

seed()