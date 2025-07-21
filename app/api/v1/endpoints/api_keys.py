from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import HTMLResponse
from prisma import Prisma
from typing import List, Optional
from datetime import datetime
import asyncio
from cryptography.fernet import Fernet
import os

from app.core.database import get_db
from app.schemas.api_keys import *
from app.api.v1.endpoints.auth import get_current_user_id
from app.core.logger import logger
from app.core.exceptions import *
from app.core.config import settings
from app.services.binance_service import BinanceAPIService
from app.services.zerodha_service import zerodha_service
from app.services.angel_one_service import angel_one_service
from app.services.groww_service import groww_service

router = APIRouter()

# Encryption key for API keys (should be stored securely in production)
ENCRYPTION_KEY = os.getenv('API_KEY_ENCRYPTION_KEY')
if not ENCRYPTION_KEY:
    logger.error("API_KEY_ENCRYPTION_KEY environment variable not set!")
    ENCRYPTION_KEY = Fernet.generate_key()
    logger.warning(f"Generated new encryption key: {ENCRYPTION_KEY.decode()}")
else:
    logger.info("API_KEY_ENCRYPTION_KEY loaded from environment")

# Ensure the key is bytes for Fernet
if isinstance(ENCRYPTION_KEY, str):
    ENCRYPTION_KEY = ENCRYPTION_KEY.encode()

cipher_suite = Fernet(ENCRYPTION_KEY)

def encrypt_api_key(api_key: str) -> str:
    """Encrypt API key for storage"""
    return cipher_suite.encrypt(api_key.encode()).decode()

def decrypt_api_key(encrypted_key: str) -> str:
    """Decrypt API key for use"""
    try:
        return cipher_suite.decrypt(encrypted_key.encode()).decode()
    except Exception as e:
        logger.error(f"Failed to decrypt API key: {e}")
        logger.error(f"This usually means the API_KEY_ENCRYPTION_KEY has changed or is incorrect")
        logger.error(f"Current encryption key (first 10 chars): {str(ENCRYPTION_KEY)[:10]}...")
        raise HTTPException(
            status_code=500, 
            detail="Unable to decrypt API key. The encryption key may have changed. Please contact support or re-add your API keys."
        )

