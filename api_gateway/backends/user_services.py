# backends/user_service.py
from fastapi import FastAPI,HTTPException
app = FastAPI(title="User Service")

USERS = {
    1: {"id": 1, "name": "alice", "email": "alice@example.com"},
    2: {"id": 2, "name": "bob",   "email": "bob@example.com"},
}

@app.get("/users")
def list_users():
    return list(USERS.values())

@app.get("/users/{user_id}")
def get_user(user_id: int):
    user = USERS.get(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user