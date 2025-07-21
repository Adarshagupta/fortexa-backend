from typing import Optional, List
from pydantic import BaseModel, Field
from datetime import datetime

# Asset schemas
class AssetResponse(BaseModel):
    id: str
    symbol: str
    name: str
    type: str
    description: Optional[str] = None
    logo_url: Optional[str] = None
    current_price: float
    market_cap: Optional[float] = None
    volume_24h: Optional[float] = None
    change_24h: Optional[float] = None
    change_7d: Optional[float] = None
    change_30d: Optional[float] = None
    high_24h: Optional[float] = None
    low_24h: Optional[float] = None
    price_updated_at: datetime
    is_active: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class AssetSummaryResponse(BaseModel):
    id: str
    symbol: str
    name: str
    type: str
    current_price: float
    change_24h: Optional[float] = None
    logo_url: Optional[str] = None

# Market overview schemas
class MarketOverviewResponse(BaseModel):
    total_market_cap: float
    total_volume_24h: float
    market_cap_change_24h: float
    active_cryptocurrencies: int
    trending_assets: List[AssetSummaryResponse]
    top_gainers: List[AssetSummaryResponse]
    top_losers: List[AssetSummaryResponse]

# Price history schemas
class PriceHistoryPoint(BaseModel):
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float

class PriceHistoryResponse(BaseModel):
    asset_id: str
    symbol: str
    timeframe: str
    data: List[PriceHistoryPoint]

# Trading signal schemas
class TradingSignalResponse(BaseModel):
    id: str
    asset_id: str
    symbol: str
    type: str  # BUY, SELL, HOLD
    strength: float
    confidence: float
    current_price: float
    target_price: float
    stop_loss: Optional[float] = None
    timeframe: str
    reasoning: str
    ai_model: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class TradingSignalsResponse(BaseModel):
    signals: List[TradingSignalResponse]
    total_count: int

# Asset list schemas
class AssetsListResponse(BaseModel):
    assets: List[AssetResponse]
    total_count: int
    page: int
    page_size: int
    total_pages: int

# Search schemas
class AssetSearchRequest(BaseModel):
    query: str = Field(..., min_length=1)
    asset_type: Optional[str] = None
    limit: Optional[int] = Field(10, ge=1, le=100)

class AssetSearchResponse(BaseModel):
    assets: List[AssetSummaryResponse]
    total_count: int

# Watchlist schemas
class WatchlistResponse(BaseModel):
    id: str
    user_id: str
    name: str
    description: Optional[str] = None
    is_default: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class WatchlistItemResponse(BaseModel):
    id: str
    watchlist_id: str
    asset_id: str
    asset: AssetSummaryResponse
    added_at: datetime
    
    class Config:
        from_attributes = True

class WatchlistWithItemsResponse(BaseModel):
    watchlist: WatchlistResponse
    items: List[WatchlistItemResponse]
    total_items: int

class CreateWatchlistRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    is_default: bool = False

class UpdateWatchlistRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    is_default: Optional[bool] = None

class AddToWatchlistRequest(BaseModel):
    asset_id: str

class WatchlistsResponse(BaseModel):
    watchlists: List[WatchlistResponse]
    total_count: int

# Market data request schemas
class MarketDataRequest(BaseModel):
    symbols: List[str] = Field(..., min_items=1, max_items=50)
    timeframe: Optional[str] = Field("1h", pattern="^(1m|5m|15m|1h|4h|1d|7d|30d)$")

class BulkPriceUpdateRequest(BaseModel):
    updates: List[dict] = Field(..., min_items=1, max_items=100) 