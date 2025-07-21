#!/usr/bin/env python3
"""
Seed script to add sample data to the database
"""
import asyncio
import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from prisma import Prisma
from prisma.enums import AssetType, SignalType

async def seed_data():
    """Add sample data to the database"""
    db = Prisma()
    await db.connect()
    
    try:
        # Add sample assets
        assets_data = [
            {
                "symbol": "BTC",
                "name": "Bitcoin",
                "type": AssetType.CRYPTOCURRENCY,
                "description": "Digital currency",
                "currentPrice": 45000.00,
                "marketCap": 850000000000.00,
                "volume24h": 25000000000.00,
                "change24h": 2.5,
                "change7d": 8.2,
                "change30d": 15.8,
                "high24h": 46000.00,
                "low24h": 44000.00,
                "isActive": True,
            },
            {
                "symbol": "ETH",
                "name": "Ethereum",
                "type": AssetType.CRYPTOCURRENCY,
                "description": "Smart contract platform",
                "currentPrice": 2800.00,
                "marketCap": 340000000000.00,
                "volume24h": 12000000000.00,
                "change24h": 3.2,
                "change7d": 12.5,
                "change30d": 22.1,
                "high24h": 2900.00,
                "low24h": 2700.00,
                "isActive": True,
            },
            {
                "symbol": "ADA",
                "name": "Cardano",
                "type": AssetType.CRYPTOCURRENCY,
                "description": "Blockchain platform",
                "currentPrice": 0.45,
                "marketCap": 15000000000.00,
                "volume24h": 800000000.00,
                "change24h": -1.2,
                "change7d": 5.8,
                "change30d": 8.5,
                "high24h": 0.48,
                "low24h": 0.42,
                "isActive": True,
            },
            {
                "symbol": "DOT",
                "name": "Polkadot",
                "type": AssetType.CRYPTOCURRENCY,
                "description": "Interoperability protocol",
                "currentPrice": 7.50,
                "marketCap": 9000000000.00,
                "volume24h": 450000000.00,
                "change24h": 1.8,
                "change7d": -2.3,
                "change30d": 12.7,
                "high24h": 7.80,
                "low24h": 7.20,
                "isActive": True,
            },
            {
                "symbol": "SOL",
                "name": "Solana",
                "type": AssetType.CRYPTOCURRENCY,
                "description": "High-performance blockchain",
                "currentPrice": 105.00,
                "marketCap": 47000000000.00,
                "volume24h": 2000000000.00,
                "change24h": 4.2,
                "change7d": 18.5,
                "change30d": 35.2,
                "high24h": 108.00,
                "low24h": 100.00,
                "isActive": True,
            },
        ]
        
        # Check if assets already exist
        existing_assets = await db.asset.find_many()
        if len(existing_assets) == 0:
            print("Creating sample assets...")
            for asset_data in assets_data:
                await db.asset.create(data=asset_data)
            print(f"Created {len(assets_data)} assets")
        else:
            print(f"Found {len(existing_assets)} existing assets")
        
        # Get all assets for creating signals
        all_assets = await db.asset.find_many()
        
        # Create sample trading signals
        signals_data = []
        for asset in all_assets[:3]:  # Create signals for first 3 assets
            signals_data.extend([
                {
                    "assetId": asset.id,
                    "type": SignalType.BUY,
                    "strength": 85.0,
                    "confidence": 78.0,
                    "currentPrice": asset.currentPrice,
                    "targetPrice": asset.currentPrice * 1.15,
                    "stopLoss": asset.currentPrice * 0.95,
                    "timeframe": "1d",
                    "reasoning": f"Technical analysis shows strong bullish momentum for {asset.symbol}",
                    "aiModel": "GPT-4 Technical Analysis",
                    "isActive": True,
                },
                {
                    "assetId": asset.id,
                    "type": SignalType.HOLD,
                    "strength": 70.0,
                    "confidence": 65.0,
                    "currentPrice": asset.currentPrice,
                    "targetPrice": asset.currentPrice * 1.05,
                    "stopLoss": asset.currentPrice * 0.98,
                    "timeframe": "4h",
                    "reasoning": f"Market consolidation expected for {asset.symbol}",
                    "aiModel": "Machine Learning Model v2.1",
                    "isActive": True,
                },
            ])
        
        # Check if signals already exist
        existing_signals = await db.tradingsignal.find_many()
        if len(existing_signals) == 0:
            print("Creating sample trading signals...")
            for signal_data in signals_data:
                await db.tradingsignal.create(data=signal_data)
            print(f"Created {len(signals_data)} trading signals")
        else:
            print(f"Found {len(existing_signals)} existing signals")
        
        print("Database seeding completed successfully!")
        
    except Exception as e:
        print(f"Error seeding database: {e}")
        raise
    finally:
        await db.disconnect()

if __name__ == "__main__":
    asyncio.run(seed_data()) 