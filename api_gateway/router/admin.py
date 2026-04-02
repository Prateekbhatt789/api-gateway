# router/admin.py
from fastapi import APIRouter, Depends
from middleware.admin_auth import require_admin

router = APIRouter(prefix="/admin", tags=["admin"])

@router.get("/stats/overview")
async def overview(admin=Depends(require_admin)):
    return {
        "message": f"Welcome admin '{admin.name}'",
        "stats": "working"
    }

@router.get("/users")
async def list_users(admin=Depends(require_admin)):
    return {"users": "coming soon"}