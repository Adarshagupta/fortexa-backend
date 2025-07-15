from fastapi import APIRouter, Depends, HTTPException
from prisma import Prisma
from app.core.database import get_db
from app.api.v1.endpoints.auth import get_verified_user_id
from app.schemas.alerts import AlertsListResponse, AlertResponse, CreateAlertRequest, UpdateAlertRequest
from app.core.logger import logger
from datetime import datetime

router = APIRouter()

@router.get("/", response_model=AlertsListResponse)
async def get_alerts(
    current_user_id: str = Depends(get_verified_user_id),
    db: Prisma = Depends(get_db)
):
    """Get user alerts"""
    try:
        alerts = await db.alert.find_many(
            where={"userId": current_user_id},
            order={"createdAt": "desc"},
            include={"asset": True}
        )
        
        alert_responses = []
        active_count = 0
        triggered_count = 0
        
        for alert in alerts:
            alert_response = AlertResponse(
                id=alert.id,
                user_id=alert.userId,
                asset_id=alert.assetId,
                type=alert.type.value,
                condition=alert.condition.value,
                target_price=alert.targetPrice,
                current_price=alert.currentPrice,
                is_active=alert.isActive,
                is_triggered=alert.isTriggered,
                triggered_at=alert.triggeredAt,
                message=alert.message,
                expires_at=alert.expiresAt,
                created_at=alert.createdAt,
                updated_at=alert.updatedAt,
            )
            alert_responses.append(alert_response)
            
            if alert.isActive:
                active_count += 1
            if alert.isTriggered:
                triggered_count += 1
        
        return AlertsListResponse(
            alerts=alert_responses,
            total_count=len(alert_responses),
            active_count=active_count,
            triggered_count=triggered_count
        )
    except Exception as e:
        logger.error(f"Get alerts failed: {e}")
        # Return empty response if no alerts found
        return AlertsListResponse(
            alerts=[],
            total_count=0,
            active_count=0,
            triggered_count=0
        )

@router.post("/", response_model=AlertResponse)
async def create_alert(
    request: CreateAlertRequest,
    current_user_id: str = Depends(get_verified_user_id),
    db: Prisma = Depends(get_db)
):
    """Create new alert"""
    try:
        # Check if asset exists
        asset = await db.asset.find_unique(
            where={"id": request.asset_id}
        )
        
        if not asset:
            raise HTTPException(status_code=404, detail="Asset not found")
        
        # Create alert
        alert = await db.alert.create(
            data={
                "userId": current_user_id,
                "assetId": request.asset_id,
                "type": request.type,
                "condition": request.condition,
                "targetPrice": request.target_price,
                "currentPrice": asset.currentPrice,
                "message": request.message,
                "expiresAt": request.expires_at,
                "isActive": True,
                "isTriggered": False,
            }
        )
        
        return AlertResponse(
            id=alert.id,
            user_id=alert.userId,
            asset_id=alert.assetId,
            type=alert.type.value,
            condition=alert.condition.value,
            target_price=alert.targetPrice,
            current_price=alert.currentPrice,
            is_active=alert.isActive,
            is_triggered=alert.isTriggered,
            triggered_at=alert.triggeredAt,
            message=alert.message,
            expires_at=alert.expiresAt,
            created_at=alert.createdAt,
            updated_at=alert.updatedAt,
        )
        
    except Exception as e:
        logger.error(f"Create alert failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to create alert")

@router.put("/{alert_id}", response_model=AlertResponse)
async def update_alert(
    alert_id: str,
    request: UpdateAlertRequest,
    current_user_id: str = Depends(get_verified_user_id),
    db: Prisma = Depends(get_db)
):
    """Update an alert"""
    try:
        # Check if alert exists and belongs to user
        alert = await db.alert.find_first(
            where={
                "id": alert_id,
                "userId": current_user_id
            }
        )
        
        if not alert:
            raise HTTPException(status_code=404, detail="Alert not found")
        
        # Build update data
        update_data = {}
        if request.target_price is not None:
            update_data["targetPrice"] = request.target_price
        if request.message is not None:
            update_data["message"] = request.message
        if request.is_active is not None:
            update_data["isActive"] = request.is_active
        if request.expires_at is not None:
            update_data["expiresAt"] = request.expires_at
        
        # Update alert
        updated_alert = await db.alert.update(
            where={"id": alert_id},
            data=update_data
        )
        
        return AlertResponse(
            id=updated_alert.id,
            user_id=updated_alert.userId,
            asset_id=updated_alert.assetId,
            type=updated_alert.type.value,
            condition=updated_alert.condition.value,
            target_price=updated_alert.targetPrice,
            current_price=updated_alert.currentPrice,
            is_active=updated_alert.isActive,
            is_triggered=updated_alert.isTriggered,
            triggered_at=updated_alert.triggeredAt,
            message=updated_alert.message,
            expires_at=updated_alert.expiresAt,
            created_at=updated_alert.createdAt,
            updated_at=updated_alert.updatedAt,
        )
        
    except Exception as e:
        logger.error(f"Update alert failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to update alert")

@router.delete("/{alert_id}")
async def delete_alert(
    alert_id: str,
    current_user_id: str = Depends(get_verified_user_id),
    db: Prisma = Depends(get_db)
):
    """Delete an alert"""
    try:
        # Check if alert exists and belongs to user
        alert = await db.alert.find_first(
            where={
                "id": alert_id,
                "userId": current_user_id
            }
        )
        
        if not alert:
            raise HTTPException(status_code=404, detail="Alert not found")
        
        # Delete alert
        await db.alert.delete(where={"id": alert_id})
        
        return {"message": "Alert deleted successfully", "success": True}
        
    except Exception as e:
        logger.error(f"Delete alert failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete alert") 
    return {"message": "Create alert endpoint - implementation needed"} 