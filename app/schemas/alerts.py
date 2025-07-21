from typing import Optional, List
from pydantic import BaseModel, Field
from datetime import datetime

# Alert schemas
class AlertResponse(BaseModel):
    id: str
    user_id: str
    asset_id: str
    type: str  # AlertType enum value
    condition: str  # AlertCondition enum value
    target_price: float
    current_price: float
    is_active: bool
    is_triggered: bool
    triggered_at: Optional[datetime] = None
    message: Optional[str] = None
    expires_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class AlertsListResponse(BaseModel):
    alerts: List[AlertResponse]
    total_count: int
    active_count: int
    triggered_count: int

class CreateAlertRequest(BaseModel):
    asset_id: str = Field(..., min_length=1)
    type: str = Field(..., min_length=1)  # AlertType
    condition: str = Field(..., min_length=1)  # AlertCondition  
    target_price: float = Field(..., gt=0)
    message: Optional[str] = Field(None, max_length=500)
    expires_at: Optional[datetime] = None

class UpdateAlertRequest(BaseModel):
    target_price: Optional[float] = Field(None, gt=0)
    message: Optional[str] = Field(None, max_length=500)
    is_active: Optional[bool] = None
    expires_at: Optional[datetime] = None

class AlertTriggerResponse(BaseModel):
    alert_id: str
    triggered_at: datetime
    current_price: float
    target_price: float
    message: str 
 
 