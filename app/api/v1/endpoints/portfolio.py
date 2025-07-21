from fastapi import APIRouter, Depends, HTTPException, Query
from prisma import Prisma
from typing import List, Optional
from datetime import datetime, timedelta
from app.core.database import get_db
from app.schemas.portfolio import *
from app.schemas.market import AssetSummaryResponse
from app.api.v1.endpoints.auth import get_verified_user_id
from app.core.logger import logger
from app.core.exceptions import *

router = APIRouter()

@router.post("/", response_model=PortfolioResponse)
async def create_portfolio(
    request: CreatePortfolioRequest,
    current_user_id: str = Depends(get_verified_user_id),
    db: Prisma = Depends(get_db)
):
    """Create a new portfolio"""
    try:
        # Check if user already has a portfolio
        existing_portfolio = await db.portfolio.find_unique(
            where={"userId": current_user_id}
        )
        
        if existing_portfolio:
            # User already has a portfolio, return it
            return PortfolioResponse(
                id=existing_portfolio.id,
                user_id=existing_portfolio.userId,
                name=existing_portfolio.name,
                total_value=existing_portfolio.totalValue,
                total_cost=existing_portfolio.totalCost,
                total_gain_loss=existing_portfolio.totalGainLoss,
                total_gain_loss_percent=existing_portfolio.totalGainLossPercent,
                last_updated=existing_portfolio.lastUpdated,
                created_at=existing_portfolio.createdAt,
                updated_at=existing_portfolio.updatedAt,
            )
        
        # Create new portfolio
        portfolio = await db.portfolio.create(
            data={
                "userId": current_user_id,
                "name": request.name,
                "totalValue": 0.0,
                "totalCost": 0.0,
                "totalGainLoss": 0.0,
                "totalGainLossPercent": 0.0,
                "lastUpdated": datetime.now(),
            }
        )
        
        return PortfolioResponse(
            id=portfolio.id,
            user_id=portfolio.userId,
            name=portfolio.name,
            total_value=portfolio.totalValue,
            total_cost=portfolio.totalCost,
            total_gain_loss=portfolio.totalGainLoss,
            total_gain_loss_percent=portfolio.totalGainLossPercent,
            last_updated=portfolio.lastUpdated,
            created_at=portfolio.createdAt,
            updated_at=portfolio.updatedAt,
        )
        
    except Exception as e:
        logger.error(f"Create portfolio failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to create portfolio")

@router.get("/", response_model=List[PortfolioResponse])
async def get_portfolios(
    current_user_id: str = Depends(get_verified_user_id),
    db: Prisma = Depends(get_db)
):
    """Get user's portfolios"""
    try:
        portfolios = await db.portfolio.find_many(
            where={"userId": current_user_id},
            include={"holdings": True}
        )
        
        portfolio_responses = []
        for portfolio in portfolios:
            portfolio_responses.append(PortfolioResponse(
                id=portfolio.id,
                user_id=portfolio.userId,
                name=portfolio.name,
                total_value=portfolio.totalValue,
                total_cost=portfolio.totalCost,
                total_gain_loss=portfolio.totalGainLoss,
                total_gain_loss_percent=portfolio.totalGainLossPercent,
                last_updated=portfolio.lastUpdated,
                created_at=portfolio.createdAt,
                updated_at=portfolio.updatedAt,
            ))
        
        return portfolio_responses
    except Exception as e:
        logger.error(f"Get portfolios failed: {e}")
        raise

@router.get("/summary", response_model=PortfolioSummaryResponse)
async def get_portfolio_summary(
    current_user_id: str = Depends(get_verified_user_id),
    db: Prisma = Depends(get_db)
):
    """Get portfolio summary"""
    try:
        portfolio = await db.portfolio.find_unique(
            where={"userId": current_user_id},
            include={"holdings": True}
        )
        
        if not portfolio:
            raise PortfolioNotFoundException()
        
        return PortfolioSummaryResponse(
            id=portfolio.id,
            name=portfolio.name,
            total_value=portfolio.totalValue,
            total_cost=portfolio.totalCost,
            total_gain_loss=portfolio.totalGainLoss,
            total_gain_loss_percent=portfolio.totalGainLossPercent,
            holdings_count=len(portfolio.holdings),
            last_updated=portfolio.lastUpdated,
        )
    except Exception as e:
        logger.error(f"Get portfolio summary failed: {e}")
        raise

