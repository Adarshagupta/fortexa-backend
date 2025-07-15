from typing import Optional, List
from pydantic import BaseModel, Field, field_validator
from datetime import datetime
from enum import Enum

class ApiProvider(str, Enum):
    BINANCE = "BINANCE"
    COINBASE = "COINBASE"
    KRAKEN = "KRAKEN"
    BITFINEX = "BITFINEX"
    KUCOIN = "KUCOIN"

# Base schemas
class ApiKeyBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    provider: ApiProvider = ApiProvider.BINANCE
    testnet: bool = False
    permissions: List[str] = []

class AddApiKeyRequest(ApiKeyBase):
    api_key: str = Field(..., min_length=10, max_length=100)
    secret_key: str = Field(..., min_length=10, max_length=100)
    
    @field_validator('api_key')
    @classmethod
    def validate_api_key(cls, v):
        if len(v.strip()) < 10:
            raise ValueError('API key must be at least 10 characters long')
        return v.strip()
    
    @field_validator('secret_key')
    @classmethod
    def validate_secret_key(cls, v):
        if len(v.strip()) < 10:
            raise ValueError('Secret key must be at least 10 characters long')
        return v.strip()

class UpdateApiKeyRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    is_active: Optional[bool] = None
    permissions: Optional[List[str]] = None

class ApiKeyResponse(BaseModel):
    id: str
    name: str
    provider: ApiProvider
    testnet: bool
    is_active: bool
    last_used: Optional[datetime] = None
    permissions: List[str]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class ApiKeysListResponse(BaseModel):
    api_keys: List[ApiKeyResponse]
    total_count: int

class AddApiKeyResponse(BaseModel):
    api_key: ApiKeyResponse
    message: str = "API key added successfully"

class UpdateApiKeyResponse(BaseModel):
    api_key: ApiKeyResponse
    message: str = "API key updated successfully"

class DeleteApiKeyResponse(BaseModel):
    message: str = "API key deleted successfully"
    success: bool = True



class SyncPortfolioRequest(BaseModel):
    api_key_id: Optional[str] = None  # If None, sync all active keys
    force_sync: bool = False

class SyncPortfolioResponse(BaseModel):
    success: bool
    message: str
    synced_holdings: int = 0
    updated_assets: int = 0
    sync_duration: float = 0.0 