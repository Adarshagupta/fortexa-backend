import asyncio
import httpx
from datetime import datetime, timedelta
from typing import List, Dict, Any
from celery import current_task
from app.tasks.celery_app import celery_app
from app.core.database import init_db, db
from app.core.config import settings
from app.core.logger import logger
from app.services.binance_service import binance_service

@celery_app.task(bind=True)
def update_market_data(self):
    """Update market data for all active assets"""
    try:
        asyncio.run(_update_market_data())
        logger.info("Market data updated successfully")
        return {"status": "success", "message": "Market data updated"}
    except Exception as e:
        logger.error(f"Market data update failed: {e}")
        return {"status": "error", "message": str(e)}

async def _update_market_data():
    """Internal async function to update market data using Binance API"""
    try:
        # Initialize database connection
        await init_db()
        
        # Get top cryptocurrencies from Binance
        top_cryptos = await binance_service.get_top_cryptocurrencies(100)
        
        # Update or create assets in database
        updated_assets = []
        for crypto in top_cryptos:
            formatted_data = binance_service.format_market_data(crypto)
            
            # Check if asset exists
            existing_asset = await db.asset.find_first(
                where={"symbol": formatted_data["symbol"]}
            )
            
            if existing_asset:
                # Update existing asset
                updated_asset = await db.asset.update(
                    where={"id": existing_asset.id},
                    data={
                        "currentPrice": formatted_data["current_price"],
                        "change24h": formatted_data["price_change_percentage_24h"],
                        "priceChange24h": formatted_data["price_change_24h"],
                        "volume24h": formatted_data["volume_24h"],
                        "quoteVolume24h": formatted_data["quote_volume_24h"],
                        "high24h": formatted_data["high_24h"],
                        "low24h": formatted_data["low_24h"],
                        "openPrice": formatted_data["open_price"],
                        "prevClosePrice": formatted_data["prev_close_price"],
                        "bidPrice": formatted_data["bid_price"],
                        "askPrice": formatted_data["ask_price"],
                        "priceUpdatedAt": datetime.now(),
                        "updatedAt": datetime.now()
                    }
                )
                updated_assets.append(updated_asset)
            else:
                # Create new asset
                new_asset = await db.asset.create(
                    data={
                        "symbol": formatted_data["symbol"],
                        "name": formatted_data["name"],
                        "type": "CRYPTOCURRENCY",
                        "currentPrice": formatted_data["current_price"],
                        "change24h": formatted_data["price_change_percentage_24h"],
                        "priceChange24h": formatted_data["price_change_24h"],
                        "volume24h": formatted_data["volume_24h"],
                        "quoteVolume24h": formatted_data["quote_volume_24h"],
                        "high24h": formatted_data["high_24h"],
                        "low24h": formatted_data["low_24h"],
                        "openPrice": formatted_data["open_price"],
                        "prevClosePrice": formatted_data["prev_close_price"],
                        "bidPrice": formatted_data["bid_price"],
                        "askPrice": formatted_data["ask_price"],
                        "isActive": True,
                        "priceUpdatedAt": datetime.now(),
                        "createdAt": datetime.now(),
                        "updatedAt": datetime.now()
                    }
                )
                updated_assets.append(new_asset)
        
        # Update price history for updated assets
        await _update_price_history(updated_assets)
        
        # Update market calculations
        await _update_market_calculations(updated_assets)
        
        logger.info(f"Successfully updated {len(updated_assets)} assets from Binance")
        
    except Exception as e:
        logger.error(f"Failed to update market data: {e}")
        raise

async def _update_crypto_prices(crypto_assets: List[Any]):
    """Update cryptocurrency prices using external API"""
    try:
        # Mock price updates (in real implementation, use CoinGecko, CoinMarketCap, etc.)
        async with httpx.AsyncClient(timeout=30.0) as client:
            for asset in crypto_assets:
                # Simulate price fluctuation
                import random
                current_price = asset.currentPrice
                
                # Random price change between -5% and +5%
                price_change = random.uniform(-0.05, 0.05)
                new_price = current_price * (1 + price_change)
                
                # Calculate 24h change
                change_24h = price_change * 100
                
                # Update asset
                await db.asset.update(
                    where={"id": asset.id},
                    data={
                        "currentPrice": new_price,
                        "change24h": change_24h,
                        "high24h": max(asset.high24h or 0, new_price),
                        "low24h": min(asset.low24h or float('inf'), new_price),
                        "priceUpdatedAt": datetime.utcnow(),
                    }
                )
        
        logger.info(f"Updated prices for {len(crypto_assets)} crypto assets")
    except Exception as e:
        logger.error(f"Failed to update crypto prices: {e}")

async def _update_price_history(assets: List[Any]):
    """Update price history for assets"""
    try:
        for asset in assets:
            # Create price history entry
            await db.pricehistory.create(
                data={
                    "assetId": asset.id,
                    "timestamp": datetime.utcnow(),
                    "open": asset.currentPrice,
                    "high": asset.high24h or asset.currentPrice,
                    "low": asset.low24h or asset.currentPrice,
                    "close": asset.currentPrice,
                    "volume": asset.volume24h or 0,
                }
            )
        
        logger.info(f"Updated price history for {len(assets)} assets")
    except Exception as e:
        logger.error(f"Failed to update price history: {e}")

