from fastapi import APIRouter, Depends, HTTPException, Query
from prisma import Prisma
from typing import List, Optional
from datetime import datetime
import asyncio
from cryptography.fernet import Fernet
import os

from app.core.database import get_db
from app.schemas.api_keys import *
from app.api.v1.endpoints.auth import get_verified_user_id
from app.core.logger import logger
from app.core.exceptions import *
from app.services.binance_service import BinanceAPIService

router = APIRouter()

# Encryption key for API keys (should be stored securely in production)
ENCRYPTION_KEY = os.getenv('API_KEY_ENCRYPTION_KEY', Fernet.generate_key())
cipher_suite = Fernet(ENCRYPTION_KEY)

def encrypt_api_key(api_key: str) -> str:
    """Encrypt API key for storage"""
    return cipher_suite.encrypt(api_key.encode()).decode()

def decrypt_api_key(encrypted_key: str) -> str:
    """Decrypt API key for use"""
    return cipher_suite.decrypt(encrypted_key.encode()).decode()

@router.post("/", response_model=AddApiKeyResponse)
async def add_api_key(
    request: AddApiKeyRequest,
    current_user_id: str = Depends(get_verified_user_id),
    db: Prisma = Depends(get_db)
):
    """Add a new API key"""
    try:
        # Check if API key with same name already exists for this user
        existing_key = await db.apikey.find_first(
            where={
                "userId": current_user_id,
                "name": request.name,
                "provider": request.provider.value
            }
        )
        
        if existing_key:
            raise HTTPException(
                status_code=400,
                detail=f"API key with name '{request.name}' already exists for {request.provider.value}"
            )
        
        # Encrypt the API keys
        encrypted_api_key = encrypt_api_key(request.api_key)
        encrypted_secret_key = encrypt_api_key(request.secret_key)
        
        # Create new API key
        api_key = await db.apikey.create(
            data={
                "userId": current_user_id,
                "name": request.name,
                "provider": request.provider.value,
                "apiKey": encrypted_api_key,
                "secretKey": encrypted_secret_key,
                "testnet": request.testnet,
                "permissions": request.permissions,
                "isActive": True,
            }
        )
        
        logger.info(f"API key added for user {current_user_id}: {request.name}")
        
        return AddApiKeyResponse(
            api_key=ApiKeyResponse(
                id=api_key.id,
                name=api_key.name,
                provider=ApiProvider(api_key.provider),
                testnet=api_key.testnet,
                is_active=api_key.isActive,
                last_used=api_key.lastUsed,
                permissions=api_key.permissions,
                created_at=api_key.createdAt,
                updated_at=api_key.updatedAt
            )
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Add API key failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to add API key")

@router.get("/", response_model=ApiKeysListResponse)
async def get_api_keys(
    current_user_id: str = Depends(get_verified_user_id),
    db: Prisma = Depends(get_db)
):
    """Get all API keys for the current user"""
    try:
        api_keys = await db.apikey.find_many(
            where={"userId": current_user_id}
        )
        
        api_key_responses = []
        for key in api_keys:
            api_key_responses.append(ApiKeyResponse(
                id=key.id,
                name=key.name,
                provider=ApiProvider(key.provider),
                testnet=key.testnet,
                is_active=key.isActive,
                last_used=key.lastUsed,
                permissions=key.permissions,
                created_at=key.createdAt,
                updated_at=key.updatedAt
            ))
        
        return ApiKeysListResponse(
            api_keys=api_key_responses,
            total_count=len(api_key_responses)
        )
        
    except Exception as e:
        logger.error(f"Get API keys failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch API keys")

@router.put("/{api_key_id}", response_model=UpdateApiKeyResponse)
async def update_api_key(
    api_key_id: str,
    request: UpdateApiKeyRequest,
    current_user_id: str = Depends(get_verified_user_id),
    db: Prisma = Depends(get_db)
):
    """Update an existing API key"""
    try:
        # Check if API key exists and belongs to user
        existing_key = await db.apikey.find_first(
            where={
                "id": api_key_id,
                "userId": current_user_id
            }
        )
        
        if not existing_key:
            raise HTTPException(status_code=404, detail="API key not found")
        
        # Prepare update data
        update_data = {}
        if request.name is not None:
            update_data["name"] = request.name
        if request.is_active is not None:
            update_data["isActive"] = request.is_active
        if request.permissions is not None:
            update_data["permissions"] = request.permissions
        
        # Update API key
        updated_key = await db.apikey.update(
            where={"id": api_key_id},
            data=update_data
        )
        
        logger.info(f"API key updated for user {current_user_id}: {api_key_id}")
        
        return UpdateApiKeyResponse(
            api_key=ApiKeyResponse(
                id=updated_key.id,
                name=updated_key.name,
                provider=ApiProvider(updated_key.provider),
                testnet=updated_key.testnet,
                is_active=updated_key.isActive,
                last_used=updated_key.lastUsed,
                permissions=updated_key.permissions,
                created_at=updated_key.createdAt,
                updated_at=updated_key.updatedAt
            )
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Update API key failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to update API key")

@router.delete("/{api_key_id}", response_model=DeleteApiKeyResponse)
async def delete_api_key(
    api_key_id: str,
    current_user_id: str = Depends(get_verified_user_id),
    db: Prisma = Depends(get_db)
):
    """Delete an API key"""
    try:
        # Check if API key exists and belongs to user
        existing_key = await db.apikey.find_first(
            where={
                "id": api_key_id,
                "userId": current_user_id
            }
        )
        
        if not existing_key:
            raise HTTPException(status_code=404, detail="API key not found")
        
        # Delete API key
        await db.apikey.delete(where={"id": api_key_id})
        
        logger.info(f"API key deleted for user {current_user_id}: {api_key_id}")
        
        return DeleteApiKeyResponse()
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete API key failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete API key")



@router.post("/sync-portfolio", response_model=SyncPortfolioResponse)
async def sync_portfolio(
    request: SyncPortfolioRequest,
    current_user_id: str = Depends(get_verified_user_id),
    db: Prisma = Depends(get_db)
):
    """Sync portfolio data from connected exchanges"""
    try:
        start_time = datetime.now()
        synced_holdings = 0
        updated_assets = 0
        
        # Get API keys to sync
        if request.api_key_id:
            api_keys = await db.apikey.find_many(
                where={
                    "id": request.api_key_id,
                    "userId": current_user_id,
                    "isActive": True
                }
            )
        else:
            api_keys = await db.apikey.find_many(
                where={
                    "userId": current_user_id,
                    "isActive": True
                }
            )
        
        if not api_keys:
            raise HTTPException(status_code=404, detail="No active API keys found")
        
        # Get or create user's portfolio
        portfolio = await db.portfolio.find_unique(
            where={"userId": current_user_id}
        )
        
        if not portfolio:
            portfolio = await db.portfolio.create(
                data={
                    "userId": current_user_id,
                    "name": "My Portfolio",
                    "totalValue": 0.0,
                    "totalCost": 0.0,
                    "totalGainLoss": 0.0,
                    "totalGainLossPercent": 0.0,
                    "lastUpdated": datetime.now()
                }
            )
        
        # Sync data from each API key
        for api_key in api_keys:
            try:
                if api_key.provider == "BINANCE":
                    # Decrypt API keys
                    decrypted_api_key = decrypt_api_key(api_key.apiKey)
                    decrypted_secret_key = decrypt_api_key(api_key.secretKey)
                    
                    # Sync Binance portfolio
                    binance_service = BinanceAPIService()
                    sync_result = await binance_service.sync_portfolio(
                        api_key=decrypted_api_key,
                        secret_key=decrypted_secret_key,
                        testnet=api_key.testnet,
                        portfolio_id=portfolio.id,
                        db=db
                    )
                    
                    synced_holdings += sync_result.get('synced_holdings', 0)
                    updated_assets += sync_result.get('updated_assets', 0)
                    
                    # Update last used timestamp
                    await db.apikey.update(
                        where={"id": api_key.id},
                        data={"lastUsed": datetime.now()}
                    )
                    
            except Exception as e:
                logger.error(f"Failed to sync portfolio for API key {api_key.id}: {str(e)}")
                logger.error(f"Exception type: {type(e).__name__}")
                import traceback
                logger.error(f"Traceback: {traceback.format_exc()}")
                continue
        
        # Update portfolio totals
        await update_portfolio_totals(portfolio.id, db)
        
        end_time = datetime.now()
        sync_duration = (end_time - start_time).total_seconds()
        
        return SyncPortfolioResponse(
            success=True,
            message=f"Portfolio synchronized successfully. {synced_holdings} holdings synced, {updated_assets} assets updated.",
            synced_holdings=synced_holdings,
            updated_assets=updated_assets,
            sync_duration=sync_duration
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Sync portfolio failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to sync portfolio")

async def update_portfolio_totals(portfolio_id: str, db: Prisma):
    """Update portfolio total values"""
    try:
        # Get all holdings for the portfolio
        holdings = await db.portfolioholding.find_many(
            where={"portfolioId": portfolio_id}
        )
        
        total_value = sum(holding.totalValue for holding in holdings)
        total_cost = sum(holding.totalCost for holding in holdings)
        total_gain_loss = total_value - total_cost
        total_gain_loss_percent = (total_gain_loss / total_cost) * 100 if total_cost > 0 else 0
        
        # Update portfolio
        await db.portfolio.update(
            where={"id": portfolio_id},
            data={
                "totalValue": total_value,
                "totalCost": total_cost,
                "totalGainLoss": total_gain_loss,
                "totalGainLossPercent": total_gain_loss_percent,
                "lastUpdated": datetime.now()
            }
        )
        
    except Exception as e:
        logger.error(f"Failed to update portfolio totals: {e}")
        raise 