@router.get("/holdings", response_model=HoldingsListResponse)
async def get_holdings(
    current_user_id: str = Depends(get_verified_user_id),
    db: Prisma = Depends(get_db)
):
    """Get all portfolio holdings"""
    try:
        portfolio = await db.portfolio.find_unique(
            where={"userId": current_user_id},
            include={
                "holdings": {
                    "include": {"asset": True}
                }
            }
        )
        
        if not portfolio:
            raise PortfolioNotFoundException()
        
        holdings = []
        for holding in portfolio.holdings:
            holdings.append(HoldingResponse(
                id=holding.id,
                portfolio_id=holding.portfolioId,
                asset_id=holding.assetId,
                symbol=holding.symbol,
                quantity=holding.quantity,
                average_price=holding.averagePrice,
                current_price=holding.currentPrice,
                total_value=holding.totalValue,
                total_cost=holding.totalCost,
                gain_loss=holding.gainLoss,
                gain_loss_percent=holding.gainLossPercent,
                allocation=holding.allocation,
                created_at=holding.createdAt,
                updated_at=holding.updatedAt,
                asset={
                    "id": holding.asset.id,
                    "symbol": holding.asset.symbol,
                    "name": holding.asset.name,
                    "type": holding.asset.type,
                    "current_price": holding.asset.currentPrice,
                    "price_change_percentage_24h": holding.asset.change24h or 0.0,
                },
            ))
        
        portfolio_summary = PortfolioSummaryResponse(
            id=portfolio.id,
            name=portfolio.name,
            total_value=portfolio.totalValue,
            total_cost=portfolio.totalCost,
            total_gain_loss=portfolio.totalGainLoss,
            total_gain_loss_percent=portfolio.totalGainLossPercent,
            holdings_count=len(holdings),
            last_updated=portfolio.lastUpdated,
        )
        
        return HoldingsListResponse(
            holdings=holdings,
            total_count=len(holdings),
            portfolio_summary=portfolio_summary
        )
    except Exception as e:
        logger.error(f"Get holdings failed: {e}")
        raise

@router.post("/holdings", response_model=AddHoldingResponse)
async def add_holding(
    request: AddHoldingRequest,
    current_user_id: str = Depends(get_verified_user_id),
    db: Prisma = Depends(get_db)
):
    """Add a new holding to portfolio"""
    try:
        # Get user's portfolio
        portfolio = await db.portfolio.find_unique(
            where={"userId": current_user_id}
        )
        
        if not portfolio:
            raise PortfolioNotFoundException()
        
        # Check if asset exists
        asset = await db.asset.find_unique(
            where={"id": request.asset_id}
        )
        
        if not asset:
            raise AssetNotFoundException()
        
        # Check if holding already exists
        existing_holding = await db.portfolioholding.find_first(
            where={
                "portfolioId": portfolio.id,
                "assetId": request.asset_id
            }
        )
        
        if existing_holding:
            # Update existing holding
            total_cost = existing_holding.totalCost + (request.quantity * request.average_price)
            total_quantity = existing_holding.quantity + request.quantity
            new_average_price = total_cost / total_quantity
            
            updated_holding = await db.portfolioholding.update(
                where={"id": existing_holding.id},
                data={
                    "quantity": total_quantity,
                    "averagePrice": new_average_price,
                    "totalCost": total_cost,
                    "currentPrice": asset.currentPrice,
                    "totalValue": total_quantity * asset.currentPrice,
                    "gainLoss": (total_quantity * asset.currentPrice) - total_cost,
                    "gainLossPercent": (((total_quantity * asset.currentPrice) - total_cost) / total_cost) * 100 if total_cost > 0 else 0,
                }
            )
            
            holding = updated_holding
        else:
            # Create new holding
            total_cost = request.quantity * request.average_price
            total_value = request.quantity * asset.currentPrice
            gain_loss = total_value - total_cost
            gain_loss_percent = (gain_loss / total_cost) * 100 if total_cost > 0 else 0
            
            holding = await db.portfolioholding.create(
                data={
                    "portfolioId": portfolio.id,
                    "assetId": request.asset_id,
                    "symbol": asset.symbol,
                    "quantity": request.quantity,
                    "averagePrice": request.average_price,
                    "currentPrice": asset.currentPrice,
                    "totalValue": total_value,
                    "totalCost": total_cost,
                    "gainLoss": gain_loss,
                    "gainLossPercent": gain_loss_percent,
                    "allocation": 0.0,  # Will be calculated in portfolio update
                }
            )
        
        # Update portfolio totals
        await _update_portfolio_totals(portfolio.id, db)
        
        return AddHoldingResponse(
            holding=HoldingResponse(
                id=holding.id,
                portfolio_id=holding.portfolioId,
                asset_id=holding.assetId,
                symbol=holding.symbol,
                quantity=holding.quantity,
                average_price=holding.averagePrice,
                current_price=holding.currentPrice,
                total_value=holding.totalValue,
                total_cost=holding.totalCost,
                gain_loss=holding.gainLoss,
                gain_loss_percent=holding.gainLossPercent,
                allocation=holding.allocation,
                created_at=holding.createdAt,
                updated_at=holding.updatedAt,
            ),
            message="Holding added successfully"
        )
    except Exception as e:
        logger.error(f"Add holding failed: {e}")
        raise

