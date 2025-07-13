import asyncio
import json
import websockets
from typing import Dict, Set, List, Optional
from fastapi import WebSocket, WebSocketDisconnect
from app.core.logger import logger
from app.services.binance_service import BinanceAPIService
import time

class IndividualCryptoWebSocketManager:
    """
    Ultra-fast WebSocket manager for individual crypto pages
    Bloomberg terminal-level speed with 200ms updates
    """
    
    def __init__(self):
        # Symbol -> Set of WebSocket connections
        self.symbol_connections: Dict[str, Set[WebSocket]] = {}
        # Symbol -> Binance WebSocket connection
        self.binance_connections: Dict[str, Optional[object]] = {}
        # Symbol -> Latest price data
        self.symbol_data: Dict[str, dict] = {}
        # Symbol -> Latest kline data
        self.symbol_klines: Dict[str, dict] = {}
        
        self.binance_service = BinanceAPIService()
    
    async def connect_symbol(self, websocket: WebSocket, symbol: str):
        """Connect to a specific symbol's real-time data"""
        symbol = symbol.upper()
        await websocket.accept()
        
        # Add to symbol connections
        if symbol not in self.symbol_connections:
            self.symbol_connections[symbol] = set()
        self.symbol_connections[symbol].add(websocket)
        
        logger.info(f"New connection for {symbol}. Total connections: {len(self.symbol_connections[symbol])}")
        
        # Start Binance stream if this is the first connection for this symbol
        if len(self.symbol_connections[symbol]) == 1:
            await self.start_symbol_stream(symbol)
        
        # Send initial data immediately
        await self.send_initial_symbol_data(websocket, symbol)
    
    async def disconnect_symbol(self, websocket: WebSocket, symbol: str):
        """Disconnect from a symbol's real-time data"""
        symbol = symbol.upper()
        
        if symbol in self.symbol_connections and websocket in self.symbol_connections[symbol]:
            self.symbol_connections[symbol].remove(websocket)
            logger.info(f"Connection disconnected from {symbol}. Remaining: {len(self.symbol_connections[symbol])}")
        
        # Stop stream if no more connections
        if symbol in self.symbol_connections and len(self.symbol_connections[symbol]) == 0:
            await self.stop_symbol_stream(symbol)
            del self.symbol_connections[symbol]
    
    async def send_initial_symbol_data(self, websocket: WebSocket, symbol: str):
        """Send initial data for a specific symbol"""
        try:
            # Get current price data
            ticker_data = await self.binance_service.get_symbol_ticker(f"{symbol}USDT")
            formatted_ticker = self.binance_service.format_market_data(ticker_data)
            
            # Get recent klines (last 100 candles for chart)
            klines = await self.binance_service.get_klines(f"{symbol}USDT", "1m", 100)
            
            initial_data = {
                "type": "initial_symbol_data",
                "symbol": symbol,
                "ticker": formatted_ticker,
                "klines": klines,
                "timestamp": time.time()
            }
            
            await websocket.send_text(json.dumps(initial_data))
            logger.info(f"Sent initial data for {symbol}")
            
        except Exception as e:
            logger.error(f"Error sending initial data for {symbol}: {e}")
    
    async def start_symbol_stream(self, symbol: str):
        """Start dedicated Binance stream for a specific symbol"""
        try:
            # Create dedicated streams for this symbol with more frequent updates
            streams = [
                f"{symbol.lower()}usdt@ticker",      # Price updates
                f"{symbol.lower()}usdt@kline_1m",    # 1-minute klines for candlestick
                f"{symbol.lower()}usdt@miniTicker"   # More frequent mini ticker updates
            ]
            stream_url = f"wss://stream.binance.com:9443/stream?streams={'/'.join(streams)}"
            
            # Start the connection task
            asyncio.create_task(self.symbol_stream_handler(symbol, stream_url))
            
            # Start Bloomberg-level 200ms broadcast timer
            asyncio.create_task(self.bloomberg_timer(symbol))
            
            logger.info(f"Started dedicated Binance stream for {symbol} with 200ms Bloomberg timer")
            
        except Exception as e:
            logger.error(f"Error starting stream for {symbol}: {e}")
    
    async def symbol_stream_handler(self, symbol: str, stream_url: str):
        """Handle incoming Binance WebSocket messages for specific symbol"""
        while symbol in self.symbol_connections and len(self.symbol_connections[symbol]) > 0:
            try:
                async with websockets.connect(stream_url) as websocket:
                    self.binance_connections[symbol] = websocket
                    logger.info(f"Connected to Binance stream for {symbol}")
                    
                    async for message in websocket:
                        data = json.loads(message)
                        await self.process_symbol_message(symbol, data)
                        
            except websockets.exceptions.ConnectionClosed:
                logger.warning(f"Binance stream closed for {symbol}, reconnecting...")
                await asyncio.sleep(0.5)  # Quick reconnect
            except Exception as e:
                logger.error(f"Error in {symbol} stream: {e}")
                await asyncio.sleep(1)
    
    async def bloomberg_timer(self, symbol: str):
        """Bloomberg terminal-level 200ms update timer - creates NEW 200ms candles"""
        logger.info(f"Started Bloomberg timer for {symbol} (200ms NEW candles)")
        
        # Initialize candle history for this symbol
        if symbol not in self.symbol_klines:
            self.symbol_klines[symbol] = []
        
        candle_counter = 0
        last_price = None
        
        while symbol in self.symbol_connections and len(self.symbol_connections[symbol]) > 0:
            try:
                # Get the latest data we have
                price_data = self.symbol_data.get(symbol)
                
                if price_data:
                    current_time = time.time()
                    current_price = price_data['price']
                    current_timestamp = int(current_time * 1000)  # JavaScript timestamp
                    
                    # Update price data
                    price_data['timestamp'] = current_time
                    price_data['update_count'] = price_data.get('update_count', 0) + 1
                    
                    # Broadcast current price data
                    await self.broadcast_to_symbol(symbol, "price_update", price_data)
                    
                    # ========== CREATE NEW 200MS CANDLES ==========
                    # Each 200ms interval gets its own candle like real trading platforms
                    candle_counter += 1
                    
                    # Calculate 200ms candle time window
                    candle_open_time = current_timestamp - 200  # 200ms ago
                    candle_close_time = current_timestamp
                    
                    # Determine open price (previous candle's close or current if first)
                    if last_price is None:
                        last_price = current_price
                    
                    open_price = last_price
                    close_price = current_price
                    
                    # Use actual market data without any artificial manipulation
                    high_price = max(open_price, close_price)
                    low_price = min(open_price, close_price)
                    
                    # Create new 200ms candle
                    new_candle = {
                        'symbol': symbol,
                        'open_time': candle_open_time,
                        'close_time': candle_close_time,
                        'open': open_price,
                        'high': high_price,
                        'low': low_price,
                        'close': close_price,
                        'volume': price_data.get('volume_24h', 0) / 300,  # Distribute volume across 200ms periods
                        'is_closed': True,  # 200ms candle is immediately closed
                        'timestamp': current_time,
                        'candle_id': candle_counter,
                        'interval': '200ms',
                        'is_live': False,  # These are completed 200ms candles
                        'bloomberg_candle': True,
                        'price_change': close_price - open_price,
                        'price_change_percent': ((close_price - open_price) / open_price) * 100 if open_price > 0 else 0
                    }
                    
                    # Add to candle history (keep last 600 candles = 120 seconds = 2 minutes of 200ms candles)
                    if not isinstance(self.symbol_klines[symbol], list):
                        self.symbol_klines[symbol] = []
                    
                    self.symbol_klines[symbol].append(new_candle)
                    
                    # Keep only last 600 candles (2 minutes of 200ms data)
                    if len(self.symbol_klines[symbol]) > 600:
                        self.symbol_klines[symbol] = self.symbol_klines[symbol][-600:]
                    
                    # Broadcast new 200ms candle
                    await self.broadcast_to_symbol(symbol, "new_200ms_candle", new_candle)
                    
                    # Broadcast entire candle history for chart updates (2 minutes of data)
                    candle_history = {
                        'symbol': symbol,
                        'candles': self.symbol_klines[symbol],  # All candles for 2-minute chart
                        'timestamp': current_time,
                        'total_candles': len(self.symbol_klines[symbol]),
                        'interval': '200ms',
                        'candle_type': 'bloomberg_series',
                        'time_window': '2_minutes'
                    }
                    
                    await self.broadcast_to_symbol(symbol, "candle_history", candle_history)
                    
                    # ========== LIVE PRICE TICK FOR REAL-TIME UPDATES ==========
                    live_tick = {
                        'symbol': symbol,
                        'price': current_price,
                        'timestamp': current_timestamp,
                        'volume': price_data.get('volume_24h', 0),
                        'tick_id': price_data['update_count'],
                        'candle_id': candle_counter,
                        'is_bloomberg_tick': True
                    }
                    
                    # Broadcast live tick for immediate price updates
                    await self.broadcast_to_symbol(symbol, "live_tick", live_tick)
                
                    # ========== MINI-TICK FOR SMOOTH ANIMATION ==========
                    mini_tick = {
                        'symbol': symbol,
                        'price': current_price,
                        'timestamp': current_timestamp,
                        'volume': price_data.get('volume_24h', 0),
                        'tick_id': price_data['update_count'],
                        'candle_id': candle_counter,
                        'progress_ms': 200,  # Each tick represents 200ms
                        'price_change': close_price - open_price,
                        'is_bloomberg_tick': True
                    }
                    
                    # Broadcast mini-tick for ultra-smooth movement
                    await self.broadcast_to_symbol(symbol, "mini_tick", mini_tick)
                    
                    # Update last price for next candle
                    last_price = current_price
                    
                    logger.debug(f"Created 200ms candle #{candle_counter} for {symbol}: {open_price:.6f} -> {close_price:.6f}")
                
                # Bloomberg terminal speed: 200ms (5 updates per second)
                await asyncio.sleep(0.2)
                
            except Exception as e:
                logger.error(f"Error in Bloomberg timer for {symbol}: {e}")
                await asyncio.sleep(0.2)
        
        logger.info(f"Stopped Bloomberg timer for {symbol}")

    async def process_symbol_message(self, symbol: str, data: dict):
        """Process incoming Binance messages for specific symbol"""
        try:
            if 'stream' not in data or 'data' not in data:
                return
            
            stream_name = data['stream']
            stream_data = data['data']
            
            if '@ticker' in stream_name or '@miniTicker' in stream_name:
                # Price ticker update (both full ticker and mini ticker)
                await self.handle_ticker_update(symbol, stream_data)
            elif '@kline' in stream_name:
                # Kline update
                await self.handle_kline_update(symbol, stream_data)
                
        except Exception as e:
            logger.error(f"Error processing {symbol} message: {e}")
    
    async def handle_ticker_update(self, symbol: str, ticker_data: dict):
        """Handle price ticker updates - store data for Bloomberg timer"""
        try:
            price_update = {
                'symbol': symbol,
                'price': float(ticker_data.get('c', 0)),
                'change_24h': float(ticker_data.get('P', 0)),
                'volume_24h': float(ticker_data.get('v', 0)),
                'high_24h': float(ticker_data.get('h', 0)),
                'low_24h': float(ticker_data.get('l', 0)),
                'timestamp': time.time(),
                'update_count': 0
            }
            
            # Store the latest data - Bloomberg timer will broadcast it
            self.symbol_data[symbol] = price_update
            
        except Exception as e:
            logger.error(f"Error handling ticker for {symbol}: {e}")

    async def handle_kline_update(self, symbol: str, kline_data: dict):
        """Handle kline (candlestick) updates - store data for Bloomberg timer"""
        try:
            kline = kline_data.get('k', {})
            if not kline:
                return
            
            kline_update = {
                'symbol': symbol,
                'open_time': int(kline.get('t', 0)),
                'close_time': int(kline.get('T', 0)),
                'open': float(kline.get('o', 0)),
                'high': float(kline.get('h', 0)),
                'low': float(kline.get('l', 0)),
                'close': float(kline.get('c', 0)),
                'volume': float(kline.get('v', 0)),
                'is_closed': kline.get('x', False),  # True if this kline is closed
                'timestamp': time.time(),
                'update_count': 0
            }
            
            # Store the latest data - Bloomberg timer will broadcast it
            self.symbol_klines[symbol] = kline_update
            
        except Exception as e:
            logger.error(f"Error handling kline for {symbol}: {e}")
    
    async def broadcast_to_symbol(self, symbol: str, update_type: str, data: dict):
        """Broadcast updates to all connections for a symbol"""
        if symbol not in self.symbol_connections:
            return
        
        message = {
            "type": update_type,
            "symbol": symbol,
            "data": data,
            "timestamp": time.time()
        }
        
        # Send to all connected clients for this symbol
        disconnected = []
        for websocket in self.symbol_connections[symbol].copy():
            try:
                await websocket.send_text(json.dumps(message))
            except WebSocketDisconnect:
                disconnected.append(websocket)
            except Exception as e:
                logger.error(f"Error broadcasting to {symbol}: {e}")
                disconnected.append(websocket)
        
        # Remove disconnected clients
        for ws in disconnected:
            await self.disconnect_symbol(ws, symbol)
    
    async def stop_symbol_stream(self, symbol: str):
        """Stop Binance stream for a specific symbol"""
        if symbol in self.binance_connections and self.binance_connections[symbol]:
            try:
                await self.binance_connections[symbol].close()
            except:
                pass
            self.binance_connections[symbol] = None
            logger.info(f"Stopped Binance stream for {symbol}")
        
        # Clean up data
        self.symbol_data.pop(symbol, None)
        self.symbol_klines.pop(symbol, None)

# Global instance for individual crypto WebSocket management
individual_crypto_ws_manager = IndividualCryptoWebSocketManager() 