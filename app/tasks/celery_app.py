from celery import Celery
from app.core.config import settings

# Create Celery app
celery_app = Celery(
    "fortexa_worker",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=[
        "app.tasks.market_data_tasks",
        "app.tasks.notification_tasks",
        "app.tasks.portfolio_tasks",
        "app.tasks.news_tasks",
    ]
)

# Configure Celery
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes
    task_soft_time_limit=25 * 60,  # 25 minutes
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
)

# Celery Beat Schedule
celery_app.conf.beat_schedule = {
    "update-market-data": {
        "task": "app.tasks.market_data_tasks.update_market_data",
        "schedule": settings.MARKET_DATA_UPDATE_INTERVAL,
    },
    "update-portfolio-values": {
        "task": "app.tasks.portfolio_tasks.update_portfolio_values",
        "schedule": settings.PORTFOLIO_UPDATE_INTERVAL,
    },
    "fetch-news": {
        "task": "app.tasks.news_tasks.fetch_news",
        "schedule": settings.NEWS_UPDATE_INTERVAL,
    },
    "process-alerts": {
        "task": "app.tasks.notification_tasks.process_alerts",
        "schedule": 30,  # Every 30 seconds
    },
    "generate-trading-signals": {
        "task": "app.tasks.market_data_tasks.generate_trading_signals",
        "schedule": 300,  # Every 5 minutes
    },
}

# Task routes
celery_app.conf.task_routes = {
    "app.tasks.market_data_tasks.*": {"queue": "market_data"},
    "app.tasks.notification_tasks.*": {"queue": "notifications"},
    "app.tasks.portfolio_tasks.*": {"queue": "portfolio"},
    "app.tasks.news_tasks.*": {"queue": "news"},
} 