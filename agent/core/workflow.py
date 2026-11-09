"""LangGraph workflow for FastAPI service."""

from collections import Counter
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
import re
from typing import Dict, Any, List
from urllib.parse import urljoin, urlparse
from loguru import logger

from models.api import (
    WorkflowResponse,
    Report,
    ReportMetadata,
    APIError,
    GRCAnalysisConfig,
    ArticleInput,
    ArticleRecord,
)
from services.rss_service import RSSService
from services.model_service import GRCModelService
from services.regulatory_sources import enrich_regulatory_sources
from core.article_evidence import capture_article_evidence
from core.content_policy import contains_virtual_event
from core.article_selection import article_text, selected_article_mask, workflow_selected
from core.entities import analyze_article_grc_content, detect_risk_categories
from core.reporting_identity import (
    ReportingIdentityError,
    normalize_reporting_url,
    sentrydigest_issue_date,
    sentrydigest_issue_url,
    sentrydigest_item_url,
)

# Initialize services
rss_service = RSSService()

SOURCE_EVIDENCE_LIMIT = 12
REPORT_CVE_LIMIT = 10
REPORT_CVE_EVIDENCE_LIMIT = min(REPORT_CVE_LIMIT, SOURCE_EVIDENCE_LIMIT - 2)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _build_article_reason(local: Dict[str, Any], risk_categories: List[str]) -> str:
    """Create a compact reviewer-facing reason for article relevance."""
    if local.get("regulations"):
        return f"Regulation references: {', '.join(local['regulations'][:2])}"
    if local.get("frameworks"):
        return f"Framework references: {', '.join(local['frameworks'][:2])}"
    if local.get("regulatory_bodies"):
        return f"Regulatory bodies: {', '.join(local['regulatory_bodies'][:2])}"
    if risk_categories:
        return f"Risk themes: {', '.join(risk_categories[:2])}"
    return "Operational and compliance monitoring signal"


def _extract_cves(text: str) -> List[str]:
    """Extract valid-shape CVE identifiers while preserving first-seen order."""
    seen = set()
    cves = []
    for match in re.finditer(r"\bCVE-\d{4}-\d{4,}\b", text, re.IGNORECASE):
        cve = match.group(0).upper()
        if cve not in seen:
            seen.add(cve)
            cves.append(cve)
    return cves


def _canonical_public_url(value: str, field: str) -> str:
    """Normalize the WHATWG-aligned URL identity used by SentryDigest cards."""
    if not str(value or "").strip():
        raise ValueError(f"{field} must be a credential-free HTTP URL")
    try:
        return normalize_reporting_url(value)
    except ReportingIdentityError as error:
        raise ValueError(f"{field}: {error}") from error


def _sentrydigest_issue_date(feed_data: Dict[str, Any]) -> str:
    """Return the UTC issue date attested by the fetched RSS channel."""
    try:
        return sentrydigest_issue_date(feed_data.get("last_updated"))
    except ReportingIdentityError as error:
        raise ValueError(str(error)) from error


def _sentrydigest_issue_url(feed_home_url: str, issue_date: str) -> str:
    """Build the retained issue URL owned by SentryDigest."""
    try:
        return sentrydigest_issue_url(feed_home_url, issue_date)
    except ReportingIdentityError as error:
        raise ValueError(str(error)) from error


def _sentrydigest_item_url(feed_home_url: str, issue_date: str, article_url: str) -> str:
    """Build the dated item permalink defined by SentryDigest identity."""
    try:
        return sentrydigest_item_url(feed_home_url, issue_date, article_url)
    except ReportingIdentityError as error:
        raise ValueError(str(error)) from error


