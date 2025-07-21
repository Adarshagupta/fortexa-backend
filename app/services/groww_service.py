import httpx
import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import json
import time
from app.core.logger import logger
from app.core.config import settings

class GrowwAPIService:
    """
    Service for fetching portfolio data from Groww
    NOTE: Groww has limited public API access
    This service provides a framework for future integration
    """
    
    def __init__(self):
        self.base_url = "https://groww.in"  # Base URL for potential web API
        self.api_base_url = "https://groww.in/v1/api"  # Potential API endpoint
        self.timeout = 10.0
        self.session = None
        
    async def get_session(self) -> httpx.AsyncClient:
        """Get or create HTTP session"""
        if self.session is None:
            self.session = httpx.AsyncClient(
                timeout=self.timeout,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
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

    def _get_headers(self, access_token: str = None) -> Dict[str, str]:
        """Get authorization headers for Groww API"""
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "Fortexa-Trading-App/1.0"
        }
        
        if access_token:
            headers["Authorization"] = f"Bearer {access_token}"
            
        return headers

    async def get_profile(self, access_token: str) -> Dict[str, Any]:
        """
        Get user profile information
        NOTE: This is a placeholder - Groww doesn't have public API
        """
        try:
            logger.warning("Groww API not publicly available - using placeholder implementation")
            
            # Placeholder response
            return {
                "status": "error",
                "message": "Groww API not publicly available",
                "data": None
            }
            
        except Exception as e:
            logger.error(f"Groww profile fetch failed: {e}")
            raise

    async def get_holdings(self, access_token: str) -> List[Dict[str, Any]]:
        """
        Get user's stock holdings
        NOTE: This is a placeholder - Groww doesn't have public API
        """
        try:
            logger.warning("Groww holdings API not publicly available")
            
            # For now, return empty holdings
            # In the future, this could be implemented via:
            # 1. Official Groww API (when available)
            # 2. Web scraping (with user consent)
            # 3. CSV/Excel import functionality
            
            return []
            
        except Exception as e:
            logger.error(f"Failed to fetch Groww holdings: {e}")
            raise

    async def get_mutual_funds(self, access_token: str) -> List[Dict[str, Any]]:
        """
        Get user's mutual fund holdings
        NOTE: Placeholder for future implementation
        """
        try:
            logger.warning("Groww mutual funds API not available")
            return []
            
        except Exception as e:
            logger.error(f"Failed to fetch Groww mutual funds: {e}")
            raise

    def format_stock_data(self, holding: Dict[str, Any]) -> Dict[str, Any]:
        """
        Format Groww holding data to standardized format
        This will be implemented when API becomes available
        """
        try:
            # Placeholder formatting - adapt based on actual Groww API response
            formatted_data = {
                "symbol": holding.get('symbol', ''),
                "name": holding.get('name', ''),
                "exchange": holding.get('exchange', 'NSE'),
                "isin": holding.get('isin', ''),
                "quantity": holding.get('quantity', 0),
                "average_price": holding.get('avg_price', 0.0),
                "current_price": holding.get('current_price', 0.0),
                "total_value": holding.get('market_value', 0.0),
                "total_cost": holding.get('invested_value', 0.0),
                "pnl": holding.get('pnl', 0.0),
                "pnl_percentage": holding.get('pnl_percentage', 0.0),
                "last_updated": datetime.now().isoformat()
            }
            
            return formatted_data
            
        except Exception as e:
            logger.error(f"Failed to format Groww stock data: {e}")
            raise

    async def import_from_csv(self, csv_data: str, portfolio_id: str, db) -> Dict[str, Any]:
        """
        Import portfolio data from CSV export
        This is an alternative approach for Groww integration
        """
        try:
            logger.info(f"Starting Groww CSV import for portfolio_id: {portfolio_id}")
            
            # Parse CSV data
            import csv
            from io import StringIO
            
            csv_reader = csv.DictReader(StringIO(csv_data))
            holdings_data = list(csv_reader)
            
            synced_holdings = 0
            updated_assets = 0
            
            # Process each holding from CSV
            for row in holdings_data:
                try:
                    # Adapt these field names based on actual Groww CSV export format
                    symbol = row.get('Symbol', '').strip()
                    quantity = float(row.get('Quantity', 0))
                    
                    if not symbol or quantity <= 0:
                        continue
                    
                    # Create standardized holding data
                    holding_data = {
                        'symbol': symbol,
                        'name': row.get('Company Name', symbol),
                        'exchange': row.get('Exchange', 'NSE'),
                        'quantity': quantity,
                        'avg_price': float(row.get('Avg Price', 0)),
                        'current_price': float(row.get('Current Price', row.get('Avg Price', 0))),
                        'market_value': float(row.get('Market Value', 0)),
                        'invested_value': float(row.get('Invested Value', 0)),
                        'pnl': float(row.get('P&L', 0)),
                        'pnl_percentage': float(row.get('P&L %', 0))
                    }
                    
                    formatted_data = self.format_stock_data(holding_data)
                    full_symbol = f"{formatted_data['exchange']}:{formatted_data['symbol']}"
                    
                    # Get or create asset
                    asset = await db.asset.find_first(
                        where={'symbol': full_symbol}
                    )
                    
                    if not asset:
                        asset = await db.asset.create(
                            data={
                                'symbol': full_symbol,
                                'name': formatted_data['name'],
                                'type': 'STOCK',
                                'description': f"{formatted_data['symbol']} stock on {formatted_data['exchange']}",
                                'currentPrice': formatted_data['current_price'],
                                'priceUpdatedAt': datetime.now()
                            }
                        )
                        updated_assets += 1
                    
                    # Create or update holding
                    existing_holding = await db.portfolioholding.find_first(
                        where={
                            'portfolioId': portfolio_id,
                            'assetId': asset.id
                        }
                    )
                    
                    if existing_holding:
                        await db.portfolioholding.update(
                            where={'id': existing_holding.id},
                            data={
                                'quantity': formatted_data['quantity'],
                                'averagePrice': formatted_data['average_price'],
                                'currentPrice': formatted_data['current_price'],
                                'totalValue': formatted_data['total_value'],
                                'totalCost': formatted_data['total_cost'],
                                'gainLoss': formatted_data['pnl'],
                                'gainLossPercent': formatted_data['pnl_percentage'],
                                'allocation': 0.0,
                                'updatedAt': datetime.now()
                            }
                        )
                    else:
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
                                'gainLossPercent': formatted_data['pnl_percentage'],
                                'allocation': 0.0
                            }
                        )
                    
                    synced_holdings += 1
                    logger.info(f"Imported holding for {full_symbol}: qty={formatted_data['quantity']}")
                    
                except Exception as e:
                    logger.error(f"Failed to import holding from CSV row: {e}")
                    continue
            
            # Recalculate portfolio totals
            await self._recalculate_portfolio_totals(portfolio_id, db)
            await self._recalculate_allocations(portfolio_id, db)
            
            logger.info(f"Successfully imported {synced_holdings} holdings from Groww CSV")
            
            return {
                'synced_holdings': synced_holdings,
                'updated_assets': updated_assets,
                'method': 'csv_import'
            }
            
        except Exception as e:
            logger.error(f"Failed to import Groww CSV data: {str(e)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            raise

    async def sync_portfolio(self, access_token: str, portfolio_id: str, db) -> Dict[str, Any]:
        """
        Sync portfolio data from Groww account
        Currently returns placeholder response due to API limitations
        """
        try:
            logger.warning("Groww API sync not available - consider using CSV import")
            
            return {
                'synced_holdings': 0,
                'updated_assets': 0,
                'error': 'Groww API not publicly available',
                'suggestion': 'Use CSV import functionality instead'
            }
            
        except Exception as e:
            logger.error(f"Failed to sync Groww portfolio: {str(e)}")
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
            
            logger.info(f"Updated Groww portfolio totals: value=₹{total_value:.2f}, cost=₹{total_cost:.2f}")
            
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
            
            logger.info(f"Updated allocations for {len(holdings)} Groww holdings")
            
        except Exception as e:
            logger.error(f"Failed to recalculate allocations: {str(e)}")
            raise

# Global instance
groww_service = GrowwAPIService() 