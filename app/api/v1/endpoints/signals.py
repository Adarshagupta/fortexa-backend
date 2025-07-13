from fastapi import APIRouter, Depends
from prisma import Prisma
from app.core.database import get_db
from app.schemas.market import TradingSignalsResponse, TradingSignalResponse
from app.core.logger import logger

router = APIRouter()

@router.get("/")
async def get_trading_signals():
    """Get AI trading signals (simplified for testing)"""
    return {
        "signals": [
            {
                "id": "1",
                "asset_id": "btc",
                "symbol": "BTC",
                "type": "BUY",
                "strength": 85.0,
                "confidence": 78.0,
                "current_price": 45000.0,
                "target_price": 52000.0,
                "reasoning": "Strong bullish momentum",
                "ai_model": "GPT-4",
                "is_active": True
            }
        ],
        "total_count": 1
    }

@router.get("/{signal_id}", response_model=TradingSignalResponse)
async def get_trading_signal(signal_id: str, db: Prisma = Depends(get_db)):
    """Get a specific trading signal"""
    try:
        signal = await db.tradingsignal.find_unique(
            where={"id": signal_id},
            include={"asset": True}
        )
        
        if not signal:
            return {"error": "Signal not found"}
            
        return TradingSignalResponse(
            id=signal.id,
            asset_id=signal.assetId,
            symbol=signal.asset.symbol,
            type=signal.type.value,
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
        )
    except Exception as e:
        logger.error(f"Get trading signal failed: {e}")
        raise 