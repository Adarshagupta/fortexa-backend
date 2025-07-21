import httpx
import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import json
import jwt
import pyotp
import time
from app.core.logger import logger
from app.core.config import settings

class AngelOneAPIService:
    """
    Service for fetching portfolio data from Angel One SmartAPI
    Supports Indian stock market data and portfolio synchronization
    """
    
    def __init__(self):
        self.base_url = "https://apiconnect.angelbroking.com"
        self.timeout = 10.0
        self.session = None
        
    async def get_session(self) -> httpx.AsyncClient:
        """Get or create HTTP session"""
        if self.session is None:
            self.session = httpx.AsyncClient(
                timeout=self.timeout,
                headers={
                    "User-Agent": "Fortexa-Trading-App/1.0",
                    "Content-Type": "application/json",
                    "Accept": "application/json"
                }
            )
        return self.session
    
    async def close_session(self):
        """Close HTTP session"""
        if self.session:
            await self.session.aclose()
            self.session = None

    def _get_headers(self, jwt_token: str = None, api_key: str = None) -> Dict[str, str]:
        """Get authorization headers for Angel One API"""
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "Fortexa-Trading-App/1.0"
        }
        
        if jwt_token:
            headers["Authorization"] = f"Bearer {jwt_token}"
        if api_key:
            headers["X-UserType"] = "USER"
            headers["X-SourceID"] = "WEB"
            headers["X-ClientLocalIP"] = "192.168.1.1"
            headers["X-ClientPublicIP"] = "192.168.1.1"
            headers["X-MACAddress"] = "00:00:00:00:00:00"
            headers["X-PrivateKey"] = api_key
            
        return headers

    async def login(self, client_code: str, password: str, totp: str, api_key: str) -> Dict[str, Any]:
        """
        Login to Angel One and get JWT token
        """
        try:
            session = await self.get_session()
            
            login_data = {
                "clientcode": client_code,
                "password": password,
                "totp": totp
            }
            
            response = await session.post(
                f"{self.base_url}/rest/auth/angelbroking/user/v1/loginByPassword",
                headers=self._get_headers(api_key=api_key),
                json=login_data
            )
            response.raise_for_status()
            
            data = response.json()
            logger.info("Successfully logged into Angel One")
            return data
            
        except httpx.HTTPError as e:
            logger.error(f"Failed to login to Angel One: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error logging into Angel One: {e}")
            raise

    async def get_profile(self, jwt_token: str, api_key: str) -> Dict[str, Any]:
        """
        Get user profile information
        """
        try:
            session = await self.get_session()
            response = await session.get(
                f"{self.base_url}/rest/secure/angelbroking/user/v1/getProfile",
                headers=self._get_headers(jwt_token, api_key)
            )
            response.raise_for_status()
            
            data = response.json()
            logger.info("Successfully fetched Angel One user profile")
            return data
            
        except httpx.HTTPError as e:
            logger.error(f"Failed to fetch Angel One profile: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error fetching Angel One profile: {e}")
            raise

    async def get_holdings(self, jwt_token: str, api_key: str) -> List[Dict[str, Any]]:
        """
        Get user's stock holdings
        """
        try:
            session = await self.get_session()
            response = await session.get(
                f"{self.base_url}/rest/secure/angelbroking/portfolio/v1/getHolding",
                headers=self._get_headers(jwt_token, api_key)
            )
            response.raise_for_status()
            
            data = response.json()
            holdings = data.get('data', [])
            
            logger.info(f"Successfully fetched {len(holdings)} Angel One holdings")
            return holdings
            
        except httpx.HTTPError as e:
            logger.error(f"Failed to fetch Angel One holdings: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error fetching Angel One holdings: {e}")
            raise

    async def get_positions(self, jwt_token: str, api_key: str) -> Dict[str, Any]:
        """
        Get user's current positions
        """
        try:
            session = await self.get_session()
            response = await session.get(
                f"{self.base_url}/rest/secure/angelbroking/order/v1/getPosition",
                headers=self._get_headers(jwt_token, api_key)
            )
            response.raise_for_status()
            
            data = response.json()
            logger.info("Successfully fetched Angel One positions")
            return data
            
        except httpx.HTTPError as e:
            logger.error(f"Failed to fetch Angel One positions: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error fetching Angel One positions: {e}")
            raise

    async def get_ltp(self, exchange: str, symboltoken: str, jwt_token: str, api_key: str) -> Dict[str, Any]:
        """
        Get Last Traded Price for a specific instrument
        """
        try:
            session = await self.get_session()
            
            ltp_data = {
                "exchange": exchange,
                "symboltoken": symboltoken
            }
            
            response = await session.post(
                f"{self.base_url}/rest/secure/angelbroking/order/v1/getLTP",
                headers=self._get_headers(jwt_token, api_key),
                json=ltp_data
            )
            response.raise_for_status()
            
            data = response.json()
            logger.info(f"Successfully fetched LTP for {exchange}:{symboltoken}")
            return data
            
        except httpx.HTTPError as e:
            logger.error(f"Failed to fetch Angel One LTP: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error fetching Angel One LTP: {e}")
            raise

    async def get_candle_data(self, exchange: str, symboltoken: str, interval: str, fromdate: str, todate: str, jwt_token: str, api_key: str) -> Dict[str, Any]:
        """
        Get historical candle data
        """
        try:
            session = await self.get_session()
            
            candle_data = {
                "exchange": exchange,
                "symboltoken": symboltoken,
                "interval": interval,
                "fromdate": fromdate,
                "todate": todate
            }
            
            response = await session.post(
                f"{self.base_url}/rest/secure/angelbroking/historical/v1/getCandleData",
                headers=self._get_headers(jwt_token, api_key),
                json=candle_data
            )
            response.raise_for_status()
            
            data = response.json()
            logger.info(f"Successfully fetched candle data for {exchange}:{symboltoken}")
            return data
            
        except httpx.HTTPError as e:
            logger.error(f"Failed to fetch Angel One candle data: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error fetching Angel One candle data: {e}")
            raise

    def format_stock_data(self, holding: Dict[str, Any], ltp_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Format Angel One holding data to standardized format
        """
        try:
            # Get current price from LTP data or use last_price from holding
            current_price = holding.get('ltp', 0.0)
            if ltp_data and 'data' in ltp_data and 'ltp' in ltp_data['data']:
                current_price = ltp_data['data']['ltp']
            
            quantity = holding.get('quantity', 0)
            avg_price = holding.get('averageprice', 0.0)
            total_value = quantity * current_price
            total_cost = quantity * avg_price
            pnl = total_value - total_cost
            
            formatted_data = {
                "symbol": holding.get('tradingsymbol', ''),
                "name": holding.get('symbolname', holding.get('tradingsymbol', '')),
                "exchange": holding.get('exchange', 'NSE'),
                "symboltoken": holding.get('symboltoken', ''),
                "isin": holding.get('isin', ''),
                "product": holding.get('product', 'CNC'),
                "quantity": quantity,
                "authorised_quantity": holding.get('authorisedquantity', 0),
                "t1_quantity": holding.get('t1quantity', 0),
                "average_price": avg_price,
                "current_price": current_price,
                "ltp": holding.get('ltp', 0.0),
                "pnl": pnl,
                "day_change": holding.get('daychange', 0.0),
                "day_change_percentage": holding.get('daychangepercentage', 0.0),
                "total_value": total_value,
                "total_cost": total_cost,
                "last_updated": datetime.now().isoformat()
            }
            
            return formatted_data
            
        except Exception as e:
            logger.error(f"Failed to format Angel One stock data: {e}")
            raise

    async def sync_portfolio(self, jwt_token: str, api_key: str, portfolio_id: str, db) -> Dict[str, Any]:
        """
        Sync portfolio data from Angel One account
        """
        try:
            logger.info(f"Starting Angel One portfolio sync for portfolio_id: {portfolio_id}")
            
            # Get holdings data
            holdings = await self.get_holdings(jwt_token, api_key)
            logger.info(f"Got {len(holdings)} holdings from Angel One")
            
            synced_holdings = 0
            updated_assets = 0
            
            # Process each holding
            for holding in holdings:
                try:
                    quantity = holding.get('quantity', 0)
                    if quantity <= 0:
                        logger.info(f"Skipping {holding.get('tradingsymbol')} due to zero quantity")
                        continue
                    
                    # Format the holding data
                    formatted_data = self.format_stock_data(holding)
                    symbol = formatted_data['symbol']
                    exchange = formatted_data['exchange']
                    full_symbol = f"{exchange}:{symbol}"
                    
                    # Get or create asset
                    asset = await db.asset.find_first(
                        where={'symbol': full_symbol}
                    )
                    
                    if not asset:
                        # Create new stock asset
                        asset = await db.asset.create(
                            data={
                                'symbol': full_symbol,
                                'name': formatted_data['name'],
                                'type': 'STOCK',
                                'description': f"{symbol} stock on {exchange}",
                                'currentPrice': formatted_data['current_price'],
                                'change24h': formatted_data['day_change_percentage'],
                                'priceUpdatedAt': datetime.now()
                            }
                        )
                        updated_assets += 1
                        logger.info(f"Created new stock asset: {full_symbol}")
                    else:
                        # Update existing asset price
                        await db.asset.update(
                            where={'id': asset.id},
                            data={
                                'currentPrice': formatted_data['current_price'],
                                'change24h': formatted_data['day_change_percentage'],
                                'priceUpdatedAt': datetime.now()
                            }
                        )
                    
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
                                'quantity': formatted_data['quantity'],
                                'averagePrice': formatted_data['average_price'],
                                'currentPrice': formatted_data['current_price'],
                                'totalValue': formatted_data['total_value'],
                                'totalCost': formatted_data['total_cost'],
                                'gainLoss': formatted_data['pnl'],
                                'gainLossPercent': (formatted_data['pnl'] / formatted_data['total_cost']) * 100 if formatted_data['total_cost'] > 0 else 0,
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
                                'symbol': full_symbol,
                                'quantity': formatted_data['quantity'],
                                'averagePrice': formatted_data['average_price'],
                                'currentPrice': formatted_data['current_price'],
                                'totalValue': formatted_data['total_value'],
                                'totalCost': formatted_data['total_cost'],
                                'gainLoss': formatted_data['pnl'],
                                'gainLossPercent': (formatted_data['pnl'] / formatted_data['total_cost']) * 100 if formatted_data['total_cost'] > 0 else 0,
                                'allocation': 0.0  # Will be calculated later
                            }
                        )
                    
                    synced_holdings += 1
                    logger.info(f"Successfully synced holding for {full_symbol}: qty={formatted_data['quantity']}, value=₹{formatted_data['total_value']:.2f}")
                    
                except Exception as e:
                    logger.error(f"Failed to sync holding {holding.get('tradingsymbol', 'Unknown')}: {e}")
                    continue
            
            logger.info(f"Successfully synced {synced_holdings} holdings from Angel One")
            
            # Recalculate portfolio totals
            await self._recalculate_portfolio_totals(portfolio_id, db)
            await self._recalculate_allocations(portfolio_id, db)
            
            return {
                'synced_holdings': synced_holdings,
                'updated_assets': updated_assets
            }
            
        except Exception as e:
            logger.error(f"Failed to sync Angel One portfolio: {str(e)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            raise

    async def _recalculate_portfolio_totals(self, portfolio_id: str, db) -> None:
        """
        Recalculate and update portfolio totals based on current holdings
        """
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
            
            logger.info(f"Updated Angel One portfolio totals: value=₹{total_value:.2f}, cost=₹{total_cost:.2f}, gain_loss=₹{total_gain_loss:.2f} ({total_gain_loss_percent:.2f}%)")
            
        except Exception as e:
            logger.error(f"Failed to recalculate portfolio totals: {str(e)}")
            raise

    async def _recalculate_allocations(self, portfolio_id: str, db) -> None:
        """
        Recalculate allocation percentages for all holdings in a portfolio
        """
        try:
            portfolio = await db.portfolio.find_unique(where={'id': portfolio_id})
            
            if not portfolio or portfolio.totalValue == 0:
                await db.portfolioholding.update_many(
                    where={'portfolioId': portfolio_id},
                    data={'allocation': 0.0}
                )
                return
            
            holdings = await db.portfolioholding.find_many(
                where={'portfolioId': portfolio_id}
            )
            
            for holding in holdings:
                allocation = (holding.totalValue / portfolio.totalValue) * 100 if portfolio.totalValue > 0 else 0.0
                await db.portfolioholding.update(
                    where={'id': holding.id},
                    data={'allocation': allocation}
                )
            
            logger.info(f"Updated allocations for {len(holdings)} Angel One holdings")
            
        except Exception as e:
            logger.error(f"Failed to recalculate allocations: {str(e)}")
            raise

    async def sync_portfolio_oauth(self, access_token: str, portfolio_id: str, db) -> Dict[str, Any]:
        """
        Sync portfolio using OAuth access token
        """
        try:
            logger.info("Starting Angel One OAuth portfolio sync")
            
            # Use OAuth token to fetch portfolio data
            # This would use the access token to make API calls to Angel One
            # For now, return a placeholder response
            
            logger.info("Angel One OAuth portfolio sync completed")
            
            return {
                'synced_holdings': 0,
                'updated_assets': 0,
                'status': 'oauth_sync_placeholder'
            }
            
        except Exception as e:
            logger.error(f"OAuth portfolio sync failed: {e}")
            raise

# Global instance
angel_one_service = AngelOneAPIService() 