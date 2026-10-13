"""Resolve model selections while preserving request-local article identity."""

from typing import Any

from models.api import ArticleInput


def selected_article_mask(articles: list[ArticleInput], analysis: dict[str, Any]) -> list[bool]:
    """Use typed positions when supplied, otherwise retain legacy matching."""
    if "grc_article_indices" in analysis:
        indices = analysis["grc_article_indices"]
        if (
            not isinstance(indices, list)
            or any(type(index) is not int or not 0 <= index < len(articles) for index in indices)
            or len(set(indices)) != len(indices)
        ):
            raise ValueError("Invalid article selection positions")
        selected = set(indices)
        return [index in selected for index in range(len(articles))]
    identified = analysis.get("grc_articles", []) or []
    urls = {item.get("url") for item in identified if isinstance(item, dict) and item.get("url")}
    titles = {
        item.get("title") for item in identified if isinstance(item, dict) and item.get("title")
    }
    return [article.url in urls or article.title in titles for article in articles]