@router.put("/holdings/{holding_id}", response_model=UpdateHoldingResponse)
async def update_holding(
    holding_id: str,
    request: UpdateHoldingRequest,
    current_user_id: str = Depends(get_verified_user_id),
    db: Prisma = Depends(get_db)
):
    """Update a portfolio holding"""
    try:
        # Get user's portfolio
        portfolio = await db.portfolio.find_unique(
            where={"userId": current_user_id}
        )
        
        if not portfolio:
            raise PortfolioNotFoundException()
        
        # Get holding
        holding = await db.portfolioholding.find_first(
            where={
                "id": holding_id,
                "portfolioId": portfolio.id
            },
            include={"asset": True}
        )
        
        if not holding:
            raise HTTPException(
                status_code=404,
                detail="Holding not found"
            )
        
        # Prepare update data
        update_data = {}
        
        if request.quantity is not None:
            update_data["quantity"] = request.quantity
        if request.average_price is not None:
            update_data["averagePrice"] = request.average_price
        
        # Calculate new values
        quantity = request.quantity if request.quantity is not None else holding.quantity
        avg_price = request.average_price if request.average_price is not None else holding.averagePrice
        
        total_cost = quantity * avg_price
        total_value = quantity * holding.asset.currentPrice
        gain_loss = total_value - total_cost
        gain_loss_percent = (gain_loss / total_cost) * 100 if total_cost > 0 else 0
        
        update_data.update({
            "totalCost": total_cost,
            "totalValue": total_value,
            "gainLoss": gain_loss,
            "gainLossPercent": gain_loss_percent,
        })
        
        # Update holding
        updated_holding = await db.portfolioholding.update(
            where={"id": holding_id},
            data=update_data
        )
        
        # Update portfolio totals
        await _update_portfolio_totals(portfolio.id, db)
        
        return UpdateHoldingResponse(
            holding=HoldingResponse(
                id=updated_holding.id,
                portfolio_id=updated_holding.portfolioId,
                asset_id=updated_holding.assetId,
                symbol=updated_holding.symbol,
                quantity=updated_holding.quantity,
                average_price=updated_holding.averagePrice,
                current_price=updated_holding.currentPrice,
                total_value=updated_holding.totalValue,
                total_cost=updated_holding.totalCost,
                gain_loss=updated_holding.gainLoss,
                gain_loss_percent=updated_holding.gainLossPercent,
                allocation=updated_holding.allocation,
                created_at=updated_holding.createdAt,
                updated_at=updated_holding.updatedAt,
            ),
            message="Holding updated successfully"
        )
    except Exception as e:
        logger.error(f"Update holding failed: {e}")
        raise

@router.delete("/holdings/{holding_id}", response_model=RemoveHoldingResponse)
async def remove_holding(
    holding_id: str,
    current_user_id: str = Depends(get_verified_user_id),
    db: Prisma = Depends(get_db)
):
    """Remove a holding from portfolio"""
    try:
        # Get user's portfolio
        portfolio = await db.portfolio.find_unique(
            where={"userId": current_user_id}
        )
        
        if not portfolio:
            raise PortfolioNotFoundException()
        
        # Check if holding exists
        holding = await db.portfolioholding.find_first(
            where={
                "id": holding_id,
                "portfolioId": portfolio.id
            }
        )
        
        if not holding:
            raise HTTPException(
                status_code=404,
                detail="Holding not found"
            )
        
        # Delete holding
        await db.portfolioholding.delete(
            where={"id": holding_id}
        )
        
        # Update portfolio totals
        await _update_portfolio_totals(portfolio.id, db)
        
        return RemoveHoldingResponse(
            message="Holding removed successfully",
            success=True
        )
    except Exception as e:
        logger.error(f"Remove holding failed: {e}")
        raise

