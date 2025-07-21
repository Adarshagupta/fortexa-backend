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
    ZERODHA = "ZERODHA"
    ANGEL_ONE = "ANGEL_ONE"
    GROWW = "GROWW"

# Base schemas
class ApiKeyBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    provider: ApiProvider = ApiProvider.BINANCE
    testnet: bool = False
    permissions: List[str] = []

class AddApiKeyRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="A descriptive name for the API key")
    provider: ApiProvider = Field(..., description="The trading platform provider")
    api_key: str = Field(..., min_length=1, description="API key from the provider")
    secret_key: Optional[str] = Field(None, description="Secret key (required for most providers)")
    testnet: bool = Field(False, description="Whether to use testnet/sandbox mode")
    permissions: List[str] = Field(default_factory=list, description="List of permissions for the API key")
    
    # Additional fields for Indian brokers
    client_code: Optional[str] = Field(None, description="Client code (required for Angel One)")
    password: Optional[str] = Field(None, description="Login password (required for Angel One)")
    totp_secret: Optional[str] = Field(None, description="TOTP secret for 2FA (Angel One)")
    access_token: Optional[str] = Field(None, description="Access token (for Zerodha/Groww)")
    
    @field_validator('permissions')
    @classmethod
    def validate_permissions(cls, v):
        if not isinstance(v, list):
            return []
        return [perm.strip() for perm in v if perm.strip()]

class UpdateApiKeyRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    is_active: Optional[bool] = None
    testnet: Optional[bool] = None
    permissions: Optional[List[str]] = None
    
    # Additional updatable fields for Indian brokers
    client_code: Optional[str] = None
    password: Optional[str] = None
    totp_secret: Optional[str] = None
    access_token: Optional[str] = None

class ApiKeyResponse(BaseModel):
    id: str
    name: str
    provider: ApiProvider
    testnet: bool
    is_active: bool
    last_used: Optional[datetime]
    permissions: List[str]
    created_at: datetime
    updated_at: datetime
    
    # Additional fields for display (but not sensitive data)
    has_client_code: Optional[bool] = Field(None, description="Whether client code is configured (Angel One)")
    has_access_token: Optional[bool] = Field(None, description="Whether access token is available (Zerodha/Groww)")
    
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
    success: bool
    message: str

class SyncPortfolioRequest(BaseModel):
    api_key_id: Optional[str] = Field(None, description="Specific API key ID to use for sync")
    force_sync: bool = Field(False, description="Force sync even if recently synced")
    provider_specific_data: Optional[dict] = Field(None, description="Provider-specific data for sync")

class SyncPortfolioResponse(BaseModel):
    success: bool
    message: str
    synced_holdings: int
    updated_assets: int
    sync_duration: float
    provider: ApiProvider
    method: Optional[str] = Field(None, description="Sync method used (api, csv_import, etc.)")

# Provider-specific request schemas
class ZerodhaLoginRequest(BaseModel):
    api_key: str
    request_token: str
    
class AngelOneLoginRequest(BaseModel):
    api_key: str
    client_code: str
    password: str
    totp: str
    
class GrowwImportRequest(BaseModel):
    csv_data: str = Field(..., description="CSV data exported from Groww app")
    portfolio_name: Optional[str] = Field("Groww Portfolio", description="Name for the imported portfolio")

# Provider-specific response schemas
class ZerodhaLoginResponse(BaseModel):
    access_token: str
    refresh_token: Optional[str]
    expires_at: datetime
    
class AngelOneLoginResponse(BaseModel):
    jwt_token: str
    refresh_token: Optional[str]
    expires_at: datetime
    
class GrowwImportResponse(BaseModel):
    success: bool
    message: str
    imported_holdings: int
    created_assets: int 