def _build_source_evidence(
    enriched_articles: List[ArticleInput],
) -> List[Dict[str, Any]]:
    """Build bounded current-source evidence for report-specific claims."""
    evidence: List[Dict[str, Any]] = []
    for article in enriched_articles:
        text = "\n".join(filter(None, [article.title, article.summary, article.content]))
        evidence.append(
            {
                "title": article.title,
                "url": article.url,
                "digest_url": article.digest_url,
                "snippet": re.sub(r"\s+", " ", text).strip()[:700],
                "article_evidence": capture_article_evidence(
                    summary=article.summary, content=article.content
                ),
                "cves": _extract_cves(text),
            }
        )

    selected_indices = []
    selected_index_set = set()
    selected_cves = set()

    def add(index: int) -> bool:
        if len(selected_indices) >= SOURCE_EVIDENCE_LIMIT or index in selected_index_set:
            return False
        selected_indices.append(index)
        selected_index_set.add(index)
        return True

    # Preserve evidence for distinct CVEs across the entire feed. Repeated
    # coverage of one CVE must not consume the bounded evidence budget.
    for index, item in enumerate(evidence):
        if len(selected_cves) >= REPORT_CVE_LIMIT:
            break
        new_cves = [cve for cve in item["cves"] if cve not in selected_cves]
        if new_cves and add(index):
            selected_cves.update(new_cves[: REPORT_CVE_LIMIT - len(selected_cves)])
        if len(selected_indices) >= REPORT_CVE_EVIDENCE_LIMIT:
            break

    for index in range(len(evidence)):
        add(index)

    selected = [evidence[index] for index in selected_indices]
    allowed_cves: set[str] = set()
    for item in selected:
        for cve in item["cves"]:
            if len(allowed_cves) >= REPORT_CVE_LIMIT:
                break
            allowed_cves.add(cve)
    bounded_evidence = []
    for item in selected:
        identity_cves = _extract_cves(f'{item["title"]}\n{item["url"]}')
        retained_cves = [cve for cve in item["cves"] if cve in allowed_cves]
        retained_cves.extend(cve for cve in identity_cves if cve not in retained_cves)
        bounded_evidence.append(
            {
                **item,
                "cves": retained_cves,
            }
        )
    return bounded_evidence


def _build_local_analysis(enriched_articles: List[ArticleInput]):
    """Build deterministic article analysis for no-LLM fallback mode."""
    regulations = set()
    frameworks = set()
    industries = set()
    regulatory_bodies = set()
    risk_counter: Counter[str] = Counter()
    local_signals: List[Dict[str, Any]] = []
    grc_articles = []

    for article in enriched_articles:
        local = analyze_article_grc_content(article.model_dump())
        risk_categories = detect_risk_categories(article_text(article))
        entity_signal = bool(local.get("has_grc_content", False))
        has_grc = workflow_selected(entity=entity_signal, risk=bool(risk_categories), model=False)

        local["entity_signal"] = entity_signal
        local["has_grc_content"] = has_grc
        local["risk_categories"] = risk_categories
        local_signals.append(local)

        regulations.update(local.get("regulations", []))
        frameworks.update(local.get("frameworks", []))
        industries.update(local.get("industries", []))
        regulatory_bodies.update(local.get("regulatory_bodies", []))
        risk_counter.update(risk_categories)

        if has_grc:
            grc_articles.append(
                {
                    "title": article.title,
                    "url": article.url,
                    "reason": _build_article_reason(local, risk_categories),
                }
            )

    grc_count = sum(1 for signal in local_signals if signal.get("has_grc_content"))
    analysis = {
        "grc_articles": grc_articles,
        "summary": {
            "total_articles": len(enriched_articles),
            "grc_relevant_count": grc_count,
            "confidence_score": 0.35,
        },
        "analysis": {
            "regulations_mentioned": sorted(regulations),
            "frameworks_referenced": sorted(frameworks),
            "industries_affected": sorted(industries),
            "regulatory_bodies": sorted(regulatory_bodies),
            "risk_categories": [name for name, _ in risk_counter.most_common(6)],
        },
    }
    return local_signals, analysis


def _relevance_diagnostics(model_service: Any) -> Dict[str, Any] | None:
    """The report's relevance evidence; never allowed to affect report generation."""
    summarize = getattr(model_service, "relevance_summary", None)
    if not callable(summarize):
        return None
    try:
        return summarize()
    except Exception:
        logger.warning("Article relevance summary was unavailable for this report")
        return None


def _unavailable_report_content(title: str, generated_at: datetime) -> str:
    """Body stored for a refused run.

    Publication refuses every report whose analysis mode is not ``model``, so a
    refused run carries no report sections. The reason stays in metadata.
    """
    return "\n".join(
        [
            f"# {title} - Unavailable",
            f"**Generated:** {generated_at.isoformat().replace('+00:00', 'Z')}",
            "",
            "Model-backed analysis was unavailable, so this run produced no publishable report.",
            "",
        ]
    )


