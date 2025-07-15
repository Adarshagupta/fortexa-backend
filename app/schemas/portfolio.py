from typing import Optional, List
from pydantic import BaseModel, Field
from datetime import datetime

# Portfolio creation schemas
class CreatePortfolioRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    is_default: bool = False

# Portfolio schemas
class PortfolioResponse(BaseModel):
    id: str
    user_id: str
    name: str
    total_value: float
    total_cost: float
    total_gain_loss: float
    total_gain_loss_percent: float
    last_updated: datetime
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class PortfolioSummaryResponse(BaseModel):
    id: str
    name: str
    total_value: float
    total_cost: float
    total_gain_loss: float
    total_gain_loss_percent: float
    holdings_count: int
    last_updated: datetime

# Asset schema for holdings response
class AssetInfo(BaseModel):
    id: str
    symbol: str
    name: str
    type: str
    current_price: float
    price_change_percentage_24h: float = 0.0
    
    class Config:
        from_attributes = True

# Portfolio holding schemas
class HoldingResponse(BaseModel):
    id: str
    portfolio_id: str
    asset_id: str
    symbol: str
    quantity: float
    average_price: float
    current_price: float
    total_value: float
    total_cost: float
    gain_loss: float
    gain_loss_percent: float
    allocation: float
    created_at: datetime
    updated_at: datetime
    asset: AssetInfo
    
    class Config:
        from_attributes = True

class AddHoldingRequest(BaseModel):
    asset_id: str
    quantity: float = Field(..., gt=0)
    average_price: float = Field(..., gt=0)

class UpdateHoldingRequest(BaseModel):
    quantity: Optional[float] = Field(None, gt=0)
    average_price: Optional[float] = Field(None, gt=0)

class AddHoldingResponse(BaseModel):
    holding: HoldingResponse
    message: str

class UpdateHoldingResponse(BaseModel):
    holding: HoldingResponse
    message: str

class RemoveHoldingResponse(BaseModel):
    message: str
    success: bool

# Portfolio performance schemas
class PerformanceDataPoint(BaseModel):
    date: datetime
    total_value: float
    total_cost: float
    gain_loss: float
    gain_loss_percent: float

class PortfolioPerformanceResponse(BaseModel):
    portfolio_id: str
    timeframe: str
    performance_data: List[PerformanceDataPoint]
    summary: dict

class PortfolioAnalyticsResponse(BaseModel):
    portfolio_id: str
    total_value: float
    total_cost: float
    total_gain_loss: float
    total_gain_loss_percent: float
    best_performer: Optional[dict] = None
    worst_performer: Optional[dict] = None
    sector_allocation: List[dict] = []
    asset_allocation: List[dict] = []
    risk_metrics: dict = {}
    
# Portfolio update schemas
class UpdatePortfolioRequest(BaseModel):
    name: Optional[str] = None

class UpdatePortfolioResponse(BaseModel):
    portfolio: PortfolioResponse
    message: str

# Holdings list response
class HoldingsListResponse(BaseModel):
    holdings: List[HoldingResponse]
    total_count: int
    portfolio_summary: PortfolioSummaryResponse 