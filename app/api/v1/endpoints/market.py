from fastapi import APIRouter, Depends, HTTPException, Query
from prisma import Prisma
from app.core.database import get_db
from app.schemas.market import *
from app.core.logger import logger
from app.services.binance_service import binance_service
from typing import List, Optional

router = APIRouter()

@router.get("/data")
async def get_market_data(limit: int = Query(50, ge=1, le=100)):
    """Get real-time market data from Binance"""
    try:
        # Get top cryptocurrencies from Binance
        top_cryptos = await binance_service.get_top_cryptocurrencies(limit)
        
        # Get market summary
        market_summary = await binance_service.get_market_summary()
        
        # Format top cryptocurrencies data
        formatted_cryptos = []
        for crypto in top_cryptos:
            formatted_data = binance_service.format_market_data(crypto)
            formatted_cryptos.append(formatted_data)
        
        # Split into gainers and losers
        top_gainers = sorted(
            [crypto for crypto in formatted_cryptos if crypto['price_change_percentage_24h'] > 0],
            key=lambda x: x['price_change_percentage_24h'],
            reverse=True
        )[:10]
        
        top_losers = sorted(
            [crypto for crypto in formatted_cryptos if crypto['price_change_percentage_24h'] < 0],
            key=lambda x: x['price_change_percentage_24h']
        )[:10]
        
        # Get trending assets (highest volume)
        trending_assets = sorted(
            formatted_cryptos,
            key=lambda x: x['volume_24h'],
            reverse=True
        )[:10]
        
        return {
            "total_market_cap": None,  # Binance doesn't provide total market cap
            "total_volume_24h": market_summary['total_volume_24h'],
            "market_cap_change_24h": market_summary['market_cap_change_24h'],
            "active_cryptocurrencies": market_summary['active_cryptocurrencies'],
            "trending_assets": trending_assets,
            "top_gainers": top_gainers,
            "top_losers": top_losers,
            "market_summary": market_summary
        }
    except Exception as e:
        logger.error(f"Failed to fetch market data: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch market data")

@router.get("/overview")
async def get_market_overview(limit: int = Query(50, ge=1, le=100)):
    """Get market overview data from Binance"""
    try:
        # Get top cryptocurrencies from Binance
        top_cryptos = await binance_service.get_top_cryptocurrencies(limit)
        
        # Get market summary
        market_summary = await binance_service.get_market_summary()
        
        # Format top cryptocurrencies data
        formatted_cryptos = []
        for crypto in top_cryptos:
            formatted_data = binance_service.format_market_data(crypto)
            formatted_cryptos.append(formatted_data)
        
        # Get trending assets (highest volume)
        trending_assets = sorted(
            formatted_cryptos,
            key=lambda x: x['volume_24h'],
            reverse=True
        )[:10]
        
        # Get top gainers
        top_gainers = sorted(
            [crypto for crypto in formatted_cryptos if crypto['price_change_percentage_24h'] > 0],
            key=lambda x: x['price_change_percentage_24h'],
            reverse=True
        )[:10]
        
        # Get top losers
        top_losers = sorted(
            [crypto for crypto in formatted_cryptos if crypto['price_change_percentage_24h'] < 0],
            key=lambda x: x['price_change_percentage_24h']
        )[:10]
        
        # Convert to summary responses
        trending_summaries = [AssetSummaryResponse(
            id=crypto['symbol'], symbol=crypto['symbol'], name=crypto['name'], 
            type="CRYPTOCURRENCY", current_price=crypto['current_price'], 
            change_24h=crypto['price_change_percentage_24h'], logo_url=None
        ) for crypto in trending_assets]
        
        gainer_summaries = [AssetSummaryResponse(
            id=crypto['symbol'], symbol=crypto['symbol'], name=crypto['name'], 
            type="CRYPTOCURRENCY", current_price=crypto['current_price'], 
            change_24h=crypto['price_change_percentage_24h'], logo_url=None
        ) for crypto in top_gainers]
        
        loser_summaries = [AssetSummaryResponse(
            id=crypto['symbol'], symbol=crypto['symbol'], name=crypto['name'], 
            type="CRYPTOCURRENCY", current_price=crypto['current_price'], 
            change_24h=crypto['price_change_percentage_24h'], logo_url=None
        ) for crypto in top_losers]
        
        return MarketOverviewResponse(
            total_market_cap=0.0,  # Binance doesn't provide total market cap
            total_volume_24h=market_summary['total_volume_24h'],
            market_cap_change_24h=market_summary['market_cap_change_24h'],
            active_cryptocurrencies=market_summary['active_cryptocurrencies'],
            trending_assets=trending_summaries,
            top_gainers=gainer_summaries,
            top_losers=loser_summaries
        )
    except Exception as e:
        logger.error(f"Get market overview failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch market overview")

@router.get("/signals", response_model=TradingSignalsResponse)
async def get_trading_signals(db: Prisma = Depends(get_db)):
    """Get AI trading signals"""
    try:
        signals = await db.tradingsignal.find_many(
            where={"isActive": True},
            order={"createdAt": "desc"},
            take=20,
            include={"asset": True}
        )
        
        signal_responses = []
        for signal in signals:
            signal_responses.append(TradingSignalResponse(
                id=signal.id,
                asset_id=signal.assetId,
                symbol=signal.asset.symbol,
                type=signal.type,
                strength=signal.strength,
                confidence=signal.confidence,
                current_price=signal.currentPrice,
                target_price=signal.targetPrice,
                stop_loss=signal.stopLoss,
                timeframe=signal.timeframe,
                reasoning=signal.reasoning,
                ai_model=signal.aiModel,
                is_active=signal.isActive,
                created_at=signal.createdAt,
                updated_at=signal.updatedAt,
            ))
        
        return TradingSignalsResponse(
            signals=signal_responses,
            total_count=len(signal_responses)
        )
    except Exception as e:
        logger.error(f"Get trading signals failed: {e}")
        raise 