async def run_grc_analysis_endpoint(
    feed_url: str,
    config: GRCAnalysisConfig,
    model_deadline: float | None = None,
) -> WorkflowResponse:
    """
    Main workflow endpoint that orchestrates the complete GRC analysis.
    """
    logger.info(f"Starting GRC analysis workflow for feed: {feed_url}")

    try:
        # Step 1: Fetch RSS feed
        logger.info("Step 1: Fetching RSS feed")
        feed_data = await rss_service.fetch_feed(feed_url)

        if "error" in feed_data:
            return WorkflowResponse(
                status="failed",
                error=APIError(
                    code="RSS_FETCH_FAILED",
                    message="Failed to fetch RSS feed",
                    details=feed_data["error"],
                ),
            )

        # Step 2: Convert entries to ArticleInput format
        logger.info("Step 2: Processing feed entries")
        try:
            feed_home_url = _canonical_public_url(str(feed_data.get("link") or ""), "feed home URL")
            source_issue_date = _sentrydigest_issue_date(feed_data)
            source_issue_url = _sentrydigest_issue_url(feed_home_url, source_issue_date)
        except ValueError as error:
            return WorkflowResponse(
                status="failed",
                error=APIError(
                    code="FEED_IDENTITY_INVALID",
                    message="Feed does not expose a usable retained issue identity",
                    details=str(error),
                ),
            )
        articles: List[ArticleInput] = []
        seen_article_urls: set[str] = set()
        for entry in feed_data.get("entries", []):
            try:
                title = re.sub(r"\s+", " ", str(entry.get("title") or "")).strip()
                raw_url = str(entry.get("link") or "").strip()
                url = urljoin(feed_url, raw_url) if raw_url else ""
                parsed_url = urlparse(url)
                if (
                    not title
                    or re.search(r"\s", url)
                    or parsed_url.scheme not in {"http", "https"}
                    or not parsed_url.netloc
                ):
                    logger.warning("Skipping feed entry that cannot serve as linked evidence")
                    continue
                if url in seen_article_urls:
                    logger.warning(
                        "Skipping duplicate feed entry URL to preserve canonical evidence"
                    )
                    continue
                if contains_virtual_event(
                    {key: entry.get(key) for key in ("title", "description", "content")}
                ):
                    logger.info("Skipping a tagged virtual-event promotion")
                    continue
                seen_article_urls.add(url)
                published_raw = entry.get("published", "")
                published_dt = None
                if published_raw:
                    try:
                        published_dt = parsedate_to_datetime(published_raw)
                    except Exception:
                        try:
                            from datetime import datetime as _dt

                            published_dt = _dt.fromisoformat(published_raw.replace("Z", "+00:00"))
                        except Exception:
                            published_dt = None

                article = ArticleInput(
                    title=title,
                    url=url,
                    content=entry.get("content", ""),
                    summary=entry.get("description", ""),
                    source=feed_data.get("title", "Unknown Source"),
                    digest_url=_sentrydigest_item_url(feed_home_url, source_issue_date, url),
                    published=published_dt or datetime.now(),
                    published_known=published_dt is not None,
                )
                articles.append(article)
            except Exception as e:
                logger.warning(f"Skipping invalid article entry: {e}")
                continue

        logger.info(f"Processed {len(articles)} articles from feed")
        if not articles:
            return WorkflowResponse(
                status="failed",
                error=APIError(
                    code="NO_LINKED_ARTICLES",
                    message="Feed contains no articles with usable evidence links",
                ),
            )

        # Step 3: Enrich articles with full content
        logger.info("Step 3: Enriching articles with full content")
        enriched_articles = await rss_service.enrich_articles(articles)

        # Build local analysis upfront, used as fallback if model output is unavailable.
        local_signals, local_analysis = _build_local_analysis(enriched_articles)

        # Step 4: Initialize model service
        logger.info("Step 4: Initializing model service")
        fallback_reason = ""
        analysis_results = local_analysis
        used_model_analysis = False
        model_service = None

        try:
            model_service = GRCModelService(
                model_name=config.model,
                max_tokens=config.max_tokens,
                model_deadline=model_deadline,
            )
        except ValueError as e:
            fallback_reason = str(e)
            logger.warning(f"Model service unavailable, falling back to local analysis: {e}")

        # Step 5: Analyze articles for GRC content with the configured model
        logger.info("Step 5: Analyzing articles for GRC content")
        if model_service is not None:
            model_analysis = await model_service.analyze_articles_for_grc(enriched_articles)
            if "error" in model_analysis:
                fallback_reason = model_analysis["error"]
                logger.warning(f"GRC analysis failed, using local fallback: {fallback_reason}")
            else:
                analysis_results = model_analysis
                used_model_analysis = True

        relevance_diagnostics = _relevance_diagnostics(model_service)

        grc_article_count = analysis_results.get("summary", {}).get("grc_relevant_count", 0)
        source_evidence = await enrich_regulatory_sources(
            _build_source_evidence(enriched_articles), model_deadline=model_deadline
        )
        analysis_results["source_evidence"] = source_evidence

        # Build per-article output
        selected = selected_article_mask(enriched_articles, analysis_results)

        articles_out: List[ArticleRecord] = []
        for art, local, model_selected in zip(enriched_articles, local_signals, selected):
            has_grc = workflow_selected(
                entity=local["entity_signal"],
                risk=bool(local["risk_categories"]),
                model=model_selected,
            )
            articles_out.append(
                ArticleRecord(
                    title=art.title,
                    url=art.url,
                    content=art.content,
                    summary=art.summary,
                    source=art.source,
                    digest_url=art.digest_url,
                    published=art.published,
                    published_known=art.published_known,
                    content_origin=art.content_origin,
                    content_truncated=art.content_truncated,
                    has_grc_content=has_grc,
                    regulations=local.get("regulations", []),
                    frameworks=local.get("frameworks", []),
                    industries=local.get("industries", []),
                    regulatory_bodies=local.get("regulatory_bodies", []),
                )
            )

        if "grc_article_indices" in analysis_results:
            grc_article_count = sum(article.has_grc_content for article in articles_out)
            analysis_results["summary"]["grc_relevant_count"] = grc_article_count
        logger.info(f"Found {grc_article_count} articles with GRC content")

        # Step 6: Generate comprehensive report
        logger.info("Step 6: Generating comprehensive GRC report")
        report_content = ""
        resolved_model = ""
        report_plan = None
        used_fallback_report = False

        if used_model_analysis and model_service is not None:
            report_generation = await model_service.generate_grc_report(analysis_results, feed_data)
            report_content = report_generation.content
            resolved_model = report_generation.resolved_model
            report_plan = report_generation.report_plan
            if report_generation.failure_reason:
                fallback_reason = report_generation.failure_reason
                report_content = ""
                resolved_model = ""
            elif not resolved_model or resolved_model in {
                "openrouter/free",
                "openrouter/auto",
            }:
                fallback_reason = "OpenRouter did not attest a usable upstream model identity"
                report_content = ""
                resolved_model = ""
            if not report_content or report_content.startswith("# GRC Intelligence Report - Error"):
                fallback_reason = (
                    fallback_reason or report_content or "empty report content from model"
                )
                report_content = ""
                resolved_model = ""

        # Step 7: Create response
        logger.info("Step 7: Creating workflow response")

        generated_at = _utc_now()
        title = f"GRC Intelligence Report - {generated_at.strftime('%Y-%m-%d')}"
        if not report_content:
            report_content = _unavailable_report_content(title, generated_at)
            used_fallback_report = True
            logger.warning("Model output was unavailable; recording a refused run")

        report = Report(
            title=title,
            content=report_content,
            generated_at=generated_at,
        )

        analysis_data = analysis_results.get("analysis", {})
        metadata = ReportMetadata(
            article_count=len(articles),
            grc_article_count=grc_article_count,
            analysis_mode="fallback" if used_fallback_report else "model",
            fallback_reason=fallback_reason if used_fallback_report else None,
            source_name=feed_data.get("title") or "Unknown Feed",
            source_url=feed_url,
            source_home_url=feed_home_url,
            source_issue_date=source_issue_date,
            source_issue_url=source_issue_url,
            analysis_period=generated_at.strftime("%B %Y"),
            requested_model=config.model,
            resolved_model=resolved_model,
            report_plan=(
                None if used_fallback_report or report_plan is None else report_plan.as_json()
            ),
            source_articles=[
                {
                    "title": source["title"],
                    "url": source["url"],
                    "digest_url": source["digest_url"],
                    "cves": source["cves"],
                    "snippet": source["snippet"],
                    "article_evidence": source["article_evidence"],
                    "effective_date_evidence": source["effective_date_evidence"],
                }
                for source in source_evidence
            ],
            regulations_mentioned=analysis_data.get("regulations_mentioned", []),
            frameworks_referenced=analysis_data.get("frameworks_referenced", []),
            industries_affected=analysis_data.get("industries_affected", []),
            regulatory_bodies=analysis_data.get("regulatory_bodies", []),
            relevance_diagnostics=relevance_diagnostics,
        )

        logger.info("GRC workflow completed successfully")
        return WorkflowResponse(
            status="completed", report=report, metadata=metadata, articles=articles_out
        )

    except Exception as e:
        logger.error(f"Workflow execution failed: {str(e)}")
        return WorkflowResponse(
            status="failed",
            error=APIError(
                code="WORKFLOW_EXECUTION_ERROR",
                message="Workflow execution failed",
                details=str(e),
            ),
        )
