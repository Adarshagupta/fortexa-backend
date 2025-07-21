import httpx
import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import json
import hashlib
import time
from urllib.parse import urlencode
from app.core.logger import logger
from app.core.config import settings

class ZerodhaAPIService:
    """
    Service for fetching portfolio data from Zerodha Kite Connect API
    Supports Indian stock market data and portfolio synchronization
    """
    
    def __init__(self):
        self.base_url = "https://api.kite.trade"
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

    def _get_headers(self, access_token: str) -> Dict[str, str]:
        """Get authorization headers for Kite API"""
        return {
            "Authorization": f"token {access_token}",
            "X-Kite-Version": "3",
            "User-Agent": "Fortexa-Trading-App/1.0"
        }

    async def get_profile(self, access_token: str) -> Dict[str, Any]:
        """
        Get user profile information
        """
        try:
            session = await self.get_session()
            response = await session.get(
                f"{self.base_url}/user/profile",
                headers=self._get_headers(access_token)
            )
            response.raise_for_status()
            
            data = response.json()
            logger.info("Successfully fetched Zerodha user profile")
            return data
            
        except httpx.HTTPError as e:
            logger.error(f"Failed to fetch Zerodha profile: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error fetching Zerodha profile: {e}")
            raise

    async def get_holdings(self, access_token: str) -> List[Dict[str, Any]]:
        """
        Get user's stock holdings
        """
        try:
            session = await self.get_session()
            response = await session.get(
                f"{self.base_url}/portfolio/holdings",
                headers=self._get_headers(access_token)
            )
            response.raise_for_status()
            
            data = response.json()
            holdings = data.get('data', [])
            
            logger.info(f"Successfully fetched {len(holdings)} Zerodha holdings")
            return holdings
            
        except httpx.HTTPError as e:
            logger.error(f"Failed to fetch Zerodha holdings: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error fetching Zerodha holdings: {e}")
            raise

    async def get_positions(self, access_token: str) -> Dict[str, Any]:
        """
        Get user's current positions (day + net)
        """
        try:
            session = await self.get_session()
            response = await session.get(
                f"{self.base_url}/portfolio/positions",
                headers=self._get_headers(access_token)
            )
            response.raise_for_status()
            
            data = response.json()
            logger.info("Successfully fetched Zerodha positions")
            return data
            
        except httpx.HTTPError as e:
            logger.error(f"Failed to fetch Zerodha positions: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error fetching Zerodha positions: {e}")
            raise

    async def get_instruments(self, exchange: str = "NSE") -> List[Dict[str, Any]]:
        """
        Get instruments list for a specific exchange
        Exchange options: NSE, BSE, NFO, BFO, CDS, MCX
        """
        try:
            session = await self.get_session()
            response = await session.get(f"https://api.kite.trade/instruments/{exchange}")
            response.raise_for_status()
            
            # Parse CSV response
            csv_data = response.text
            lines = csv_data.strip().split('\n')
            headers = lines[0].split(',')
            
            instruments = []
            for line in lines[1:]:
                values = line.split(',')
                if len(values) == len(headers):
                    instrument = dict(zip(headers, values))
                    instruments.append(instrument)
            
            logger.info(f"Successfully fetched {len(instruments)} instruments for {exchange}")
            return instruments
            
        except httpx.HTTPError as e:
            logger.error(f"Failed to fetch Zerodha instruments: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error fetching Zerodha instruments: {e}")
            raise

    async def get_quote(self, instruments: List[str], access_token: str) -> Dict[str, Any]:
        """
        Get real-time quotes for instruments
        instruments: List of instrument tokens or trading symbols like ["NSE:INFY", "BSE:SENSEX"]
        """
        try:
            session = await self.get_session()
            
            # Join instruments with comma
            instruments_str = ','.join(instruments)
            
            response = await session.get(
                f"{self.base_url}/quote",
                params={"i": instruments_str},
                headers=self._get_headers(access_token)
            )
            response.raise_for_status()
            
            data = response.json()
            logger.info(f"Successfully fetched quotes for {len(instruments)} instruments")
            return data
            
        except httpx.HTTPError as e:
            logger.error(f"Failed to fetch Zerodha quotes: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error fetching Zerodha quotes: {e}")
            raise

    def format_stock_data(self, holding: Dict[str, Any], quote_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Format Zerodha holding data to standardized format
        """
        try:
            # Get current price from quote data or use last_price from holding
            current_price = holding.get('last_price', 0.0)
            if quote_data and 'last_price' in quote_data:
                current_price = quote_data['last_price']
            
            formatted_data = {
                "symbol": holding.get('tradingsymbol', ''),
                "name": holding.get('trading_symbol', holding.get('tradingsymbol', '')),
                "exchange": holding.get('exchange', 'NSE'),
                "instrument_token": holding.get('instrument_token', ''),
                "isin": holding.get('isin', ''),
                "product": holding.get('product', 'CNC'),
                "quantity": holding.get('quantity', 0),
                "t1_quantity": holding.get('t1_quantity', 0),
                "realised_quantity": holding.get('realised_quantity', 0),
                "average_price": holding.get('average_price', 0.0),
                "current_price": current_price,
                "last_price": holding.get('last_price', 0.0),
                "pnl": holding.get('pnl', 0.0),
                "day_change": holding.get('day_change', 0.0),
                "day_change_percentage": holding.get('day_change_percentage', 0.0),
                "total_value": (holding.get('quantity', 0) * current_price),
                "total_cost": (holding.get('quantity', 0) * holding.get('average_price', 0.0)),
                "last_updated": datetime.now().isoformat()
            }
            
            return formatted_data
            
        except Exception as e:
            logger.error(f"Failed to format Zerodha stock data: {e}")
            raise

    async def sync_portfolio(self, access_token: str, portfolio_id: str, db) -> Dict[str, Any]:
        """
        Sync portfolio data from Zerodha account
        """
        try:
            logger.info(f"Starting Zerodha portfolio sync for portfolio_id: {portfolio_id}")
            
            # Get holdings data
            holdings = await self.get_holdings(access_token)
            logger.info(f"Got {len(holdings)} holdings from Zerodha")
            
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
            
            logger.info(f"Successfully synced {synced_holdings} holdings from Zerodha")
            
            # Recalculate portfolio totals (reuse from Binance service)
            await self._recalculate_portfolio_totals(portfolio_id, db)
            await self._recalculate_allocations(portfolio_id, db)
            
            return {
                'synced_holdings': synced_holdings,
                'updated_assets': updated_assets
            }
            
        except Exception as e:
            logger.error(f"Failed to sync Zerodha portfolio: {str(e)}")
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
            
            logger.info(f"Updated Zerodha portfolio totals: value=₹{total_value:.2f}, cost=₹{total_cost:.2f}, gain_loss=₹{total_gain_loss:.2f} ({total_gain_loss_percent:.2f}%)")
            
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
            
            logger.info(f"Updated allocations for {len(holdings)} Zerodha holdings")
            
        except Exception as e:
            logger.error(f"Failed to recalculate allocations: {str(e)}")
            raise

# Global instance
zerodha_service = ZerodhaAPIService() 