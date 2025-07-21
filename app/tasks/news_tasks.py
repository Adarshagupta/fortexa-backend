import asyncio
import httpx
from datetime import datetime, timedelta
from app.tasks.celery_app import celery_app
from app.core.database import init_db, db
from app.core.config import settings
from app.core.logger import logger

@celery_app.task(bind=True)
def fetch_news(self):
    """Fetch latest news articles"""
    try:
        asyncio.run(_fetch_news())
        logger.info("News fetched successfully")
        return {"status": "success", "message": "News fetched"}
    except Exception as e:
        logger.error(f"News fetching failed: {e}")
        return {"status": "error", "message": str(e)}

async def _fetch_news():
    """Internal async function to fetch news"""
    await init_db()
    
    # Mock news articles (in real implementation, use News API, RSS feeds, etc.)
    mock_articles = [
        {
            "title": "Bitcoin Reaches New All-Time High",
            "content": "Bitcoin has reached a new all-time high amid institutional adoption...",
            "summary": "Bitcoin sets new price record with institutional backing.",
            "author": "Crypto News Team",
            "source": "CryptoNews",
            "sourceUrl": "https://cryptonews.com/bitcoin-ath",
            "category": "cryptocurrency",
            "tags": ["bitcoin", "cryptocurrency", "price", "institutional"],
            "publishedAt": datetime.utcnow(),
            "sentiment": 0.8,
            "relevanceScore": 0.9,
        },
        {
            "title": "Ethereum 2.0 Staking Reaches Milestone",
            "content": "Ethereum 2.0 staking has reached a significant milestone with over 10 million ETH staked...",
            "summary": "Ethereum 2.0 staking shows strong community participation.",
            "author": "ETH Reporter",
            "source": "EthereumNews",
            "sourceUrl": "https://ethereumnews.com/eth2-staking",
            "category": "cryptocurrency",
            "tags": ["ethereum", "staking", "eth2", "milestone"],
            "publishedAt": datetime.utcnow() - timedelta(hours=2),
            "sentiment": 0.6,
            "relevanceScore": 0.7,
        },
        {
            "title": "Market Analysis: Altcoin Season Approaching",
            "content": "Technical analysis suggests that altcoin season may be approaching as Bitcoin dominance decreases...",
            "summary": "Technical indicators point to potential altcoin season.",
            "author": "Market Analyst",
            "source": "MarketWatch",
            "sourceUrl": "https://marketwatch.com/altcoin-season",
            "category": "analysis",
            "tags": ["altcoin", "market", "analysis", "bitcoin-dominance"],
            "publishedAt": datetime.utcnow() - timedelta(hours=4),
            "sentiment": 0.4,
            "relevanceScore": 0.8,
        },
    ]
    
    # Save articles to database
    for article_data in mock_articles:
        # Check if article already exists
        existing_article = await db.newsarticle.find_first(
            where={"sourceUrl": article_data["sourceUrl"]}
        )
        
        if not existing_article:
            await db.newsarticle.create(data=article_data)
            logger.info(f"Added news article: {article_data['title']}")
    
    logger.info(f"Processed {len(mock_articles)} news articles")

@celery_app.task(bind=True)
def analyze_news_sentiment(self):
    """Analyze sentiment of recent news articles"""
    try:
        asyncio.run(_analyze_news_sentiment())
        logger.info("News sentiment analysis completed")
        return {"status": "success", "message": "News sentiment analyzed"}
    except Exception as e:
        logger.error(f"News sentiment analysis failed: {e}")
        return {"status": "error", "message": str(e)}

async def _analyze_news_sentiment():
    """Internal async function to analyze news sentiment"""
    await init_db()
    
    # Get recent articles without sentiment analysis
    recent_articles = await db.newsarticle.find_many(
        where={
            "publishedAt": {"gte": datetime.utcnow() - timedelta(days=1)},
            "sentiment": None
        },
        take=50
    )
    
    for article in recent_articles:
        # Mock sentiment analysis (in real implementation, use NLP libraries)
        import random
        sentiment_score = random.uniform(-1, 1)
        
        # Update article with sentiment
        await db.newsarticle.update(
            where={"id": article.id},
            data={"sentiment": sentiment_score}
        )
    
    logger.info(f"Analyzed sentiment for {len(recent_articles)} articles")

@celery_app.task(bind=True)
def cleanup_old_news(self):
    """Clean up old news articles"""
    try:
        asyncio.run(_cleanup_old_news())
        logger.info("Old news cleaned up")
        return {"status": "success", "message": "Old news cleaned up"}
    except Exception as e:
        logger.error(f"News cleanup failed: {e}")
        return {"status": "error", "message": str(e)}

async def _cleanup_old_news():
    """Internal async function to cleanup old news"""
    await init_db()
    
    # Delete articles older than 30 days
    cutoff_date = datetime.utcnow() - timedelta(days=30)
    
    await db.newsarticle.delete_many(
        where={"publishedAt": {"lt": cutoff_date}}
    )
    
    logger.info("Old news cleanup completed") 