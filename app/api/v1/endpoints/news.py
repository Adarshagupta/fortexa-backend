from fastapi import APIRouter, Depends, Query
from prisma import Prisma
from app.core.database import get_db
from app.schemas.news import NewsResponse, NewsListResponse
from app.core.logger import logger
from typing import List, Optional

router = APIRouter()

@router.get("/", response_model=NewsListResponse)
async def get_news(
    limit: int = Query(10, ge=1, le=50),
    category: Optional[str] = Query(None),
    db: Prisma = Depends(get_db)
):
    """Get latest news"""
    try:
        # Build where clause
        where_clause = {"isActive": True}
        if category:
            where_clause["category"] = category
        
        # Get news articles
        news_articles = await db.newsarticle.find_many(
            where=where_clause,
            order={"publishedAt": "desc"},
            take=limit
        )
        
        # Convert to response
        news_responses = []
        for article in news_articles:
            news_responses.append(NewsResponse(
                id=article.id,
                title=article.title,
                content=article.content,
                summary=article.summary,
                author=article.author,
                source=article.source,
                source_url=article.sourceUrl,
                image_url=article.imageUrl,
                category=article.category,
                tags=article.tags,
                published_at=article.publishedAt,
                sentiment=article.sentiment,
                relevance_score=article.relevanceScore,
                is_active=article.isActive,
                created_at=article.createdAt,
                updated_at=article.updatedAt,
            ))
        
        return NewsListResponse(
            news=news_responses,
            total_count=len(news_responses),
            category=category
        )
    except Exception as e:
        logger.error(f"Get news failed: {e}")
        # Return empty list if no news found
        return NewsListResponse(
            news=[],
            total_count=0,
            category=category
        )

@router.get("/{news_id}", response_model=NewsResponse)
async def get_news_article(
    news_id: str,
    db: Prisma = Depends(get_db)
):
    """Get a specific news article"""
    try:
        article = await db.newsarticle.find_unique(
            where={"id": news_id}
        )
        
        if not article:
            return {"error": "News article not found"}
            
        return NewsResponse(
            id=article.id,
            title=article.title,
            content=article.content,
            summary=article.summary,
            author=article.author,
            source=article.source,
            source_url=article.sourceUrl,
            image_url=article.imageUrl,
            category=article.category,
            tags=article.tags,
            published_at=article.publishedAt,
            sentiment=article.sentiment,
            relevance_score=article.relevanceScore,
            is_active=article.isActive,
            created_at=article.createdAt,
            updated_at=article.updatedAt,
        )
    except Exception as e:
        logger.error(f"Get news article failed: {e}")
        return {"error": "Failed to fetch news article"}

@router.get("/public", response_model=List[NewsResponse])
async def get_public_news(
    limit: int = Query(5, ge=1, le=20),
    db: Prisma = Depends(get_db)
):
    """Get public news (no auth required)"""
    try:
        news_articles = await db.newsarticle.find_many(
            where={"isActive": True},
            order={"publishedAt": "desc"},
            take=limit
        )
        
        # Convert to response
        news_responses = []
        for article in news_articles:
            news_responses.append(NewsResponse(
                id=article.id,
                title=article.title,
                content=article.content,
                summary=article.summary,
                author=article.author,
                source=article.source,
                source_url=article.sourceUrl,
                image_url=article.imageUrl,
                category=article.category,
                tags=article.tags,
                published_at=article.publishedAt,
                sentiment=article.sentiment,
                relevance_score=article.relevanceScore,
                is_active=article.isActive,
                created_at=article.createdAt,
                updated_at=article.updatedAt,
            ))
        
        return news_responses
    except Exception as e:
        logger.error(f"Get public news failed: {e}")
        # Return empty list if no news found
        return [] 
    return {"message": "Public news endpoint - implementation needed"} 