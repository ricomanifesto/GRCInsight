"""RSS feed processing endpoints."""

from fastapi import APIRouter, HTTPException
from loguru import logger
from typing import List

from models.api import RSSFeedResponse, ArticleInput
from services.rss_service import RSSService

router = APIRouter()
rss_service = RSSService()


@router.post("/rss/fetch", response_model=RSSFeedResponse)
async def fetch_rss_feed(feed_url: str):
    """Fetch and parse an RSS feed."""
    logger.info(f"Fetching RSS feed: {feed_url}")
    
    try:
        feed_data = await rss_service.fetch_feed(feed_url)
        
        return RSSFeedResponse(
            title=feed_data.get("title", "Unknown Feed"),
            description=feed_data.get("description", ""),
            link=feed_data.get("link", ""),
            last_updated=feed_data.get("last_updated", ""),
            entry_count=feed_data.get("entry_count", 0),
            entries=feed_data.get("entries", [])
        )
        
    except Exception as e:
        logger.error(f"RSS feed fetch failed: {str(e)}")
        return RSSFeedResponse(
            title="Error",
            entry_count=0,
            error=str(e)
        )


@router.post("/rss/enrich")
async def enrich_articles(articles: List[ArticleInput]):
    """Enrich articles with additional content."""
    logger.info(f"Enriching {len(articles)} articles")
    
    try:
        enriched_articles = await rss_service.enrich_articles(articles)
        
        return {
            "status": "success",
            "articles": enriched_articles
        }
        
    except Exception as e:
        logger.error(f"Article enrichment failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Article enrichment failed: {str(e)}"
        )