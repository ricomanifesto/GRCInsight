"""Turn a completed ``WorkflowResponse`` into the retained report and article records.

Field mapping follows the existing Lambda writeback (top-level report fields plus
the metadata map, articles with their GRC entity lists). Two deliberate MVP
differences: article ``published`` keeps the article's own timestamp (the
writeback's ``model_dump()`` yields a datetime and falls back to writeback time),
and identity validation rejects any result whose provenance does not match the
frozen submission. Provenance is never repaired.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from core.reporting_identity import (
    ReportingIdentityError,
    sentrydigest_issue_url,
    sentrydigest_item_url,
)
from models.api import WorkflowResponse

ROUTING_ALIASES = {"openrouter/free", "openrouter/auto"}


class InvalidResult(ValueError):
    """A completed workflow response that cannot be retained as this report's outcome."""


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def build_product_record(
    response: WorkflowResponse, submission: dict[str, Any]
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    if response.status != "completed":
        raise InvalidResult("response is not completed")
    if response.report is None or response.metadata is None or response.articles is None:
        raise InvalidResult("completed response lacks report, metadata or articles")
    report, md, articles = response.report, response.metadata, response.articles
    if not report.title.strip() or not report.content.strip():
        raise InvalidResult("report title or content is empty")
    if md.analysis_mode not in {"model", "fallback"}:
        raise InvalidResult("analysis_mode is not model or fallback")
    if md.source_url != submission["feed_url"]:
        raise InvalidResult("metadata.source_url does not match the frozen feed URL")
    if md.requested_model != submission["config"]["model"]:
        raise InvalidResult("metadata.requested_model does not match the frozen model")
    if md.analysis_mode == "model":
        if not md.resolved_model or md.resolved_model in ROUTING_ALIASES:
            raise InvalidResult("model-mode result lacks an attested resolved model")
        if not isinstance(md.report_plan, dict) or md.fallback_reason is not None:
            raise InvalidResult("model-mode result lacks its report plan")
    else:
        if not md.fallback_reason or md.report_plan is not None or md.resolved_model:
            raise InvalidResult("fallback result does not record its fallback reason")
    if not articles:
        raise InvalidResult("completed response retains no articles")
    if md.article_count != len(articles):
        raise InvalidResult("metadata.article_count does not match the retained articles")
    if not 0 <= md.grc_article_count <= md.article_count:
        raise InvalidResult("metadata.grc_article_count is out of range")
    try:
        expected_issue_url = sentrydigest_issue_url(md.source_home_url, md.source_issue_date)
        if md.source_issue_url != expected_issue_url:
            raise InvalidResult("metadata.source_issue_url does not match its issue identity")
        urls = []
        for article in articles:
            if article.digest_url != sentrydigest_item_url(
                md.source_home_url, md.source_issue_date, article.url
            ):
                raise InvalidResult("article digest_url does not match its reporting identity")
            urls.append(article.url)
        if len(set(urls)) != len(urls):
            raise InvalidResult("articles repeat a URL")
        if len({article.source for article in articles}) != 1:
            raise InvalidResult("articles do not share one feed source")
        if not md.source_articles or len(md.source_articles) > len(articles):
            raise InvalidResult("metadata.source_articles is empty or larger than the article set")
        by_url = {article.url: article for article in articles}
        for source in md.source_articles:
            article = by_url.get(source.get("url"))
            if article is None or source.get("title") != article.title:
                raise InvalidResult("source evidence names an article outside the result")
            if source.get("digest_url") != article.digest_url:
                raise InvalidResult("source evidence digest_url does not match its article")
    except ReportingIdentityError as error:
        raise InvalidResult(f"reporting identity is invalid: {error}") from error

    now_iso = _now_iso()
    metadata = {
        "article_count": md.article_count,
        "grc_article_count": md.grc_article_count,
        "analysis_mode": md.analysis_mode,
        "fallback_reason": md.fallback_reason,
        "source_name": md.source_name,
        "source_url": md.source_url,
        "source_home_url": md.source_home_url,
        "source_issue_date": md.source_issue_date,
        "source_issue_url": md.source_issue_url,
        "analysis_period": md.analysis_period,
        "requested_model": md.requested_model,
        "resolved_model": md.resolved_model,
        "source_articles": md.source_articles or [],
        "report_plan": md.report_plan,
        "regulations_mentioned": md.regulations_mentioned or [],
        "frameworks_referenced": md.frameworks_referenced or [],
        "industries_affected": md.industries_affected or [],
        "regulatory_bodies": md.regulatory_bodies or [],
    }
    record = {
        "title": report.title,
        "content": report.content,
        "status": "completed",
        "source_url": md.source_url,
        "generated_at": now_iso,
        "metadata": metadata,
    }
    retained = []
    for article in articles:
        dumped = article.model_dump(mode="json")
        retained.append(
            {
                "title": dumped["title"],
                "url": dumped["url"],
                "content": dumped.get("content", ""),
                "summary": dumped.get("summary", ""),
                "source": dumped.get("source", ""),
                "digest_url": dumped.get("digest_url", ""),
                "published": dumped.get("published") or now_iso,
                "has_grc_content": bool(dumped.get("has_grc_content", False)),
                "regulations": dumped.get("regulations", []) or [],
                "frameworks": dumped.get("frameworks", []) or [],
                "industries": dumped.get("industries", []) or [],
                "regulatory_bodies": dumped.get("regulatory_bodies", []) or [],
            }
        )
    return record, retained
