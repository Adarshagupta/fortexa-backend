import asyncio
from datetime import datetime, timedelta
from app.tasks.celery_app import celery_app
from app.core.database import init_db, db
from app.core.logger import logger

@celery_app.task(bind=True)
def process_alerts(self):
    """Process price alerts and send notifications"""
    try:
        asyncio.run(_process_alerts())
        logger.info("Alerts processed successfully")
        return {"status": "success", "message": "Alerts processed"}
    except Exception as e:
        logger.error(f"Alert processing failed: {e}")
        return {"status": "error", "message": str(e)}

async def _process_alerts():
    """Internal async function to process alerts"""
    await init_db()
    
    # Get active alerts
    alerts = await db.alert.find_many(
        where={"isActive": True, "isTriggered": False},
        include={"asset": True, "user": True}
    )
    
    for alert in alerts:
        current_price = alert.asset.currentPrice
        should_trigger = False
        
        # Check alert condition
        if alert.condition == "GREATER_THAN" and current_price >= alert.targetPrice:
            should_trigger = True
        elif alert.condition == "LESS_THAN" and current_price <= alert.targetPrice:
            should_trigger = True
        elif alert.condition == "PERCENT_CHANGE":
            # Calculate percentage change
            price_change = ((current_price - alert.currentPrice) / alert.currentPrice) * 100
            if abs(price_change) >= alert.targetPrice:  # targetPrice used as threshold
                should_trigger = True
        
        if should_trigger:
            # Mark alert as triggered
            await db.alert.update(
                where={"id": alert.id},
                data={
                    "isTriggered": True,
                    "triggeredAt": datetime.utcnow(),
                    "currentPrice": current_price,
                }
            )
            
            # Create notification
            message = f"{alert.asset.symbol} price alert: ${current_price:.2f}"
            await db.notification.create(
                data={
                    "userId": alert.userId,
                    "title": "Price Alert Triggered",
                    "message": message,
                    "type": "PRICE_ALERT",
                    "category": "trading",
                    "data": {
                        "alert_id": alert.id,
                        "asset_id": alert.assetId,
                        "symbol": alert.asset.symbol,
                        "current_price": current_price,
                        "target_price": alert.targetPrice,
                    },
                    "isRead": False,
                    "isPush": True,
                    "isEmail": True,
                }
            )
            
            logger.info(f"Alert triggered for {alert.asset.symbol}: {current_price}")
    
    logger.info(f"Processed {len(alerts)} alerts")

@celery_app.task(bind=True)
def send_notification(self, user_id: str, title: str, message: str, notification_type: str = "SYSTEM_ALERT"):
    """Send notification to user"""
    try:
        asyncio.run(_send_notification(user_id, title, message, notification_type))
        return {"status": "success", "message": "Notification sent"}
    except Exception as e:
        logger.error(f"Notification sending failed: {e}")
        return {"status": "error", "message": str(e)}

async def _send_notification(user_id: str, title: str, message: str, notification_type: str):
    """Internal async function to send notification"""
    await init_db()
    
    # Create notification
    await db.notification.create(
        data={
            "userId": user_id,
            "title": title,
            "message": message,
            "type": notification_type,
            "isRead": False,
            "isPush": True,
            "isEmail": False,
        }
    )
    
    logger.info(f"Notification sent to user {user_id}: {title}")

@celery_app.task(bind=True)
def cleanup_old_notifications(self):
    """Clean up old notifications"""
    try:
        asyncio.run(_cleanup_old_notifications())
        logger.info("Old notifications cleaned up")
        return {"status": "success", "message": "Old notifications cleaned up"}
    except Exception as e:
        logger.error(f"Notification cleanup failed: {e}")
        return {"status": "error", "message": str(e)}

async def _cleanup_old_notifications():
    """Internal async function to cleanup old notifications"""
    await init_db()
    
    # Delete notifications older than 30 days
    cutoff_date = datetime.utcnow() - timedelta(days=30)
    
    await db.notification.delete_many(
        where={"createdAt": {"lt": cutoff_date}}
    )
    
    logger.info("Old notifications cleanup completed") 