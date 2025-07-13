import asyncio
import json
import websockets
from typing import Dict, Set, List, Optional
from fastapi import WebSocket, WebSocketDisconnect
from app.core.logger import logger
from app.services.binance_service import BinanceAPIService
from app.services.cache_service import CacheService
from app.core.database import get_db
from prisma import Prisma
import time
import httpx
from datetime import datetime


class PortfolioWebSocketManager:
    """
    Ultra-fast WebSocket manager for portfolio real-time updates
    Updates every 200ms with no latency
    """
    
    def __init__(self):
        # User ID -> Set of WebSocket connections
        self.user_connections: Dict[str, Set[WebSocket]] = {}
        # User ID -> Portfolio data
        self.user_portfolios: Dict[str, dict] = {}
        # User ID -> Asset symbols they hold
        self.user_symbols: Dict[str, Set[str]] = {}
        # Symbol -> Latest price data
        self.symbol_prices: Dict[str, dict] = {}
        # Binance WebSocket connection
        self.binance_ws_connection = None
        # All symbols we need to track
        self.tracked_symbols: Set[str] = set()
        
        self.binance_service = BinanceAPIService()
        self.cache_service = CacheService()
        
        # Start background tasks
        self.update_task = None
        self.price_fetcher_task = None
    
    async def connect_user(self, websocket: WebSocket, user_id: str):
        """Connect a user to portfolio WebSocket"""
        # Note: WebSocket is already accepted in the endpoint
        
        # Add to user connections
        if user_id not in self.user_connections:
            self.user_connections[user_id] = set()
        self.user_connections[user_id].add(websocket)
        
        logger.info(f"Portfolio WebSocket connected for user {user_id}. Total connections: {len(self.user_connections[user_id])}")
        
        # Load user's portfolio data
        await self.load_user_portfolio(user_id)
        
        # Start price streaming if this is the first connection
        if len(self.user_connections) == 1:
            await self.start_price_streaming()
        
        # Send initial portfolio data
        await self.send_initial_portfolio_data(websocket, user_id)
    
    async def disconnect_user(self, websocket: WebSocket, user_id: str):
        """Disconnect a user from portfolio WebSocket"""
        if user_id in self.user_connections and websocket in self.user_connections[user_id]:
            self.user_connections[user_id].remove(websocket)
            logger.info(f"Portfolio WebSocket disconnected for user {user_id}. Remaining: {len(self.user_connections[user_id])}")
        
        # Clean up empty user connections
        if user_id in self.user_connections and len(self.user_connections[user_id]) == 0:
            del self.user_connections[user_id]
            if user_id in self.user_portfolios:
                del self.user_portfolios[user_id]
            if user_id in self.user_symbols:
                del self.user_symbols[user_id]
        
        # Stop price streaming if no more connections
        if len(self.user_connections) == 0:
            await self.stop_price_streaming()
    
    async def load_user_portfolio(self, user_id: str):
        """Load user's portfolio data from database"""
        try:
            # Get database connection
            db = await get_db()
            
            # Get user's portfolio with holdings
            portfolio = await db.portfolio.find_unique(
                where={"userId": user_id},
                include={
                    "holdings": {
                        "include": {"asset": True}
                    }
                }
            )
            
            if not portfolio:
                logger.warning(f"No portfolio found for user {user_id}")
                # Create empty portfolio data
                self.user_portfolios[user_id] = {
                    "id": "",
                    "name": "Portfolio",
                    "total_value": 0,
                    "total_gain_loss": 0,
                    "total_gain_loss_percent": 0,
                    "holdings": []
                }
                self.user_symbols[user_id] = set()
                return
                
                # Extract symbols from holdings
                user_symbols = set()
                portfolio_data = {
                    "id": portfolio.id,
                    "name": portfolio.name,
                    "total_value": portfolio.totalValue or 0,
                    "total_gain_loss": portfolio.totalGainLoss or 0,
                    "total_gain_loss_percent": portfolio.totalGainLossPercent or 0,
                    "holdings": []
                }
                
                for holding in portfolio.holdings:
                    symbol = holding.symbol
                    user_symbols.add(symbol)
                    
                    # Add holding data
                    portfolio_data["holdings"].append({
                        "id": holding.id,
                        "symbol": symbol,
                        "quantity": holding.quantity,
                        "average_price": holding.averagePrice,
                        "current_price": holding.currentPrice,
                        "total_value": holding.totalValue or 0,
                        "gain_loss": holding.gainLoss or 0,
                        "gain_loss_percent": holding.gainLossPercent or 0,
                        "allocation": holding.allocation or 0
                    })
                
                # Store user data
                self.user_portfolios[user_id] = portfolio_data
                self.user_symbols[user_id] = user_symbols
                
                # Update tracked symbols
                self.tracked_symbols.update(user_symbols)
                
                logger.info(f"Loaded portfolio for user {user_id}: {len(portfolio_data['holdings'])} holdings, symbols: {list(user_symbols)}")
                
        except Exception as e:
            logger.error(f"Error loading portfolio for user {user_id}: {e}")
    
    async def send_initial_portfolio_data(self, websocket: WebSocket, user_id: str):
        """Send initial portfolio data to new connection"""
        try:
            portfolio_data = self.user_portfolios.get(user_id)
            if not portfolio_data:
                # Send empty portfolio message
                empty_portfolio = {
                    "id": "",
                    "name": "Portfolio",
                    "total_value": 0,
                    "total_gain_loss": 0,
                    "total_gain_loss_percent": 0,
                    "holdings": []
                }
                
                initial_message = {
                    "type": "initial_portfolio_data",
                    "data": empty_portfolio,
                    "timestamp": time.time()
                }
                
                await websocket.send_text(json.dumps(initial_message))
                logger.info(f"Sent empty portfolio data to user {user_id} (no portfolio found)")
                return
            
            # Get latest prices for all symbols
            await self.update_portfolio_prices(user_id)
            
            initial_message = {
                "type": "initial_portfolio_data",
                "data": self.user_portfolios[user_id],
                "timestamp": time.time()
            }
            
            await websocket.send_text(json.dumps(initial_message))
            logger.info(f"Sent initial portfolio data to user {user_id}")
            
        except Exception as e:
            logger.error(f"Error sending initial portfolio data for user {user_id}: {e}")
            try:
                # Send error message
                error_message = {
                    "type": "error",
                    "data": "Failed to load portfolio data",
                    "timestamp": time.time()
                }
                await websocket.send_text(json.dumps(error_message))
            except:
                pass
    
    async def start_price_streaming(self):
        """Start streaming real-time prices from Binance"""
        if not self.tracked_symbols:
            return
        
        try:
            # Start Bloomberg-level 200ms update timer
            self.update_task = asyncio.create_task(self.portfolio_update_timer())
            
            # Start price fetcher
            self.price_fetcher_task = asyncio.create_task(self.price_fetcher())
            
            logger.info(f"Started portfolio price streaming for {len(self.tracked_symbols)} symbols")
            
        except Exception as e:
            logger.error(f"Error starting price streaming: {e}")
    
    async def stop_price_streaming(self):
        """Stop price streaming"""
        if self.update_task:
            self.update_task.cancel()
            self.update_task = None
        
        if self.price_fetcher_task:
            self.price_fetcher_task.cancel()
            self.price_fetcher_task = None
        
        logger.info("Stopped portfolio price streaming")
    
    async def portfolio_update_timer(self):
        """Bloomberg-level 200ms update timer for portfolio values"""
        logger.info("Started portfolio update timer (200ms interval)")
        
        while len(self.user_connections) > 0:
            try:
                # Update all users' portfolios
                for user_id in list(self.user_connections.keys()):
                    await self.update_portfolio_prices(user_id)
                    await self.broadcast_portfolio_update(user_id)
                
                # Wait 200ms for Bloomberg-level updates
                await asyncio.sleep(0.2)
                
            except Exception as e:
                logger.error(f"Error in portfolio update timer: {e}")
                await asyncio.sleep(1)
    
    async def price_fetcher(self):
        """Fetch real-time prices from Binance API"""
        while len(self.user_connections) > 0:
            try:
                if not self.tracked_symbols:
                    await asyncio.sleep(1)
                    continue
                
                # Fetch prices for all tracked symbols
                async with httpx.AsyncClient() as client:
                    for symbol in self.tracked_symbols:
                        try:
                            response = await client.get(f"https://api.binance.com/api/v3/ticker/24hr?symbol={symbol}USDT")
                            if response.status_code == 200:
                                data = response.json()
                                self.symbol_prices[symbol] = {
                                    "price": float(data["lastPrice"]),
                                    "change_24h": float(data["priceChangePercent"]),
                                    "volume_24h": float(data["volume"]),
                                    "high_24h": float(data["highPrice"]),
                                    "low_24h": float(data["lowPrice"]),
                                    "timestamp": time.time()
                                }
                        except Exception as e:
                            logger.error(f"Error fetching price for {symbol}: {e}")
                            continue
                
                # Wait 1 second before next batch fetch
                await asyncio.sleep(1)
                
            except Exception as e:
                logger.error(f"Error in price fetcher: {e}")
                await asyncio.sleep(5)
    
    async def update_portfolio_prices(self, user_id: str):
        """Update portfolio calculations with latest prices"""
        try:
            portfolio_data = self.user_portfolios.get(user_id)
            if not portfolio_data:
                return
            
            total_value = 0
            total_cost = 0
            
            # Update each holding
            for holding in portfolio_data["holdings"]:
                symbol = holding["symbol"]
                price_data = self.symbol_prices.get(symbol)
                
                if price_data:
                    current_price = price_data["price"]
                    holding["current_price"] = current_price
                    
                    # Calculate values
                    quantity = holding["quantity"]
                    avg_price = holding["average_price"]
                    total_value_holding = quantity * current_price
                    total_cost_holding = quantity * avg_price
                    gain_loss = total_value_holding - total_cost_holding
                    gain_loss_percent = (gain_loss / total_cost_holding) * 100 if total_cost_holding > 0 else 0
                    
                    holding["total_value"] = total_value_holding
                    holding["gain_loss"] = gain_loss
                    holding["gain_loss_percent"] = gain_loss_percent
                    
                    total_value += total_value_holding
                    total_cost += total_cost_holding
            
            # Update portfolio totals
            total_gain_loss = total_value - total_cost
            total_gain_loss_percent = (total_gain_loss / total_cost) * 100 if total_cost > 0 else 0
            
            portfolio_data["total_value"] = total_value
            portfolio_data["total_gain_loss"] = total_gain_loss
            portfolio_data["total_gain_loss_percent"] = total_gain_loss_percent
            
            # Calculate allocations
            for holding in portfolio_data["holdings"]:
                holding["allocation"] = (holding["total_value"] / total_value) * 100 if total_value > 0 else 0
            
            # Update database
            await self.update_portfolio_database(user_id, portfolio_data)
            
        except Exception as e:
            logger.error(f"Error updating portfolio prices for user {user_id}: {e}")
    
    async def update_portfolio_database(self, user_id: str, portfolio_data: dict):
        """Update portfolio data in database"""
        try:
            db = await get_db()
            
            # Update portfolio totals
            await db.portfolio.update(
                where={"userId": user_id},
                data={
                    "totalValue": portfolio_data["total_value"],
                    "totalGainLoss": portfolio_data["total_gain_loss"],
                    "totalGainLossPercent": portfolio_data["total_gain_loss_percent"],
                    "updatedAt": datetime.now()
                }
            )
            
            # Update holdings
            for holding in portfolio_data["holdings"]:
                await db.portfolioholding.update(
                    where={"id": holding["id"]},
                    data={
                        "currentPrice": holding["current_price"],
                        "totalValue": holding["total_value"],
                        "gainLoss": holding["gain_loss"],
                        "gainLossPercent": holding["gain_loss_percent"],
                        "allocation": holding["allocation"]
                    }
                )
            
            # Update asset prices
            for symbol, price_data in self.symbol_prices.items():
                await db.asset.update(
                    where={"symbol": symbol},
                    data={
                        "currentPrice": price_data["price"],
                        "change24h": price_data["change_24h"],
                        "volume24h": price_data["volume_24h"],
                        "high24h": price_data["high_24h"],
                        "low24h": price_data["low_24h"],
                        "priceUpdatedAt": datetime.now()
                    }
                )
            
        except Exception as e:
            logger.error(f"Error updating database for user {user_id}: {e}")
    
    async def broadcast_portfolio_update(self, user_id: str):
        """Broadcast portfolio update to all user connections"""
        if user_id not in self.user_connections:
            return
        
        portfolio_data = self.user_portfolios.get(user_id)
        if not portfolio_data:
            return
        
        message = {
            "type": "portfolio_update",
            "data": portfolio_data,
            "timestamp": time.time()
        }
        
        # Send to all connected clients for this user
        disconnected = []
        for websocket in self.user_connections[user_id].copy():
            try:
                await websocket.send_text(json.dumps(message))
            except WebSocketDisconnect:
                disconnected.append(websocket)
            except Exception as e:
                logger.error(f"Error broadcasting portfolio update to user {user_id}: {e}")
                disconnected.append(websocket)
        
        # Remove disconnected clients
        for ws in disconnected:
            await self.disconnect_user(ws, user_id)
    
    async def handle_portfolio_change(self, user_id: str):
        """Handle portfolio changes (new holdings, deletions, etc.)"""
        # Reload portfolio data
        await self.load_user_portfolio(user_id)
        
        # Update tracked symbols
        self.tracked_symbols.clear()
        for symbols in self.user_symbols.values():
            self.tracked_symbols.update(symbols)
        
        # Send updated data immediately
        await self.update_portfolio_prices(user_id)
        await self.broadcast_portfolio_update(user_id)
        
        logger.info(f"Portfolio change handled for user {user_id}")


# Global portfolio WebSocket manager instance
portfolio_ws_manager = PortfolioWebSocketManager() 