@router.get("/performance", response_model=PortfolioPerformanceResponse)
async def get_portfolio_performance(
    timeframe: str = Query("30d", pattern="^(7d|30d|90d|1y|all)$"),
    current_user_id: str = Depends(get_verified_user_id),
    db: Prisma = Depends(get_db)
):
    """Get portfolio performance data"""
    try:
        portfolio = await db.portfolio.find_unique(
            where={"userId": current_user_id}
        )
        
        if not portfolio:
            raise PortfolioNotFoundException()
        
        # Calculate date range
        end_date = datetime.now()
        if timeframe == "7d":
            start_date = end_date - timedelta(days=7)
        elif timeframe == "30d":
            start_date = end_date - timedelta(days=30)
        elif timeframe == "90d":
            start_date = end_date - timedelta(days=90)
        elif timeframe == "1y":
            start_date = end_date - timedelta(days=365)
        else:  # all
            start_date = portfolio.createdAt
        
        # Get performance data
        performance_data = await db.portfolioperformance.find_many(
            where={
                "portfolioId": portfolio.id,
                "date": {
                    "gte": start_date,
                    "lte": end_date
                }
            },
            order={"date": "asc"}
        )
        
        # Convert to response format
        performance_points = []
        for point in performance_data:
            performance_points.append(PerformanceDataPoint(
                date=point.date,
                total_value=point.totalValue,
                total_cost=point.totalCost,
                gain_loss=point.gainLoss,
                gain_loss_percent=point.gainLossPercent,
            ))
        
        # Calculate summary
        summary = {
            "start_value": performance_points[0].total_value if performance_points else 0,
            "end_value": performance_points[-1].total_value if performance_points else 0,
            "total_return": 0,
            "total_return_percent": 0,
        }
        
        if performance_points:
            summary["total_return"] = summary["end_value"] - summary["start_value"]
            if summary["start_value"] > 0:
                summary["total_return_percent"] = (summary["total_return"] / summary["start_value"]) * 100
        
        return PortfolioPerformanceResponse(
            portfolio_id=portfolio.id,
            timeframe=timeframe,
            performance_data=performance_points,
            summary=summary
        )
    except Exception as e:
        logger.error(f"Get portfolio performance failed: {e}")
        raise

@router.get("/analytics", response_model=PortfolioAnalyticsResponse)
async def get_portfolio_analytics(
    current_user_id: str = Depends(get_verified_user_id),
    db: Prisma = Depends(get_db)
):
    """Get portfolio analytics and insights"""
    try:
        portfolio = await db.portfolio.find_unique(
            where={"userId": current_user_id},
            include={
                "holdings": {
                    "include": {"asset": True}
                }
            }
        )
        
        if not portfolio:
            raise PortfolioNotFoundException()
        
        # Calculate analytics
        holdings = portfolio.holdings
        
        # Best and worst performers
        best_performer = None
        worst_performer = None
        
        if holdings:
            best_holding = max(holdings, key=lambda h: h.gainLossPercent)
            worst_holding = min(holdings, key=lambda h: h.gainLossPercent)
            
            best_performer = {
                "symbol": best_holding.symbol,
                "gain_loss_percent": best_holding.gainLossPercent,
                "gain_loss": best_holding.gainLoss,
            }
            
            worst_performer = {
                "symbol": worst_holding.symbol,
                "gain_loss_percent": worst_holding.gainLossPercent,
                "gain_loss": worst_holding.gainLoss,
            }
        
        # Asset allocation
        asset_allocation = []
        for holding in holdings:
            asset_allocation.append({
                "symbol": holding.symbol,
                "allocation": holding.allocation,
                "value": holding.totalValue,
            })
        
        # Risk metrics (simplified)
        risk_metrics = {
            "portfolio_volatility": 0.0,  # Would need historical data
            "sharpe_ratio": 0.0,  # Would need risk-free rate
            "beta": 1.0,  # Would need market benchmark
            "diversification_score": min(len(holdings) * 10, 100),  # Simple score
        }
        
        return PortfolioAnalyticsResponse(
            portfolio_id=portfolio.id,
            total_value=portfolio.totalValue,
            total_cost=portfolio.totalCost,
            total_gain_loss=portfolio.totalGainLoss,
            total_gain_loss_percent=portfolio.totalGainLossPercent,
            best_performer=best_performer,
            worst_performer=worst_performer,
            asset_allocation=asset_allocation,
            risk_metrics=risk_metrics,
        )
    except Exception as e:
        logger.error(f"Get portfolio analytics failed: {e}")
        raise

async def _update_portfolio_totals(portfolio_id: str, db: Prisma):
    """Update portfolio totals based on holdings"""
    try:
        # Get all holdings
        holdings = await db.portfolioholding.find_many(
            where={"portfolioId": portfolio_id}
        )
        
        total_value = sum(h.totalValue for h in holdings)
        total_cost = sum(h.totalCost for h in holdings)
        total_gain_loss = total_value - total_cost
        total_gain_loss_percent = (total_gain_loss / total_cost) * 100 if total_cost > 0 else 0
        
        # Update allocations
        for holding in holdings:
            allocation = (holding.totalValue / total_value) * 100 if total_value > 0 else 0
            await db.portfolioholding.update(
                where={"id": holding.id},
                data={"allocation": allocation}
            )
        
        # Update portfolio
        await db.portfolio.update(
            where={"id": portfolio_id},
            data={
                "totalValue": total_value,
                "totalCost": total_cost,
                "totalGainLoss": total_gain_loss,
                "totalGainLossPercent": total_gain_loss_percent,
                "lastUpdated": datetime.now(),
            }
        )
        
        logger.info(f"Portfolio totals updated: {portfolio_id}")
    except Exception as e:
        logger.error(f"Update portfolio totals failed: {e}")
        raise 