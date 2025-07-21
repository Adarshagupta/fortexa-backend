import json
import asyncio
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from app.services.websocket_service import ws_manager
from app.services.individual_crypto_websocket import individual_crypto_ws_manager
from app.services.portfolio_websocket_service import portfolio_ws_manager
from app.core.logger import logger
from app.core.exceptions import AuthenticationException
from app.core.database import get_db
from prisma import Prisma
from jose import JWTError, jwt
from app.core.config import settings

router = APIRouter()

async def get_user_id_from_token(token: str) -> str:
    """Extract user ID from JWT token"""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id = payload.get("sub")
        if not user_id:
            raise AuthenticationException("Invalid token")
        return user_id
    except jwt.ExpiredSignatureError:
        raise AuthenticationException("Token expired")
    except JWTError:
        raise AuthenticationException("Invalid token")

@router.websocket("/ws/market-data")
async def websocket_market_data(websocket: WebSocket):
    """WebSocket endpoint for real-time market data streaming"""
    await ws_manager.connect(websocket)
    try:
        # Keep connection alive and handle ping/pong
        while True:
            message = await websocket.receive_text()
            # Handle client messages if needed (ping/pong, subscriptions, etc.)
            if message == "ping":
                await websocket.send_text("pong")
            
    except WebSocketDisconnect:
        logger.info("Client disconnected from WebSocket")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        await ws_manager.disconnect(websocket)

@router.websocket("/ws/portfolio")
async def websocket_portfolio(websocket: WebSocket, token: str = None):
    """WebSocket endpoint for real-time portfolio updates"""
    user_id = None
    
    try:
        # Accept connection first
        await websocket.accept()
        logger.info("Portfolio WebSocket connection accepted")
        
        # Get token from query params or first message
        if not token:
            try:
                # Wait for auth message with timeout
                auth_message = await asyncio.wait_for(websocket.receive_text(), timeout=10.0)
                logger.info(f"Received auth message: {auth_message[:50]}...")
                
                auth_data = json.loads(auth_message)
                token = auth_data.get("token")
                
                if not token:
                    raise ValueError("No token provided in auth message")
                    
            except asyncio.TimeoutError:
                logger.error("Timeout waiting for auth message")
                await websocket.close(code=1008, reason="Authentication timeout")
                return
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON in auth message: {e}")
                await websocket.close(code=1003, reason="Invalid JSON")
                return
            except Exception as e:
                logger.error(f"Error receiving auth message: {e}")
                await websocket.close(code=1002, reason="Protocol error")
                return
        
        # Validate token and get user ID
        try:
            user_id = await get_user_id_from_token(token)
            logger.info(f"Authenticated user: {user_id}")
        except AuthenticationException as e:
            logger.error(f"Authentication failed: {e}")
            await websocket.close(code=1008, reason="Authentication failed")
            return
        
        # Connect to portfolio WebSocket manager
        await portfolio_ws_manager.connect_user(websocket, user_id)
        logger.info(f"Portfolio WebSocket manager connected for user {user_id}")
        
        try:
            # Keep connection alive and handle messages
            while True:
                try:
                    message = await websocket.receive_text()
                    
                    if message == "ping":
                        await websocket.send_text("pong")
                    elif message.startswith("portfolio_changed"):
                        # Handle portfolio changes (new holdings, deletions)
                        await portfolio_ws_manager.handle_portfolio_change(user_id)
                        
                except WebSocketDisconnect:
                    logger.info(f"Portfolio WebSocket disconnected for user {user_id}")
                    break
                except Exception as e:
                    logger.error(f"Error handling message for user {user_id}: {e}")
                    break
                
        except Exception as e:
            logger.error(f"Portfolio WebSocket error for user {user_id}: {e}")
        finally:
            if user_id:
                await portfolio_ws_manager.disconnect_user(websocket, user_id)
            
    except Exception as e:
        logger.error(f"Portfolio WebSocket connection error: {e}")
        # Only try to close if the connection is still open
        try:
            if websocket.client_state.name == "CONNECTED":
                await websocket.close(code=1011, reason="Internal server error")
        except:
            pass

@router.websocket("/ws/crypto/{symbol}")
async def websocket_individual_crypto(websocket: WebSocket, symbol: str):
    """
    Bloomberg terminal-level WebSocket for individual crypto pages
    Updates every 200ms with price and candlestick data
    """
    await individual_crypto_ws_manager.connect_symbol(websocket, symbol)
    try:
        # Keep connection alive and handle messages
        while True:
            message = await websocket.receive_text()
            if message == "ping":
                await websocket.send_text("pong")
            
    except WebSocketDisconnect:
        logger.info(f"Client disconnected from {symbol} WebSocket")
    except Exception as e:
        logger.error(f"Individual crypto WebSocket error for {symbol}: {e}")
    finally:
        await individual_crypto_ws_manager.disconnect_symbol(websocket, symbol) 