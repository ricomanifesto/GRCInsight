"""Resolve model selections while preserving request-local article identity."""

from typing import Any, overload

from core.entities import analyze_article_grc_content, detect_risk_categories
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


def article_text(article: ArticleInput) -> str:
    """The text local entity and risk-category rules read."""
    return "\n".join(filter(None, [article.title, article.summary, article.content]))


def local_overrides(article: ArticleInput) -> tuple[bool, bool]:
    """Return the local entity signal and the local risk-category signal."""
    entity = bool(analyze_article_grc_content(article.model_dump()).get("has_grc_content"))
    return entity, bool(detect_risk_categories(article_text(article)))


@overload
def workflow_selected(*, entity: bool, risk: bool, model: bool) -> bool: ...


@overload
def workflow_selected(*, entity: bool, risk: bool, model: bool | None) -> bool | None: ...


def workflow_selected(*, entity: bool, risk: bool, model: bool | None) -> bool | None:
    """The report workflow's effective selection: entity OR risk category OR model.

    An unknown model selection (None) never becomes a drop: the result stays
    unknown unless a local signal already selects the article.
    """
    if entity or risk or model:
        return True
    return None if model is None else False


@overload
def analyze_selected(*, entity: bool, model: bool) -> bool: ...


@overload
def analyze_selected(*, entity: bool, model: bool | None) -> bool | None: ...


def analyze_selected(*, entity: bool, model: bool | None) -> bool | None:
    """The /analyze effective selection, which has no risk-category override."""
    return workflow_selected(entity=entity, risk=False, model=model)
