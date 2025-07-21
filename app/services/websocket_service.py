import asyncio
import json
import websockets
from typing import Dict, Set, List, Optional
from fastapi import WebSocket, WebSocketDisconnect
from app.core.logger import logger
from app.services.binance_service import BinanceAPIService
from app.services.cache_service import CacheService
import time
import threading


class WebSocketManager:
    def __init__(self):
        self.active_connections: Set[WebSocket] = set()
        self.binance_service = BinanceAPIService()
        self.cache_service = CacheService()
        self.binance_ws_connection = None
        self.price_updates: Dict[str, dict] = {}
        self.last_broadcast = time.time()
        
        # Popular symbols to stream (Top 50 by volume)
        self.symbols_to_stream = [
            "BTCUSDT", "ETHUSDT", "SOLUSDT", "ADAUSDT", "AVAXUSDT", "DOTUSDT", 
            "LINKUSDT", "MATICUSDT", "UNIUSDT", "LTCUSDT", "PEPEUSDT", "SHIBUSDT",
            "BONKUSDT", "FLOKIUSDT", "DOGEUSDT", "XRPUSDT", "BCHUSDT", "NEARUSDT",
            "APTUSDT", "SUIUSDT", "ATOMUSDT", "FTMUSDT", "ICPUSDT", "VETUSDT",
            "FILUSDT", "HBARUSDT", "INJUSDT", "THETAUSDT", "TRXUSDT", "EOSUSDT",
            "XLMUSDT", "XMRUSDT", "AAVEUSDT", "GRTUSDT", "SANDUSDT", "MANAUSDT",
            "CHZUSDT", "ENJUSDT", "AXSUSDT", "GALAUSDT", "FLOWUSDT", "ZILUSDT",
            "CRVUSDT", "COMPUSDT", "SUSHIUSDT", "YFIUSDT", "SNXUSDT", "MKRUSDT",
            "ZECUSDT", "DASHUSDT"
        ]
    
    async def connect(self, websocket: WebSocket):
        """Connect a new WebSocket client"""
        await websocket.accept()
        self.active_connections.add(websocket)
        logger.info(f"New WebSocket connection. Total connections: {len(self.active_connections)}")
        
        # Start Binance stream if this is the first connection
        if len(self.active_connections) == 1:
            await self.start_binance_stream()
        
        # Send initial data to the new connection
        await self.send_initial_data(websocket)
    
    async def disconnect(self, websocket: WebSocket):
        """Disconnect a WebSocket client"""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            logger.info(f"WebSocket disconnected. Total connections: {len(self.active_connections)}")
        
        # Stop Binance stream if no more connections
        if len(self.active_connections) == 0:
            await self.stop_binance_stream()
    
    async def send_initial_data(self, websocket: WebSocket):
        """Send initial market data to new connection"""
        try:
            # Get current market data directly (it's already async)
            market_data = await self.binance_service.get_top_cryptocurrencies(50)
            
            # Transform to expected format
            formatted_data = {
                "trending_assets": [
                    self.binance_service.format_market_data(item) 
                    for item in market_data
                ]
            }
            
            initial_message = {
                "type": "initial_data",
                "data": formatted_data,
                "timestamp": time.time()
            }
            
            await websocket.send_text(json.dumps(initial_message))
            logger.info("Sent initial market data to new connection")
            
        except Exception as e:
            logger.error(f"Error sending initial data: {e}")
    
    async def start_binance_stream(self):
        """Start the Binance WebSocket stream"""
        try:
            # Create stream URL for individual ticker streams
            stream_names = [f"{symbol.lower()}@ticker" for symbol in self.symbols_to_stream]
            # Use the multi-stream format
            stream_url = f"wss://stream.binance.com:9443/stream?streams={'/'.join(stream_names)}"
            
            # Start the connection task
            asyncio.create_task(self.binance_stream_handler(stream_url))
            logger.info(f"Started Binance WebSocket stream for {len(self.symbols_to_stream)} symbols")
            
        except Exception as e:
            logger.error(f"Error starting Binance stream: {e}")
    
    async def binance_stream_handler(self, stream_url: str):
        """Handle incoming Binance WebSocket messages"""
        while len(self.active_connections) > 0:
            try:
                async with websockets.connect(stream_url) as websocket:
                    self.binance_ws_connection = websocket
                    logger.info("Connected to Binance WebSocket stream")
                    
                    async for message in websocket:
                        data = json.loads(message)
                        await self.process_binance_message(data)
                        
            except websockets.exceptions.ConnectionClosed:
                logger.warning("Binance WebSocket connection closed, reconnecting...")
                await asyncio.sleep(1)
            except Exception as e:
                logger.error(f"Error in Binance stream handler: {e}")
                await asyncio.sleep(5)
    
    async def process_binance_message(self, data: dict):
        """Process incoming Binance ticker messages"""
        try:
            # Handle both single stream and multi-stream formats
            ticker_data = None
            
            if 'stream' in data and 'data' in data:
                # Multi-stream format
                ticker_data = data['data']
            elif 'e' in data and data['e'] == '24hrTicker':
                # Single stream format
                ticker_data = data
            
            if ticker_data:
                symbol = ticker_data.get('s', '')
                
                # Transform Binance ticker data
                price_update = {
                    'symbol': symbol,
                    'price': float(ticker_data.get('c', 0)),
                    'change_24h': float(ticker_data.get('P', 0)),  # P is percentage change
                    'volume_24h': float(ticker_data.get('v', 0)),
                    'high_24h': float(ticker_data.get('h', 0)),
                    'low_24h': float(ticker_data.get('l', 0)),
                    'timestamp': time.time()
                }
                
                # Store update
                self.price_updates[symbol] = price_update
                
                # Cache the update with full ticker data format
                try:
                    # Store full ticker data format for compatibility with other endpoints
                    cache_data = {
                        'symbol': symbol,
                        'lastPrice': str(ticker_data.get('c', 0)),
                        'priceChange': str(ticker_data.get('p', 0)),
                        'priceChangePercent': str(ticker_data.get('P', 0)),
                        'volume': str(ticker_data.get('v', 0)),
                        'quoteVolume': str(ticker_data.get('q', 0)),
                        'highPrice': str(ticker_data.get('h', 0)),
                        'lowPrice': str(ticker_data.get('l', 0)),
                        'openPrice': str(ticker_data.get('o', 0)),
                        'prevClosePrice': str(ticker_data.get('x', 0)),
                        'bidPrice': str(ticker_data.get('c', 0)),  # Use last price as bid approximation
                        'askPrice': str(ticker_data.get('c', 0)),  # Use last price as ask approximation
                        'timestamp': price_update['timestamp']
                    }
                    self.cache_service.set_price_data(symbol, cache_data)
                except Exception as e:
                    logger.error(f"Error caching price update: {e}")
                
                # Broadcast immediately for significant changes (>0.5%)
                if abs(price_update['change_24h']) > 0.5:
                    await self.broadcast_price_update(price_update)
                
                # Batch broadcast every 200ms
                current_time = time.time()
                if current_time - self.last_broadcast > 0.2:  # 200ms
                    await self.broadcast_batch_updates()
                    self.last_broadcast = current_time
                    
        except Exception as e:
            logger.error(f"Error processing Binance message: {e}")
    
    async def broadcast_price_update(self, price_update: dict):
        """Broadcast a single price update to all connected clients"""
        if not self.active_connections:
            return
        
        message = {
            "type": "price_update",
            "data": price_update,
            "timestamp": time.time()
        }
        
        # Send to all connected clients
        disconnected = []
        for websocket in self.active_connections:
            try:
                await websocket.send_text(json.dumps(message))
            except WebSocketDisconnect:
                disconnected.append(websocket)
            except Exception as e:
                logger.error(f"Error sending price update: {e}")
                disconnected.append(websocket)
        
        # Remove disconnected clients
        for ws in disconnected:
            await self.disconnect(ws)
    
    async def broadcast_batch_updates(self):
        """Broadcast all accumulated price updates"""
        if not self.active_connections or not self.price_updates:
            return
        
        message = {
            "type": "batch_updates",
            "data": list(self.price_updates.values()),
            "timestamp": time.time()
        }
        
        # Send to all connected clients
        disconnected = []
        for websocket in self.active_connections:
            try:
                await websocket.send_text(json.dumps(message))
            except WebSocketDisconnect:
                disconnected.append(websocket)
            except Exception as e:
                logger.error(f"Error sending batch updates: {e}")
                disconnected.append(websocket)
        
        # Remove disconnected clients
        for ws in disconnected:
            await self.disconnect(ws)
        
        # Clear the updates after broadcasting
        self.price_updates.clear()
    
    async def stop_binance_stream(self):
        """Stop the Binance WebSocket stream"""
        if self.binance_ws_connection:
            await self.binance_ws_connection.close()
            self.binance_ws_connection = None
            logger.info("Stopped Binance WebSocket stream")


# Global WebSocket manager instance
ws_manager = WebSocketManager() 