@router.get("/price/{symbol}")
async def get_asset_price(symbol: str):
    """Get current price for a specific asset from Binance"""
    try:
        # Get ticker data from Binance for the specific symbol
        ticker_data = await binance_service.get_symbol_ticker(f"{symbol.upper()}USDT")
        
        if not ticker_data:
            raise HTTPException(status_code=404, detail="Asset not found")
        
        # Format the data
        formatted_data = binance_service.format_market_data(ticker_data)
        
        return {
            "symbol": formatted_data["symbol"],
            "price": formatted_data["current_price"],
            "change_24h": formatted_data["price_change_24h"],
            "change_percentage_24h": formatted_data["price_change_percentage_24h"],
            "volume_24h": formatted_data["volume_24h"],
            "quote_volume_24h": formatted_data["quote_volume_24h"],
            "high_24h": formatted_data["high_24h"],
            "low_24h": formatted_data["low_24h"],
            "market_cap": None,  # Binance doesn't provide market cap
            "last_updated": formatted_data["last_updated"]
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get asset price failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch asset price")

@router.get("/historical/{symbol}")
async def get_historical_data(
    symbol: str,
    interval: str = Query("1d", regex="^(1m|5m|15m|30m|1h|2h|4h|6h|8h|12h|1d|3d|1w|1M)$"),
    limit: int = Query(100, ge=1, le=1000)
):
    """Get historical kline/candlestick data for a symbol"""
    try:
        # Get historical data from Binance
        klines = await binance_service.get_klines(f"{symbol.upper()}USDT", interval, limit)
        
        if not klines:
            raise HTTPException(status_code=404, detail="Historical data not found")
        
        return {
            "symbol": symbol.upper(),
            "interval": interval,
            "data": klines
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get historical data failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch historical data")

@router.get("/search")
async def search_assets(
    query: str = Query(..., min_length=1, max_length=50),
    limit: int = Query(20, ge=1, le=100)
):
    """Search for assets by symbol or name"""
    try:
        # Get all tickers from Binance
        all_tickers = await binance_service.get_24hr_ticker_stats()
        
        # Filter for USDT pairs and search by symbol
        query_upper = query.upper()
        matching_assets = []
        
        for ticker in all_tickers:
            if ticker['symbol'].endswith('USDT'):
                base_symbol = ticker['symbol'].replace('USDT', '')
                if query_upper in base_symbol:
                    formatted_data = binance_service.format_market_data(ticker)
                    matching_assets.append(formatted_data)
        
        # Sort by volume and limit results
        matching_assets.sort(key=lambda x: x['volume_24h'], reverse=True)
        matching_assets = matching_assets[:limit]
        
        return {
            "query": query,
            "total_results": len(matching_assets),
            "results": matching_assets
        }
    except Exception as e:
        logger.error(f"Search assets failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to search assets")

@router.get("/top-gainers")
async def get_top_gainers(limit: int = Query(20, ge=1, le=100)):
    """Get top gaining cryptocurrencies"""
    try:
        # Get top cryptocurrencies from Binance
        top_cryptos = await binance_service.get_top_cryptocurrencies(200)
        
        # Format and filter gainers
        formatted_cryptos = []
        for crypto in top_cryptos:
            formatted_data = binance_service.format_market_data(crypto)
            if formatted_data['price_change_percentage_24h'] > 0:
                formatted_cryptos.append(formatted_data)
        
        # Sort by percentage change and limit
        top_gainers = sorted(
            formatted_cryptos,
            key=lambda x: x['price_change_percentage_24h'],
            reverse=True
        )[:limit]
        
        return {
            "top_gainers": top_gainers,
            "total_count": len(top_gainers)
        }
    except Exception as e:
        logger.error(f"Get top gainers failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch top gainers")

@router.get("/top-losers")
async def get_top_losers(limit: int = Query(20, ge=1, le=100)):
    """Get top losing cryptocurrencies"""
    try:
        # Get top cryptocurrencies from Binance
        top_cryptos = await binance_service.get_top_cryptocurrencies(200)
        
        # Format and filter losers
        formatted_cryptos = []
        for crypto in top_cryptos:
            formatted_data = binance_service.format_market_data(crypto)
            if formatted_data['price_change_percentage_24h'] < 0:
                formatted_cryptos.append(formatted_data)
        
        # Sort by percentage change (ascending for losers) and limit
        top_losers = sorted(
            formatted_cryptos,
            key=lambda x: x['price_change_percentage_24h']
        )[:limit]
        
        return {
            "top_losers": top_losers,
            "total_count": len(top_losers)
        }
    except Exception as e:
        logger.error(f"Get top losers failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch top losers")

@router.get("/order-book/{symbol}")
async def get_order_book(
    symbol: str,
    limit: int = Query(20, ge=5, le=100)
):
    """Get order book (market depth) for a symbol"""
    try:
        # Get order book from Binance
        order_book = await binance_service.get_order_book(f"{symbol.upper()}USDT", limit)
        
        if not order_book:
            raise HTTPException(status_code=404, detail="Order book not found")
        
        return order_book
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get order book failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch order book")