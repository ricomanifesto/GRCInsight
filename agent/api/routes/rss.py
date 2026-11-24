"""RSS feed processing endpoints."""

from fastapi import APIRouter, Body, Depends, HTTPException
from loguru import logger
from typing import List

from models.api import RSSFeedResponse, ArticleInput, MAX_ARTICLES, validate_article_batch
from services.rss_service import RSSService
from api.security import require_api_key, require_work_budget

router = APIRouter(dependencies=[Depends(require_api_key)])
rss_service = RSSService()


@router.post(
    "/rss/fetch", response_model=RSSFeedResponse, dependencies=[Depends(require_work_budget)]
)
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
            entries=feed_data.get("entries", []),
        )

    except Exception as e:
        logger.error(f"RSS feed fetch failed: {str(e)}")
        return RSSFeedResponse(title="Error", entry_count=0, error="RSS feed fetch failed")


@router.post("/rss/enrich", dependencies=[Depends(require_work_budget)])
async def enrich_articles(articles: List[ArticleInput] = Body(max_length=MAX_ARTICLES)):
    """Enrich articles with additional content."""
    logger.info(f"Enriching {len(articles)} articles")

    try:
        validate_article_batch(articles)
    except ValueError:
        raise HTTPException(status_code=422, detail="Article batch exceeds the server limit")
    try:
        enriched_articles = await rss_service.enrich_articles(articles)

        return {"status": "success", "articles": enriched_articles}

    except Exception as e:
        logger.error(f"Article enrichment failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Article enrichment failed")