@router.post("/", response_model=AddApiKeyResponse)
async def add_api_key(
    request: AddApiKeyRequest,
    current_user_id: str = Depends(get_current_user_id),
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
        
        # Validate provider-specific requirements  
        if request.provider == ApiProvider.ZERODHA:
            # Zerodha uses OAuth flow - credentials are handled via OAuth callback
            logger.info("Zerodha integration uses OAuth flow - no manual credentials required")
        elif request.provider == ApiProvider.ANGEL_ONE:
            # Angel One uses OAuth flow - credentials are handled via OAuth callback
            logger.info("Angel One integration uses OAuth flow - no manual credentials required")
        elif request.provider == ApiProvider.GROWW:
            # Groww doesn't require API credentials currently (CSV import only)
            logger.info("Groww integration uses CSV import - no API credentials required")
        
        # Angel One and Zerodha use OAuth - handled separately via OAuth callback
        if request.provider in [ApiProvider.ANGEL_ONE, ApiProvider.ZERODHA]:
            provider_name = request.provider.value.replace('_', ' ').title()
            raise HTTPException(
                status_code=400,
                detail=f"{provider_name} integration uses OAuth. Please use the 'Connect {provider_name} Account' button instead."
            )
        
        # Encrypt sensitive data for other providers
        encrypted_api_key = encrypt_api_key(request.api_key)
        encrypted_secret_key = encrypt_api_key(request.secret_key) if request.secret_key else None
        
        # Encrypt additional fields for other Indian brokers (not Angel One)
        encrypted_client_code = encrypt_api_key(request.client_code) if request.client_code else None
        encrypted_password = encrypt_api_key(request.password) if request.password else None
        encrypted_totp_secret = encrypt_api_key(request.totp_secret) if request.totp_secret else None
        encrypted_access_token = encrypt_api_key(request.access_token) if request.access_token else None
        
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
        
        # Store additional encrypted fields in a JSON field (for Zerodha and Groww only)
        additional_data = {
            "client_code": encrypted_client_code,
            "password": encrypted_password,
            "totp_secret": encrypted_totp_secret,
            "access_token": encrypted_access_token
        }
        
        # Store additional data for Zerodha and Groww (Angel One handled via OAuth)
        if request.provider in [ApiProvider.ZERODHA, ApiProvider.GROWW]:
            import json
            additional_json = json.dumps({k: v for k, v in additional_data.items() if v is not None})
            if additional_json != "{}":
                await db.apikey.update(
                    where={"id": api_key.id},
                    data={"secretKey": encrypt_api_key(additional_json)}
                )
        
        logger.info(f"API key added for user {current_user_id}: {request.name} ({request.provider.value})")
        
        response_api_key = ApiKeyResponse(
            id=api_key.id,
            name=api_key.name,
            provider=ApiProvider(api_key.provider),
            testnet=api_key.testnet,
            is_active=api_key.isActive,
            last_used=api_key.lastUsed,
            permissions=api_key.permissions,
            created_at=api_key.createdAt,
            updated_at=api_key.updatedAt,
            has_client_code=request.client_code is not None,
            has_access_token=request.access_token is not None
        )
        
        return AddApiKeyResponse(api_key=response_api_key)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Add API key failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to add API key")

@router.get("/", response_model=ApiKeysListResponse)
async def get_api_keys(
    current_user_id: str = Depends(get_current_user_id),
    db: Prisma = Depends(get_db)
):
    """Get all API keys for the current user"""
    try:
        api_keys = await db.apikey.find_many(
            where={"userId": current_user_id}
        )
        
        api_key_responses = []
        for key in api_keys:
            # Check if additional data exists for Indian brokers
            has_client_code = False
            has_access_token = False
            
            if key.provider in ["ZERODHA", "ANGEL_ONE", "GROWW"] and key.secretKey:
                try:
                    decrypted_secret = decrypt_api_key(key.secretKey)
                    if decrypted_secret.startswith('{'):  # JSON data
                        import json
                        additional_data = json.loads(decrypted_secret)
                        has_client_code = additional_data.get('client_code') is not None
                        has_access_token = additional_data.get('access_token') is not None
                except:
                    pass  # Ignore decryption errors for display
            
            api_key_responses.append(ApiKeyResponse(
                id=key.id,
                name=key.name,
                provider=ApiProvider(key.provider),
                testnet=key.testnet,
                is_active=key.isActive,
                last_used=key.lastUsed,
                permissions=key.permissions,
                created_at=key.createdAt,
                updated_at=key.updatedAt,
                has_client_code=has_client_code,
                has_access_token=has_access_token
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
    current_user_id: str = Depends(get_current_user_id),
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
    current_user_id: str = Depends(get_current_user_id),
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

@router.get("/debug/encryption-info")
async def get_encryption_info(
    current_user_id: str = Depends(get_current_user_id)
):
    """Debug endpoint to check encryption key info (for troubleshooting)"""
    try:
        return {
            "encryption_key_source": "environment" if os.getenv('API_KEY_ENCRYPTION_KEY') else "generated",
            "encryption_key_prefix": str(ENCRYPTION_KEY)[:10] + "...",
            "encryption_key_length": len(ENCRYPTION_KEY),
            "message": "If you're having decryption issues, the API_KEY_ENCRYPTION_KEY may have changed. You may need to re-add your API keys."
        }
    except Exception as e:
        logger.error(f"Get encryption info failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to get encryption info")

@router.post("/sync-portfolio", response_model=SyncPortfolioResponse)
async def sync_portfolio(
    request: SyncPortfolioRequest,
    current_user_id: str = Depends(get_current_user_id),
    db: Prisma = Depends(get_db)
):
    """Sync portfolio from trading platforms"""
    try:
        start_time = datetime.now()
        
        # Get user's portfolio (or create if doesn't exist)
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
                }
            )
            logger.info(f"Created new portfolio for user {current_user_id}")
        
        # Get API keys to sync
        if request.api_key_id:
            api_keys = await db.apikey.find_many(
                where={
                    "userId": current_user_id,
                    "id": request.api_key_id,
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
            raise HTTPException(
                status_code=404,
                detail="No active API keys found"
            )
        
        synced_holdings = 0
        updated_assets = 0
        sync_provider = None
        sync_method = "api"
        
        # Sync data from each API key
        for api_key in api_keys:
            try:
                sync_provider = ApiProvider(api_key.provider)
                
                if api_key.provider == "BINANCE":
                    # Existing Binance logic
                    try:
                        decrypted_api_key = decrypt_api_key(api_key.apiKey)
                        decrypted_secret_key = decrypt_api_key(api_key.secretKey)
                    except HTTPException as http_exc:
                        logger.error(f"Decryption failed for API key {api_key.id}: {http_exc.detail}")
                        continue
                    
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
                    
                elif api_key.provider == "ZERODHA":
                    # Zerodha sync logic
                    try:
                        # Get additional data from secretKey field
                        additional_data = {}
                        if api_key.secretKey:
                            decrypted_secret = decrypt_api_key(api_key.secretKey)
                            if decrypted_secret.startswith('{'):
                                import json
                                additional_data = json.loads(decrypted_secret)
                        
                        access_token = None
                        if additional_data.get('access_token'):
                            access_token = decrypt_api_key(additional_data['access_token'])
                        
                        if not access_token:
                            logger.warning(f"No access token available for Zerodha API key {api_key.id}")
                            continue
                        
                        sync_result = await zerodha_service.sync_portfolio(
                            access_token=access_token,
                            portfolio_id=portfolio.id,
                            db=db
                        )
                        
                        synced_holdings += sync_result.get('synced_holdings', 0)
                        updated_assets += sync_result.get('updated_assets', 0)
                        
                    except Exception as e:
                        logger.error(f"Zerodha sync failed: {e}")
                        continue
                
                elif api_key.provider == "ANGEL_ONE":
                    # Angel One OAuth sync logic
                    try:
                        # For OAuth-based Angel One connections, the access token is stored in secretKey
                        if not api_key.secretKey:
                            logger.warning(f"Missing OAuth token for Angel One API key {api_key.id}")
                            continue
                        
                        # Decrypt OAuth access token
                        access_token = decrypt_api_key(api_key.secretKey)
                        
                        # Sync portfolio using OAuth token
                        sync_result = await angel_one_service.sync_portfolio_oauth(
                            access_token=access_token,
                            portfolio_id=portfolio.id,
                            db=db
                        )
                        
                        synced_holdings += sync_result.get('synced_holdings', 0)
                        updated_assets += sync_result.get('updated_assets', 0)
                        
                    except Exception as e:
                        logger.error(f"Angel One OAuth sync failed: {e}")
                        continue
                
                elif api_key.provider == "GROWW":
                    # Groww currently only supports CSV import
                    logger.info("Groww sync via API not available - use CSV import endpoint")
                    continue
                
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
        
        end_time = datetime.now()
        sync_duration = (end_time - start_time).total_seconds()
        
        return SyncPortfolioResponse(
            success=True,
            message=f"Successfully synced {synced_holdings} holdings and {updated_assets} assets",
            synced_holdings=synced_holdings,
            updated_assets=updated_assets,
            sync_duration=sync_duration,
            provider=sync_provider or ApiProvider.BINANCE,
            method=sync_method
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Portfolio sync failed: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail="Failed to sync portfolio")

@router.post("/groww/import-csv", response_model=GrowwImportResponse)
async def import_groww_csv(
    request: GrowwImportRequest,
    current_user_id: str = Depends(get_current_user_id),
    db: Prisma = Depends(get_db)
):
    """Import Groww portfolio data from CSV export"""
    try:
        # Get or create user's portfolio
        portfolio = await db.portfolio.find_unique(
            where={"userId": current_user_id}
        )
        
        if not portfolio:
            portfolio = await db.portfolio.create(
                data={
                    "userId": current_user_id,
                    "name": request.portfolio_name,
                    "totalValue": 0.0,
                    "totalCost": 0.0,
                    "totalGainLoss": 0.0,
                    "totalGainLossPercent": 0.0,
                }
            )
        
        # Import CSV data using Groww service
        import_result = await groww_service.import_from_csv(
            csv_data=request.csv_data,
            portfolio_id=portfolio.id,
            db=db
        )
        
        return GrowwImportResponse(
            success=True,
            message=f"Successfully imported {import_result.get('synced_holdings', 0)} holdings from Groww",
            imported_holdings=import_result.get('synced_holdings', 0),
            created_assets=import_result.get('updated_assets', 0)
        )
        
    except Exception as e:
        logger.error(f"Groww CSV import failed: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to import Groww CSV: {str(e)}")

# Helper functions for updating portfolio totals
async def update_portfolio_totals(portfolio_id: str, db: Prisma) -> None:
    """Update portfolio totals after sync"""
    try:
        holdings = await db.portfolioholding.find_many(
            where={'portfolioId': portfolio_id}
        )
        
        total_value = sum(holding.totalValue or 0.0 for holding in holdings)
        total_cost = sum(holding.totalCost or 0.0 for holding in holdings)
        total_gain_loss = sum(holding.gainLoss or 0.0 for holding in holdings)
        total_gain_loss_percent = (total_gain_loss / total_cost) * 100 if total_cost > 0 else 0
        
        await db.portfolio.update(
            where={'id': portfolio_id},
            data={
                'totalValue': total_value,
                'totalCost': total_cost,
                'totalGainLoss': total_gain_loss,
                'totalGainLossPercent': total_gain_loss_percent,
                'lastUpdated': datetime.now()
            }
        )
        
    except Exception as e:
        logger.error(f"Failed to update portfolio totals: {e}")
        raise 

@router.get("/angel-one/auth-url")
async def get_angel_one_auth_url(
    current_user_id: str = Depends(get_current_user_id)
):
    """Get Angel One OAuth authorization URL"""
    try:
        client_id = os.getenv('ANGEL_ONE_CLIENT_ID')
        redirect_uri = settings.get_angel_one_redirect_url
        
        if not client_id:
            raise HTTPException(status_code=500, detail="Angel One OAuth not configured")
        
        # Angel One OAuth URL with state parameter for user identification
        auth_url = f"https://smartapi.angelbroking.com/publisher-login?api_key={client_id}&redirect_url={redirect_uri}&state={current_user_id}"
        
        return {
            "auth_url": auth_url,
            "state": current_user_id
        }
        
    except Exception as e:
        logger.error(f"Failed to generate Angel One auth URL: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate authorization URL")

@router.get("/zerodha/auth-url")
async def get_zerodha_auth_url(
    current_user_id: str = Depends(get_current_user_id)
):
    """Get Zerodha OAuth authorization URL"""
    try:
        client_id = os.getenv('ZERODHA_CLIENT_ID')
        redirect_uri = settings.get_zerodha_redirect_url
        
        if not client_id:
            raise HTTPException(status_code=500, detail="Zerodha OAuth not configured")
        
        # Zerodha Kite Connect OAuth URL with state parameter
        # Note: Zerodha doesn't support state parameter, so we'll handle user association differently
        auth_url = f"https://kite.trade/connect/login?api_key={client_id}&v=3"
        
        return {
            "auth_url": auth_url,
            "state": current_user_id
        }
        
    except Exception as e:
        logger.error(f"Failed to generate Zerodha auth URL: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate authorization URL")

@router.get("/angel-one/callback")
async def angel_one_oauth_callback(
    auth_token: str,
    feed_token: str,
    refresh_token: str,
    state: str = None,
    db: Prisma = Depends(get_db)
):
    """Handle Angel One OAuth callback"""
    try:
        client_id = os.getenv('ANGEL_ONE_CLIENT_ID')
        client_secret = os.getenv('ANGEL_ONE_CLIENT_SECRET')
        
        if not client_id or not client_secret:
            raise HTTPException(status_code=500, detail="Angel One OAuth not configured")
        
        # Extract user ID from state or decode from auth_token
        user_id = state
        if not user_id:
            # If state is missing, try to extract user info from auth_token
            # This is a fallback - in production you'd parse the JWT
            user_id = "temp-user"  # You'd need to implement proper user extraction
        
        # Store the connected account
        api_key = await db.apikey.create(
            data={
                "userId": user_id,
                "name": "Angel One Account",
                "provider": "ANGEL_ONE",
                "apiKey": encrypt_api_key(auth_token),
                "secretKey": encrypt_api_key(refresh_token),
                "testnet": False,
                "permissions": ["read", "trade"],
                "isActive": True,
            }
        )
        
        logger.info(f"Angel One account connected for user {user_id}")
        
        # Redirect back to frontend with success message
        redirect_response = HTMLResponse(content=f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Angel One Connected</title>
            <style>
                body {{ font-family: Arial, sans-serif; text-align: center; padding: 50px; background: #1a1a1a; color: white; }}
                .success {{ color: #4ade80; font-size: 24px; margin-bottom: 20px; }}
                .message {{ font-size: 16px; margin-bottom: 30px; }}
                .redirect {{ color: #60a5fa; }}
            </style>
        </head>
        <body>
            <div class="success">✅ Angel One Account Connected!</div>
            <div class="message">Your Angel One account has been successfully connected to Fortexa.</div>
            <div class="redirect">You can now close this window and return to the app.</div>
            <script>
                // Close the popup window
                setTimeout(function() {{
                    if (window.opener) {{
                        window.opener.location.reload();
                        window.close();
                    }} else {{
                        window.location.href = 'https://fortexa.tech/settings?connected=angel-one';
                    }}
                }}, 2000);
            </script>
        </body>
        </html>
        """)
        
        return redirect_response
        
    except Exception as e:
        logger.error(f"Angel One OAuth callback failed: {e}")
        error_response = HTMLResponse(content=f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Connection Failed</title>
            <style>
                body {{ font-family: Arial, sans-serif; text-align: center; padding: 50px; background: #1a1a1a; color: white; }}
                .error {{ color: #ef4444; font-size: 24px; margin-bottom: 20px; }}
                .message {{ font-size: 16px; }}
            </style>
        </head>
        <body>
            <div class="error">❌ Connection Failed</div>
            <div class="message">Failed to connect Angel One account. Please try again.</div>
            <script>
                setTimeout(function() {{
                    if (window.opener) {{
                        window.close();
                    }} else {{
                        window.location.href = 'https://fortexa.tech/settings';
                    }}
                }}, 3000);
            </script>
        </body>
        </html>
        """)
        return error_response

@router.get("/zerodha/callback")
async def zerodha_oauth_callback(
    request_token: str,
    action: str,
    status: str,
    state: str = None,
    db: Prisma = Depends(get_db)
):
    """Handle Zerodha OAuth callback"""
    try:
        client_id = os.getenv('ZERODHA_CLIENT_ID')
        client_secret = os.getenv('ZERODHA_CLIENT_SECRET')
        
        if not client_id or not client_secret:
            raise HTTPException(status_code=500, detail="Zerodha OAuth not configured")
        
        if status != "success":
            error_response = HTMLResponse(content="""
            <!DOCTYPE html>
            <html>
            <head>
                <title>Authorization Failed</title>
                <style>
                    body { font-family: Arial, sans-serif; text-align: center; padding: 50px; background: #1a1a1a; color: white; }
                    .error { color: #ef4444; font-size: 24px; margin-bottom: 20px; }
                </style>
            </head>
            <body>
                <div class="error">❌ Zerodha Authorization Failed</div>
                <div>Please try connecting again.</div>
                <script>
                    setTimeout(function() {
                        if (window.opener) { window.close(); }
                        else { window.location.href = 'https://fortexa.tech/settings'; }
                    }, 3000);
                </script>
            </body>
            </html>
            """)
            return error_response
        
        # Extract user ID from state parameter
        user_id = state or "temp-user"  # In production, implement proper user session handling
        
        # TODO: Exchange request token for access token using Zerodha's API
        # For now, we store the request token and will implement full OAuth later
        
        # Store the connected account
        api_key = await db.apikey.create(
            data={
                "userId": user_id,
                "name": "Zerodha Account", 
                "provider": "ZERODHA",
                "apiKey": encrypt_api_key(client_id),
                "secretKey": encrypt_api_key(request_token),  # Store the request token
                "testnet": False,
                "permissions": ["read", "trade"],
                "isActive": True,
            }
        )
        
        logger.info(f"Zerodha account connected for user {user_id} with request token: {request_token}")
        
        # Return success HTML response
        success_response = HTMLResponse(content="""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Zerodha Connected</title>
            <style>
                body { font-family: Arial, sans-serif; text-align: center; padding: 50px; background: #1a1a1a; color: white; }
                .success { color: #4ade80; font-size: 24px; margin-bottom: 20px; }
                .message { font-size: 16px; margin-bottom: 30px; }
                .redirect { color: #60a5fa; }
            </style>
        </head>
        <body>
            <div class="success">✅ Zerodha Account Connected!</div>
            <div class="message">Your Zerodha account has been successfully connected to Fortexa.</div>
            <div class="redirect">You can now close this window and return to the app.</div>
            <script>
                setTimeout(function() {
                    if (window.opener) {
                        window.opener.location.reload();
                        window.close();
                    } else {
                        window.location.href = 'https://fortexa.tech/settings?connected=zerodha';
                    }
                }, 2000);
            </script>
        </body>
        </html>
        """)
        
        return success_response
        
    except Exception as e:
        logger.error(f"Zerodha OAuth callback failed: {e}")
        error_response = HTMLResponse(content=f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Connection Failed</title>
            <style>
                body {{ font-family: Arial, sans-serif; text-align: center; padding: 50px; background: #1a1a1a; color: white; }}
                .error {{ color: #ef4444; font-size: 24px; margin-bottom: 20px; }}
                .message {{ font-size: 16px; }}
            </style>
        </head>
        <body>
            <div class="error">❌ Connection Failed</div>
            <div class="message">Failed to connect Zerodha account: {str(e)[:100]}...</div>
            <script>
                setTimeout(function() {{
                    if (window.opener) {{
                        window.close();
                    }} else {{
                        window.location.href = 'https://fortexa.tech/settings';
                    }}
                }}, 3000);
            </script>
        </body>
        </html>
        """)
        return error_response 