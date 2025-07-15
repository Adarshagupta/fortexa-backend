from fastapi import APIRouter
from app.api.v1.endpoints import auth, users, portfolio, assets, trades, alerts, news, market, notifications, settings, signals, security
from app.api.v1.endpoints import api_keys

api_router = APIRouter()

# Include all endpoint routers
api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(portfolio.router, prefix="/portfolio", tags=["portfolio"])
api_router.include_router(assets.router, prefix="/assets", tags=["assets"])
api_router.include_router(trades.router, prefix="/trades", tags=["trades"])
api_router.include_router(alerts.router, prefix="/alerts", tags=["alerts"])
api_router.include_router(news.router, prefix="/news", tags=["news"])
api_router.include_router(market.router, prefix="/market", tags=["market"])
api_router.include_router(notifications.router, prefix="/notifications", tags=["notifications"])
api_router.include_router(settings.router, prefix="/settings", tags=["settings"])
api_router.include_router(signals.router, prefix="/signals", tags=["signals"])
api_router.include_router(security.router, prefix="/security", tags=["security"])
api_router.include_router(api_keys.router, prefix="/api-keys", tags=["api-keys"]) 