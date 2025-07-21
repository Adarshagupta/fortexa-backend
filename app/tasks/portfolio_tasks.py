import asyncio
from datetime import datetime, timedelta
from app.tasks.celery_app import celery_app
from app.core.database import init_db, db
from app.core.logger import logger

@celery_app.task(bind=True)
def update_portfolio_values(self):
    """Update all portfolio values based on current asset prices"""
    try:
        asyncio.run(_update_portfolio_values())
        logger.info("Portfolio values updated successfully")
        return {"status": "success", "message": "Portfolio values updated"}
    except Exception as e:
        logger.error(f"Portfolio value update failed: {e}")
        return {"status": "error", "message": str(e)}

async def _update_portfolio_values():
    """Internal async function to update portfolio values"""
    await init_db()
    
    # Get all portfolios with holdings
    portfolios = await db.portfolio.find_many(
        include={"holdings": {"include": {"asset": True}}}
    )
    
    for portfolio in portfolios:
        total_value = 0
        total_cost = 0
        
        # Update each holding
        for holding in portfolio.holdings:
            current_price = holding.asset.currentPrice
            total_value_holding = holding.quantity * current_price
            total_cost_holding = holding.quantity * holding.averagePrice
            gain_loss = total_value_holding - total_cost_holding
            gain_loss_percent = (gain_loss / total_cost_holding) * 100 if total_cost_holding > 0 else 0
            
            # Update holding
            await db.portfolioholding.update(
                where={"id": holding.id},
                data={
                    "currentPrice": current_price,
                    "totalValue": total_value_holding,
                    "gainLoss": gain_loss,
                    "gainLossPercent": gain_loss_percent,
                }
            )
            
            total_value += total_value_holding
            total_cost += total_cost_holding
        
        # Update portfolio totals
        portfolio_gain_loss = total_value - total_cost
        portfolio_gain_loss_percent = (portfolio_gain_loss / total_cost) * 100 if total_cost > 0 else 0
        
        await db.portfolio.update(
            where={"id": portfolio.id},
            data={
                "totalValue": total_value,
                "totalCost": total_cost,
                "totalGainLoss": portfolio_gain_loss,
                "totalGainLossPercent": portfolio_gain_loss_percent,
                "lastUpdated": datetime.utcnow(),
            }
        )
        
        # Update allocations
        for holding in portfolio.holdings:
            allocation = (holding.totalValue / total_value) * 100 if total_value > 0 else 0
            await db.portfolioholding.update(
                where={"id": holding.id},
                data={"allocation": allocation}
            )
        
        # Create performance snapshot
        await db.portfolioperformance.create(
            data={
                "portfolioId": portfolio.id,
                "date": datetime.utcnow(),
                "totalValue": total_value,
                "totalCost": total_cost,
                "gainLoss": portfolio_gain_loss,
                "gainLossPercent": portfolio_gain_loss_percent,
            }
        )
    
    logger.info(f"Updated {len(portfolios)} portfolios")

@celery_app.task(bind=True)
def generate_portfolio_report(self, user_id: str):
    """Generate portfolio performance report for a user"""
    try:
        asyncio.run(_generate_portfolio_report(user_id))
        return {"status": "success", "message": "Portfolio report generated"}
    except Exception as e:
        logger.error(f"Portfolio report generation failed: {e}")
        return {"status": "error", "message": str(e)}

async def _generate_portfolio_report(user_id: str):
    """Internal async function to generate portfolio report"""
    await init_db()
    
    # Get user's portfolio
    portfolio = await db.portfolio.find_unique(
        where={"userId": user_id},
        include={"holdings": {"include": {"asset": True}}}
    )
    
    if not portfolio:
        return
    
    # Generate report data
    report_data = {
        "user_id": user_id,
        "portfolio_id": portfolio.id,
        "generated_at": datetime.utcnow(),
        "total_value": portfolio.totalValue,
        "total_gain_loss": portfolio.totalGainLoss,
        "holdings_count": len(portfolio.holdings),
        "best_performer": None,
        "worst_performer": None,
    }
    
    # Find best and worst performers
    if portfolio.holdings:
        best_holding = max(portfolio.holdings, key=lambda h: h.gainLossPercent)
        worst_holding = min(portfolio.holdings, key=lambda h: h.gainLossPercent)
        
        report_data["best_performer"] = {
            "symbol": best_holding.symbol,
            "gain_loss_percent": best_holding.gainLossPercent,
        }
        report_data["worst_performer"] = {
            "symbol": worst_holding.symbol,
            "gain_loss_percent": worst_holding.gainLossPercent,
        }
    
    # TODO: Save report or send notification
    logger.info(f"Generated portfolio report for user {user_id}")
    return report_data 