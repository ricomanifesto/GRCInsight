"""RSS feed processing service."""

import feedparser
from typing import Dict, Any, List
from loguru import logger

from models.api import ArticleInput
from config.settings import settings
from services.public_fetch import fetch_public_text

# Publisher pages fetched for empty feed items are kept up to this length.
PAGE_CONTENT_LIMIT = 5000
PAGE_BYTE_LIMIT = 65536
PAGE_FETCH_TIMEOUT = 10.0
FEED_BYTE_LIMIT = 2 * 1024 * 1024


class RSSService:
    """Service for handling RSS feed operations."""

    def __init__(self):
        self.timeout = float(settings.rss_timeout)

    async def fetch_feed(self, feed_url: str) -> Dict[str, Any]:
        """Fetch and parse an RSS feed."""
        try:
            logger.info(f"Fetching RSS feed from {feed_url}")
            response_text, truncated = await fetch_public_text(
                feed_url, max_bytes=FEED_BYTE_LIMIT, timeout=self.timeout
            )
            if truncated:
                raise ValueError("RSS feed exceeded the response byte limit")
            if not response_text.strip():
                raise ValueError("RSS feed response was empty")

            # Parse the feed
            feed = feedparser.parse(response_text)
            if feed.bozo and not feed.entries:
                raise ValueError(f"RSS feed parsing failed: {feed.bozo_exception}")
            metadata_keys = set(feed.feed.keys())
            has_feed_metadata = any(
                field in metadata_keys and str(feed.feed[field]).strip()
                for field in ("title", "link", "subtitle", "updated", "id")
            )
            if not feed.entries and not has_feed_metadata:
                raise ValueError("RSS payload contained no feed metadata or entries")

            # Extract entries
            entries = []
            for entry in feed.entries:
                entry_data = {
                    "title": entry.get("title", ""),
                    "link": entry.get("link", ""),
                    "description": entry.get("description", ""),
                    "published": entry.get("published", ""),
                    "source": entry.get("source", {}).get("title", "Unknown Source"),
                    "content": self._extract_content(entry),
                }
                entries.append(entry_data)

            return {
                "title": feed.feed.get("title", "Unknown Feed"),
                "description": feed.feed.get("description", ""),
                "link": feed.feed.get("link", ""),
                "last_updated": feed.feed.get("updated", ""),
                "entry_count": len(entries),
                "entries": entries,
            }

        except Exception as e:
            logger.error(f"Error fetching RSS feed: {e}")
            return {"error": str(e), "entries": []}

    async def enrich_articles(self, articles: List[ArticleInput]) -> List[ArticleInput]:
        """Enrich articles with additional content."""
        for article in articles:
            if not article.content and article.url:
                try:
                    content, truncated = await fetch_public_text(
                        article.url, max_bytes=PAGE_BYTE_LIMIT, timeout=PAGE_FETCH_TIMEOUT
                    )
                    article.content = content[:PAGE_CONTENT_LIMIT]
                    article.content_origin = "publisher_page"
                    article.content_truncated = truncated or len(content) > PAGE_CONTENT_LIMIT
                except Exception as error:
                    # Enrichment is optional; preserve the feed item on policy/network failure.
                    logger.warning("Publisher enrichment unavailable: {}", type(error).__name__)
        return articles

    def _extract_content(self, entry) -> str:
        """Extract content from a feed entry."""
        # Try different content fields
        if hasattr(entry, "content") and entry.content:
            return entry.content[0].value if isinstance(entry.content, list) else str(entry.content)
        elif hasattr(entry, "description") and entry.description:
            return entry.description
        elif hasattr(entry, "summary") and entry.summary:
            return entry.summary
        else:
            return ""

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        return None
