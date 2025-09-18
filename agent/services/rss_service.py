"""RSS feed processing service."""

import httpx
import feedparser
from datetime import datetime
from typing import Dict, Any, List
from loguru import logger

from models.api import ArticleInput
from config.settings import settings


class RSSService:
    """Service for handling RSS feed operations."""
    
    def __init__(self):
        self.client = httpx.AsyncClient(
            follow_redirects=True,
            timeout=settings.rss_timeout
        )
    
    async def fetch_feed(self, feed_url: str) -> Dict[str, Any]:
        """Fetch and parse an RSS feed."""
        try:
            logger.info(f"Fetching RSS feed from {feed_url}")
            response = await self.client.get(feed_url)
            response.raise_for_status()
            
            # Parse the feed
            feed = feedparser.parse(response.text)
            
            # Extract entries
            entries = []
            for entry in feed.entries:
                entry_data = {
                    "title": entry.get("title", ""),
                    "link": entry.get("link", ""),
                    "description": entry.get("description", ""),
                    "published": entry.get("published", ""),
                    "source": entry.get("source", {}).get("title", "Unknown Source"),
                    "content": self._extract_content(entry)
                }
                entries.append(entry_data)
            
            return {
                "title": feed.feed.get("title", "Unknown Feed"),
                "description": feed.feed.get("description", ""),
                "link": feed.feed.get("link", ""),
                "last_updated": feed.feed.get("updated", ""),
                "entry_count": len(entries),
                "entries": entries
            }
            
        except Exception as e:
            logger.error(f"Error fetching RSS feed: {e}")
            return {
                "error": str(e),
                "entries": []
            }
    
    async def enrich_articles(self, articles: List[ArticleInput]) -> List[ArticleInput]:
        """Enrich articles with additional content."""
        enriched_articles = []
        
        for article in articles:
            try:
                logger.debug(f"Enriching article: {article.title}")
                
                # For now, just return the article as-is
                # In the future, you could fetch full content from the URL
                enriched_article = article
                
                # If the article has minimal content, try to fetch more
                if not article.content and article.url:
                    try:
                        response = await self.client.get(article.url, timeout=10.0)
                        if response.status_code == 200:
                            # Simple content extraction - in production you'd want
                            # more sophisticated content extraction
                            enriched_article.content = response.text[:5000]  # Limit content size
                    except Exception as e:
                        logger.warning(f"Failed to fetch content for {article.url}: {e}")
                
                enriched_articles.append(enriched_article)
                
            except Exception as e:
                logger.error(f"Error enriching article: {e}")
                # Add the article anyway, even if enrichment failed
                enriched_articles.append(article)
        
        return enriched_articles
    
    def _extract_content(self, entry) -> str:
        """Extract content from a feed entry."""
        # Try different content fields
        if hasattr(entry, 'content') and entry.content:
            return entry.content[0].value if isinstance(entry.content, list) else str(entry.content)
        elif hasattr(entry, 'description') and entry.description:
            return entry.description
        elif hasattr(entry, 'summary') and entry.summary:
            return entry.summary
        else:
            return ""
    
    async def __aenter__(self):
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.client.aclose()