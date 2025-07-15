import httpx
import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import json
import hmac
import hashlib
import time
from urllib.parse import urlencode
from app.core.logger import logger
from app.core.config import settings
from app.services.cache_service import cache_service

class BinanceAPIService:
    """
    Service for fetching market data from Binance API
    Uses public endpoints - no API key required
    """
    
    def __init__(self):
        self.base_url = "https://api.binance.com"
        self.testnet_base_url = "https://testnet.binance.vision"
        self.timeout = 10.0
        self.session = None
        
    async def get_session(self) -> httpx.AsyncClient:
        """Get or create HTTP session"""
        if self.session is None:
            self.session = httpx.AsyncClient(
                timeout=self.timeout,
                headers={
                    "User-Agent": "Fortexa-Trading-App/1.0"
                }
            )
        return self.session
    
    async def close_session(self):
        """Close HTTP session"""
        if self.session:
            await self.session.aclose()
            self.session = None
    
    async def get_24hr_ticker_stats(self) -> List[Dict[str, Any]]:
        """
        Get 24hr ticker price change statistics for all symbols
        https://binance-docs.github.io/apidocs/spot/en/#24hr-ticker-price-change-statistics
        """
        try:
            session = await self.get_session()
            response = await session.get(f"{self.base_url}/api/v3/ticker/24hr")
            response.raise_for_status()
            
            data = response.json()
            logger.info(f"Successfully fetched 24hr ticker data for {len(data)} symbols")
            return data
        except httpx.HTTPError as e:
            logger.error(f"Failed to fetch 24hr ticker stats: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error fetching 24hr ticker stats: {e}")
            raise
    
    async def get_symbol_ticker(self, symbol: str) -> Dict[str, Any]:
        """
        Get ticker information for a specific symbol
        """
        try:
            # Check cache first
            cached_data = cache_service.get_price_data(symbol.upper())
            if cached_data:
                logger.info(f"Retrieved ticker data for {symbol} from cache")
                return cached_data
            
            session = await self.get_session()
            response = await session.get(
                f"{self.base_url}/api/v3/ticker/24hr",
                params={"symbol": symbol.upper()}
            )
            response.raise_for_status()
            
            data = response.json()
            
            # Cache the result
            cache_service.set_price_data(symbol.upper(), data)
            
            logger.info(f"Successfully fetched ticker data for {symbol}")
            return data
        except httpx.HTTPError as e:
            logger.error(f"Failed to fetch ticker for {symbol}: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error fetching ticker for {symbol}: {e}")
            raise
    
    async def get_top_cryptocurrencies(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Get top cryptocurrencies by volume (using USDT pairs)
        """
        try:
            # Check cache first
            cached_data = cache_service.get_top_cryptocurrencies(limit)
            if cached_data:
                logger.info(f"Retrieved top {len(cached_data)} cryptocurrencies from cache")
                return cached_data
            
            # Get all 24hr ticker data
            all_tickers = await self.get_24hr_ticker_stats()
            
            # Filter for USDT pairs only (most liquid)
            usdt_pairs = [
                ticker for ticker in all_tickers 
                if ticker['symbol'].endswith('USDT') and 
                float(ticker['volume']) > 0
            ]
            
            # Sort by volume (descending)
            usdt_pairs.sort(key=lambda x: float(x['volume']), reverse=True)
            
            # Return top cryptocurrencies
            top_cryptos = usdt_pairs[:limit]
            
            # Cache the result
            cache_service.set_top_cryptocurrencies(limit, top_cryptos)
            
            logger.info(f"Successfully fetched top {len(top_cryptos)} cryptocurrencies")
            return top_cryptos
            
        except Exception as e:
            logger.error(f"Failed to fetch top cryptocurrencies: {e}")
            raise
    
    async def get_current_prices(self, symbols: List[str]) -> Dict[str, float]:
        """
        Get current prices for multiple symbols
        """
        try:
            session = await self.get_session()
            
            # Format symbols for Binance API
            formatted_symbols = [f"{symbol.upper()}USDT" for symbol in symbols]
            
            # Get price data
            prices = {}
            for symbol in formatted_symbols:
                try:
                    response = await session.get(
                        f"{self.base_url}/api/v3/ticker/price",
                        params={"symbol": symbol}
                    )
                    response.raise_for_status()
                    data = response.json()
                    
                    # Extract base symbol (remove USDT)
                    base_symbol = symbol.replace('USDT', '')
                    prices[base_symbol] = float(data['price'])
                    
                except httpx.HTTPError as e:
                    logger.warning(f"Failed to fetch price for {symbol}: {e}")
                    continue
                    
            logger.info(f"Successfully fetched prices for {len(prices)} symbols")
            return prices
            
        except Exception as e:
            logger.error(f"Failed to fetch current prices: {e}")
            raise
    
    async def get_klines(self, symbol: str, interval: str = "1d", limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get historical kline/candlestick data
        """
        try:
            # Check cache first
            cached_data = cache_service.get_historical_data(symbol.upper(), interval, limit)
            if cached_data:
                logger.info(f"Retrieved {len(cached_data)} klines for {symbol} from cache")
                return cached_data
            
            session = await self.get_session()
            response = await session.get(
                f"{self.base_url}/api/v3/klines",
                params={
                    "symbol": symbol.upper(),
                    "interval": interval,
                    "limit": limit
                }
            )
            response.raise_for_status()
            
            raw_data = response.json()
            
            # Transform raw kline data to structured format
            klines = []
            for kline in raw_data:
                klines.append({
                    "open_time": datetime.fromtimestamp(kline[0] / 1000),
                    "open": float(kline[1]),
                    "high": float(kline[2]),
                    "low": float(kline[3]),
                    "close": float(kline[4]),
                    "volume": float(kline[5]),
                    "close_time": datetime.fromtimestamp(kline[6] / 1000),
                    "quote_volume": float(kline[7]),
                    "trades": int(kline[8])
                })
            
            # Cache the result
            cache_service.set_historical_data(symbol.upper(), interval, limit, klines)
            
            logger.info(f"Successfully fetched {len(klines)} klines for {symbol}")
            return klines
            
        except httpx.HTTPError as e:
            logger.error(f"Failed to fetch klines for {symbol}: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error fetching klines for {symbol}: {e}")
            raise
    
    async def get_order_book(self, symbol: str, limit: int = 20) -> Dict[str, Any]:
        """
        Get order book (market depth) for a symbol
        """
        try:
            session = await self.get_session()
            response = await session.get(
                f"{self.base_url}/api/v3/depth",
                params={
                    "symbol": symbol.upper(),
                    "limit": limit
                }
            )
            response.raise_for_status()
            
            data = response.json()
            
            # Format order book data
            formatted_data = {
                "symbol": symbol.upper(),
                "last_update_id": data["lastUpdateId"],
                "bids": [[float(price), float(quantity)] for price, quantity in data["bids"]],
                "asks": [[float(price), float(quantity)] for price, quantity in data["asks"]]
            }
            
            logger.info(f"Successfully fetched order book for {symbol}")
            return formatted_data
            
        except httpx.HTTPError as e:
            logger.error(f"Failed to fetch order book for {symbol}: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error fetching order book for {symbol}: {e}")
            raise
    
    async def get_exchange_info(self) -> Dict[str, Any]:
        """
        Get exchange information (symbols, trading rules, etc.)
        """
        try:
            session = await self.get_session()
            response = await session.get(f"{self.base_url}/api/v3/exchangeInfo")
            response.raise_for_status()
            
            data = response.json()
            logger.info("Successfully fetched exchange information")
            return data
            
        except httpx.HTTPError as e:
            logger.error(f"Failed to fetch exchange info: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error fetching exchange info: {e}")
            raise
    
    def format_market_data(self, ticker_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Format Binance ticker data to standardized market data format
        """
        try:
            # Extract base symbol (remove USDT)
            symbol = ticker_data['symbol'].replace('USDT', '')
            
            formatted_data = {
                "symbol": symbol,
                "name": symbol,  # We'll need to map this to full names later
                "current_price": float(ticker_data['lastPrice']),
                "price_change_24h": float(ticker_data['priceChange']),
                "price_change_percentage_24h": float(ticker_data['priceChangePercent']),
                "volume_24h": float(ticker_data['volume']),
                "quote_volume_24h": float(ticker_data['quoteVolume']),
                "high_24h": float(ticker_data['highPrice']),
                "low_24h": float(ticker_data['lowPrice']),
                "open_price": float(ticker_data['openPrice']),
                "prev_close_price": float(ticker_data['prevClosePrice']),
                "bid_price": float(ticker_data['bidPrice']),
                "ask_price": float(ticker_data['askPrice']),
                "last_updated": datetime.now().isoformat()
            }
            
            return formatted_data
            
        except Exception as e:
            logger.error(f"Failed to format market data: {e}")
            raise
    
    async def get_market_summary(self) -> Dict[str, Any]:
        """
        Get market summary with total market cap, volume, etc.
        """
        try:
            # Check cache first
            cached_summary = cache_service.get_market_summary()
            if cached_summary:
                logger.info("Retrieved market summary from cache")
                return cached_summary
            
            # Get top cryptocurrencies data
            top_cryptos = await self.get_top_cryptocurrencies(100)
            
            # Calculate market statistics
            total_volume_24h = sum(float(crypto['quoteVolume']) for crypto in top_cryptos)
            active_pairs = len(top_cryptos)
            
            # Get price change statistics
            positive_changes = [crypto for crypto in top_cryptos if float(crypto['priceChangePercent']) > 0]
            negative_changes = [crypto for crypto in top_cryptos if float(crypto['priceChangePercent']) < 0]
            
            market_change_24h = sum(float(crypto['priceChangePercent']) for crypto in top_cryptos) / len(top_cryptos)
            
            summary = {
                "total_volume_24h": total_volume_24h,
                "active_cryptocurrencies": active_pairs,
                "market_cap_change_24h": market_change_24h,
                "gainers_count": len(positive_changes),
                "losers_count": len(negative_changes),
                "neutral_count": active_pairs - len(positive_changes) - len(negative_changes),
                "top_gainer": max(top_cryptos, key=lambda x: float(x['priceChangePercent'])),
                "top_loser": min(top_cryptos, key=lambda x: float(x['priceChangePercent'])),
                "highest_volume": max(top_cryptos, key=lambda x: float(x['quoteVolume']))
            }
            
            # Cache the result
            cache_service.set_market_summary(summary)
            
            logger.info("Successfully calculated market summary")
            return summary
            
        except Exception as e:
            logger.error(f"Failed to get market summary: {e}")
            raise

    # Private API methods for authenticated requests
    
    def _get_base_url(self, testnet: bool = False) -> str:
        """Get base URL based on testnet flag"""
        return self.testnet_base_url if testnet else self.base_url
    
    def _generate_signature(self, query_string: str, secret_key: str) -> str:
        """Generate signature for authenticated requests"""
        return hmac.new(
            secret_key.encode('utf-8'),
            query_string.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
    
    def _get_timestamp(self) -> int:
        """Get current timestamp in milliseconds"""
        return int(time.time() * 1000)
    

    
    async def get_account_info(self, api_key: str, secret_key: str, testnet: bool = False) -> Dict[str, Any]:
        """
        Get account information including balances
        """
        try:
            base_url = self._get_base_url(testnet)
            session = await self.get_session()
            
            # Create query parameters
            timestamp = self._get_timestamp()
            query_params = {
                'timestamp': timestamp
            }
            
            # Create query string and signature
            query_string = urlencode(query_params)
            signature = self._generate_signature(query_string, secret_key)
            
            # Add signature to query string
            query_string += f"&signature={signature}"
            
            # Make request to account endpoint
            response = await session.get(
                f"{base_url}/api/v3/account?{query_string}",
                headers={
                    'X-MBX-APIKEY': api_key,
                    'User-Agent': 'Fortexa-Trading-App/1.0'
                }
            )
            
            response.raise_for_status()
            account_data = response.json()
            
            logger.info(f"Successfully fetched account info (testnet: {testnet})")
            return account_data
            
        except httpx.HTTPError as e:
            logger.error(f"Failed to fetch account info: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error fetching account info: {e}")
            raise
    
    async def _recalculate_portfolio_totals(self, portfolio_id: str, db) -> None:
        """
        Recalculate and update portfolio totals based on current holdings
        """
        try:
            # Get all holdings for this portfolio
            holdings = await db.portfolioholding.find_many(
                where={'portfolioId': portfolio_id}
            )
            
            # Calculate totals
            total_value = 0.0
            total_cost = 0.0
            total_gain_loss = 0.0
            
            for holding in holdings:
                total_value += holding.totalValue or 0.0
                total_cost += holding.totalCost or 0.0
                total_gain_loss += holding.gainLoss or 0.0
            
            # Calculate percentage
            total_gain_loss_percent = 0.0
            if total_cost > 0:
                total_gain_loss_percent = (total_gain_loss / total_cost) * 100
            
            # Update portfolio totals
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
            
            logger.info(f"Updated portfolio totals: value=${total_value:.2f}, cost=${total_cost:.2f}, gain_loss=${total_gain_loss:.2f} ({total_gain_loss_percent:.2f}%)")
            
        except Exception as e:
            logger.error(f"Failed to recalculate portfolio totals: {str(e)}")
            raise

    async def _recalculate_allocations(self, portfolio_id: str, db) -> None:
        """
        Recalculate allocation percentages for all holdings in a portfolio
        """
        try:
            # Get portfolio to get total value
            portfolio = await db.portfolio.find_unique(
                where={'id': portfolio_id}
            )
            
            if not portfolio or portfolio.totalValue == 0:
                logger.warning(f"Portfolio {portfolio_id} has zero total value, setting all allocations to 0")
                await db.portfolioholding.update_many(
                    where={'portfolioId': portfolio_id},
                    data={'allocation': 0.0}
                )
                return
            
            # Get all holdings for this portfolio
            holdings = await db.portfolioholding.find_many(
                where={'portfolioId': portfolio_id}
            )
            
            # Update allocation for each holding
            for holding in holdings:
                allocation = (holding.totalValue / portfolio.totalValue) * 100 if portfolio.totalValue > 0 else 0.0
                await db.portfolioholding.update(
                    where={'id': holding.id},
                    data={'allocation': allocation}
                )
            
            logger.info(f"Updated allocations for {len(holdings)} holdings in portfolio {portfolio_id}")
            
        except Exception as e:
            logger.error(f"Failed to recalculate allocations: {str(e)}")
            raise

    async def sync_portfolio(self, api_key: str, secret_key: str, testnet: bool, portfolio_id: str, db) -> Dict[str, Any]:
        """
        Sync portfolio data from Binance account
        """
        try:
            from prisma import Prisma
            
            logger.info(f"Starting portfolio sync for portfolio_id: {portfolio_id}, testnet: {testnet}")
            
            # Get account info
            account_data = await self.get_account_info(api_key, secret_key, testnet)
            logger.info(f"Got account data with {len(account_data.get('balances', []))} balances")
            
            synced_holdings = 0
            updated_assets = 0
            
            # Process balances
            balances = account_data.get('balances', [])
            logger.info(f"Processing {len(balances)} balances")
            
            for balance in balances:
                free_balance = float(balance['free'])
                locked_balance = float(balance['locked'])
                total_balance = free_balance + locked_balance
                
                asset_symbol = balance['asset']
                logger.info(f"Processing {asset_symbol}: free={free_balance}, locked={locked_balance}, total={total_balance}")
                
                # Skip zero balances
                if total_balance <= 0:
                    logger.info(f"Skipping {asset_symbol} due to zero balance")
                    continue
                
                # Get or create asset
                asset = await db.asset.find_first(
                    where={'symbol': asset_symbol}
                )
                
                if not asset:
                    # Create new asset
                    try:
                        # Get current price for the asset
                        current_price = 0.0
                        if asset_symbol != 'USDT':
                            try:
                                ticker_data = await self.get_symbol_ticker(f"{asset_symbol}USDT")
                                current_price = float(ticker_data['lastPrice'])
                            except:
                                # If we can't get price, set to 0
                                current_price = 0.0
                        else:
                            current_price = 1.0  # USDT is always 1
                        
                        asset = await db.asset.create(
                            data={
                                'symbol': asset_symbol,
                                'name': asset_symbol,  # We'll update this later with proper names
                                'type': 'CRYPTOCURRENCY',
                                'currentPrice': current_price,
                                'priceUpdatedAt': datetime.now()
                            }
                        )
                        updated_assets += 1
                        
                    except Exception as e:
                        logger.error(f"Failed to create asset {asset_symbol}: {e}")
                        continue
                
                # Get current price
                current_price = asset.currentPrice
                if asset_symbol != 'USDT' and current_price == 0:
                    try:
                        ticker_data = await self.get_symbol_ticker(f"{asset_symbol}USDT")
                        current_price = float(ticker_data['lastPrice'])
                        
                        # Update asset price
                        await db.asset.update(
                            where={'id': asset.id},
                            data={
                                'currentPrice': current_price,
                                'priceUpdatedAt': datetime.now()
                            }
                        )
                        
                    except:
                        current_price = 0.0
                
                # Calculate values
                total_value = total_balance * current_price
                
                # Check if holding already exists
                existing_holding = await db.portfolioholding.find_first(
                    where={
                        'portfolioId': portfolio_id,
                        'assetId': asset.id
                    }
                )
                
                if existing_holding:
                    # Update existing holding
                    await db.portfolioholding.update(
                        where={'id': existing_holding.id},
                        data={
                            'quantity': total_balance,
                            'currentPrice': current_price,
                            'totalValue': total_value,
                            'gainLoss': total_value - existing_holding.totalCost,
                            'gainLossPercent': ((total_value - existing_holding.totalCost) / existing_holding.totalCost) * 100 if existing_holding.totalCost > 0 else 0,
                            'allocation': 0.0,  # Will be calculated later
                            'updatedAt': datetime.now()
                        }
                    )
                else:
                    # Create new holding
                    await db.portfolioholding.create(
                        data={
                            'portfolioId': portfolio_id,
                            'assetId': asset.id,
                            'symbol': asset_symbol,
                            'quantity': total_balance,
                            'averagePrice': current_price,  # Assume current price as average
                            'currentPrice': current_price,
                            'totalValue': total_value,
                            'totalCost': total_value,  # Assume current value as cost
                            'gainLoss': 0.0,
                            'gainLossPercent': 0.0,
                            'allocation': 0.0  # Will be calculated later
                        }
                    )
                
                synced_holdings += 1
                logger.info(f"Successfully synced holding for {asset_symbol}: quantity={total_balance}, value={total_value}")
                
            logger.info(f"Successfully synced portfolio from Binance: {synced_holdings} holdings, {updated_assets} assets")
            
            # Recalculate portfolio totals after syncing holdings
            await self._recalculate_portfolio_totals(portfolio_id, db)
            
            # Update allocations for all holdings
            await self._recalculate_allocations(portfolio_id, db)
            
            return {
                'synced_holdings': synced_holdings,
                'updated_assets': updated_assets
            }
            
        except Exception as e:
            logger.error(f"Failed to sync portfolio from Binance: {str(e)}")
            logger.error(f"Exception type: {type(e).__name__}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            raise

# Global instance
binance_service = BinanceAPIService() 