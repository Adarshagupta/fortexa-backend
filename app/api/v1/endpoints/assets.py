from fastapi import APIRouter, Depends, Query
from prisma import Prisma
from typing import List, Optional
from app.core.database import get_db
from app.schemas.market import *
from app.core.logger import logger

router = APIRouter()

@router.get("/")
async def get_assets():
    """Get list of assets (simplified for testing)"""
    return {
        "assets": [
            {
                "id": "1",
                "symbol": "BTC",
                "name": "Bitcoin",
                "type": "CRYPTOCURRENCY",
                "current_price": 45000.0,
                "market_cap": 850000000000.0,
                "volume_24h": 25000000000.0,
                "change_24h": 2.5,
                "is_active": True
            },
            {
                "id": "2",
                "symbol": "ETH",
                "name": "Ethereum",
                "type": "CRYPTOCURRENCY",
                "current_price": 2800.0,
                "market_cap": 340000000000.0,
                "volume_24h": 12000000000.0,
                "change_24h": 3.2,
                "is_active": True
            }
        ],
        "total_count": 2,
        "page": 1,
        "page_size": 20,
        "total_pages": 1
    }

@router.get("/{asset_id}", response_model=AssetResponse)
async def get_asset(
    asset_id: str,
    db: Prisma = Depends(get_db)
):
    """Get single asset by ID"""
    try:
        asset = await db.asset.find_unique(where={"id": asset_id})
        
        if not asset:
            from app.core.exceptions import AssetNotFoundException
            raise AssetNotFoundException()
        
        return AssetResponse(
            id=asset.id,
            symbol=asset.symbol,
            name=asset.name,
            type=asset.type,
            description=asset.description,
            logo_url=asset.logoUrl,
            current_price=asset.currentPrice,
            market_cap=asset.marketCap,
            volume_24h=asset.volume24h,
            change_24h=asset.change24h,
            change_7d=asset.change7d,
            change_30d=asset.change30d,
            high_24h=asset.high24h,
            low_24h=asset.low24h,
            price_updated_at=asset.priceUpdatedAt,
            is_active=asset.isActive,
            created_at=asset.createdAt,
            updated_at=asset.updatedAt,
        )
    except Exception as e:
        logger.error(f"Get asset failed: {e}")
        raise

@router.post("/search", response_model=AssetSearchResponse)
async def search_assets(
    request: AssetSearchRequest,
    db: Prisma = Depends(get_db)
):
    """Search assets by symbol or name"""
    try:
        # Build search query
        where_clause = {
            "isActive": True,
            "OR": [
                {"symbol": {"contains": request.query, "mode": "insensitive"}},
                {"name": {"contains": request.query, "mode": "insensitive"}},
            ]
        }
        
        if request.asset_type:
            where_clause["type"] = request.asset_type
        
        # Search assets
        assets = await db.asset.find_many(
            where=where_clause,
            take=request.limit,
            order={"marketCap": "desc"}
        )
        
        # Convert to response
        asset_summaries = []
        for asset in assets:
            asset_summaries.append(AssetSummaryResponse(
                id=asset.id,
                symbol=asset.symbol,
                name=asset.name,
                type=asset.type,
                current_price=asset.currentPrice,
                change_24h=asset.change24h,
                logo_url=asset.logoUrl,
            ))
        
        return AssetSearchResponse(
            assets=asset_summaries,
            total_count=len(asset_summaries)
        )
    except Exception as e:
        logger.error(f"Search assets failed: {e}")
        raise

@router.get("/{asset_id}/price-history", response_model=PriceHistoryResponse)
async def get_asset_price_history(
    asset_id: str,
    timeframe: str = Query("1d", pattern="^(1h|4h|1d|7d|30d)$"),
    db: Prisma = Depends(get_db)
):
    """Get asset price history"""
    try:
        # Check if asset exists
        asset = await db.asset.find_unique(where={"id": asset_id})
        if not asset:
            from app.core.exceptions import AssetNotFoundException
            raise AssetNotFoundException()
        
        # Get price history
        price_history = await db.pricehistory.find_many(
            where={"assetId": asset_id},
            order={"timestamp": "desc"},
            take=100  # Limit to last 100 data points
        )
        
        # Convert to response
        history_points = []
        for point in price_history:
            history_points.append(PriceHistoryPoint(
                timestamp=point.timestamp,
                open=point.open,
                high=point.high,
                low=point.low,
                close=point.close,
                volume=point.volume,
            ))
        
        return PriceHistoryResponse(
            asset_id=asset_id,
            symbol=asset.symbol,
            timeframe=timeframe,
            data=history_points
        )
    except Exception as e:
        logger.error(f"Get price history failed: {e}")
        raise 