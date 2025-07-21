from fastapi import APIRouter, Depends, HTTPException
from prisma import Prisma
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from app.core.database import get_db
from app.api.v1.endpoints.auth import get_verified_user_id
from app.core.logger import logger
from app.schemas.auth import UserResponse

router = APIRouter()

class UpdateProfileRequest(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    display_name: Optional[str] = None
    phone_number: Optional[str] = None
    profile_picture: Optional[str] = None

@router.get("/profile", response_model=UserResponse)
async def get_user_profile(
    current_user_id: str = Depends(get_verified_user_id),
    db: Prisma = Depends(get_db)
):
    """Get user profile"""
    try:
        user = await db.user.find_unique(
            where={"id": current_user_id},
            include={"settings": True}
        )
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        return UserResponse(
            id=user.id,
            email=user.email,
            first_name=user.firstName,
            last_name=user.lastName,
            display_name=user.displayName,
            phone_number=user.phoneNumber,
            profile_picture=user.profilePicture,
            is_active=user.isActive,
            is_email_verified=user.isEmailVerified,
            is_mfa_enabled=user.isMfaEnabled,
            created_at=user.createdAt,
            updated_at=user.updatedAt,
        )
    except Exception as e:
        logger.error(f"Get user profile failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to get user profile")

@router.put("/profile", response_model=UserResponse)
async def update_user_profile(
    request: UpdateProfileRequest,
    current_user_id: str = Depends(get_verified_user_id),
    db: Prisma = Depends(get_db)
):
    """Update user profile"""
    try:
        # Build update data
        update_data = {}
        
        if request.first_name is not None:
            update_data["firstName"] = request.first_name
        
        if request.last_name is not None:
            update_data["lastName"] = request.last_name
        
        if request.display_name is not None:
            update_data["displayName"] = request.display_name
        elif request.first_name is not None or request.last_name is not None:
            # Auto-generate display name if first/last name changed
            user = await db.user.find_unique(where={"id": current_user_id})
            if user:
                first_name = request.first_name if request.first_name is not None else user.firstName
                last_name = request.last_name if request.last_name is not None else user.lastName
                update_data["displayName"] = f"{first_name} {last_name}"
        
        if request.phone_number is not None:
            update_data["phoneNumber"] = request.phone_number
        
        if request.profile_picture is not None:
            update_data["profilePicture"] = request.profile_picture
        
        # Add updated timestamp
        update_data["updatedAt"] = datetime.now()
        
        # Update user
        updated_user = await db.user.update(
            where={"id": current_user_id},
            data=update_data
        )
        
        logger.info(f"User profile updated successfully for user: {updated_user.email}")
        
        return UserResponse(
            id=updated_user.id,
            email=updated_user.email,
            first_name=updated_user.firstName,
            last_name=updated_user.lastName,
            display_name=updated_user.displayName,
            phone_number=updated_user.phoneNumber,
            profile_picture=updated_user.profilePicture,
            is_active=updated_user.isActive,
            is_email_verified=updated_user.isEmailVerified,
            is_mfa_enabled=updated_user.isMfaEnabled,
            created_at=updated_user.createdAt,
            updated_at=updated_user.updatedAt,
        )
        
    except Exception as e:
        logger.error(f"Update user profile failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to update user profile")

@router.delete("/account")
async def delete_user_account(
    current_user_id: str = Depends(get_verified_user_id),
    db: Prisma = Depends(get_db)
):
    """Delete user account"""
    # Implementation placeholder
    return {"message": "Delete user account endpoint - implementation needed"} 