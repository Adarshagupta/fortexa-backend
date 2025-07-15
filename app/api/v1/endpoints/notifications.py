from fastapi import APIRouter, Depends
from prisma import Prisma
from app.core.database import get_db
from app.api.v1.endpoints.auth import get_verified_user_id

router = APIRouter()

@router.get("/")
async def get_notifications(
    current_user_id: str = Depends(get_verified_user_id),
    db: Prisma = Depends(get_db)
):
    """Get user notifications"""
    return {"message": "Notifications endpoints - implementation needed"}

@router.put("/{notification_id}/read")
async def mark_notification_read(
    notification_id: str,
    current_user_id: str = Depends(get_verified_user_id),
    db: Prisma = Depends(get_db)
):
    """Mark notification as read"""
    return {"message": "Mark notification read endpoint - implementation needed"} 