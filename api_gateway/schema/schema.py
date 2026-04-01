from pydantic import BaseModel

class RegisterRequest(BaseModel):
    name: str

class RegisterResponse(BaseModel):
    message: str
    api_key: str          # Raw key — shown ONCE, never stored
    user_id: int