async def _update_market_calculations(assets: List[Any]):
    """Update market calculations like market cap, volume, etc."""
    try:
        for asset in assets:
            # Mock volume update
            import random
            volume_change = random.uniform(-0.1, 0.1)
            new_volume = (asset.volume24h or 1000000) * (1 + volume_change)
            
            # Update volume
            await db.asset.update(
                where={"id": asset.id},
                data={
                    "volume24h": new_volume,
                }
            )
        
        logger.info(f"Updated market calculations for {len(assets)} assets")
    except Exception as e:
        logger.error(f"Failed to update market calculations: {e}")

@celery_app.task(bind=True)
def generate_trading_signals(self):
    """Generate AI trading signals"""
    try:
        asyncio.run(_generate_trading_signals())
        logger.info("Trading signals generated successfully")
        return {"status": "success", "message": "Trading signals generated"}
    except Exception as e:
        logger.error(f"Trading signal generation failed: {e}")
        return {"status": "error", "message": str(e)}

async def _generate_trading_signals():
    """Internal async function to generate trading signals"""
    # Initialize database connection
    await init_db()
    
    # Get active assets
    assets = await db.asset.find_many(
        where={"isActive": True},
        take=20  # Limit to top 20 assets
    )
    
    for asset in assets:
        # Simple signal generation based on price change
        if asset.change24h and abs(asset.change24h) > 2:  # If price moved more than 2%
            signal_type = "BUY" if asset.change24h > 0 else "SELL"
            
            # Generate signal strength and confidence
            import random
            strength = min(abs(asset.change24h) * 10, 100)  # Convert to 0-100 scale
            confidence = random.uniform(60, 90)  # Random confidence between 60-90%
            
            # Calculate target price
            target_multiplier = 1.05 if signal_type == "BUY" else 0.95
            target_price = asset.currentPrice * target_multiplier
            
            # Check if signal already exists
            existing_signal = await db.tradingsignal.find_first(
                where={
                    "assetId": asset.id,
                    "isActive": True,
                    "createdAt": {"gte": datetime.utcnow() - timedelta(hours=1)}
                }
            )
            
            if not existing_signal:
                # Create new signal
                await db.tradingsignal.create(
                    data={
                        "assetId": asset.id,
                        "type": signal_type,
                        "strength": strength,
                        "confidence": confidence,
                        "currentPrice": asset.currentPrice,
                        "targetPrice": target_price,
                        "stopLoss": asset.currentPrice * 0.95 if signal_type == "BUY" else asset.currentPrice * 1.05,
                        "timeframe": "1d",
                        "reasoning": f"Price moved {asset.change24h:.2f}% in 24h, indicating {signal_type.lower()} opportunity",
                        "aiModel": "price_momentum_v1",
                        "isActive": True,
                    }
                )
    
    logger.info(f"Generated trading signals for {len(assets)} assets")

@celery_app.task(bind=True)
def update_asset_prices(self, asset_ids: List[str]):
    """Update specific asset prices"""
    try:
        asyncio.run(_update_specific_assets(asset_ids))
        return {"status": "success", "updated_assets": len(asset_ids)}
    except Exception as e:
        logger.error(f"Failed to update specific asset prices: {e}")
        return {"status": "error", "message": str(e)}

async def _update_specific_assets(asset_ids: List[str]):
    """Update prices for specific assets"""
    await init_db()
    
    for asset_id in asset_ids:
        asset = await db.asset.find_unique(where={"id": asset_id})
        if asset:
            # Mock price update
            import random
            price_change = random.uniform(-0.02, 0.02)
            new_price = asset.currentPrice * (1 + price_change)
            
            await db.asset.update(
                where={"id": asset_id},
                data={
                    "currentPrice": new_price,
                    "change24h": price_change * 100,
                    "priceUpdatedAt": datetime.utcnow(),
                }
            )

@celery_app.task(bind=True)
def cleanup_old_data(self):
    """Clean up old price history and signals"""
    try:
        asyncio.run(_cleanup_old_data())
        logger.info("Old data cleanup completed")
        return {"status": "success", "message": "Old data cleaned up"}
    except Exception as e:
        logger.error(f"Data cleanup failed: {e}")
        return {"status": "error", "message": str(e)}

async def _cleanup_old_data():
    """Internal async function to cleanup old data"""
    await init_db()
    
    # Delete price history older than 1 year
    cutoff_date = datetime.utcnow() - timedelta(days=365)
    
    await db.pricehistory.delete_many(
        where={"timestamp": {"lt": cutoff_date}}
    )
    
    # Deactivate old trading signals
    signal_cutoff = datetime.utcnow() - timedelta(days=7)
    
    await db.tradingsignal.update_many(
        where={"createdAt": {"lt": signal_cutoff}},
        data={"isActive": False}
    )
    
    logger.info("Old data cleanup completed") 