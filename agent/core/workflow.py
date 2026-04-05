"""LangGraph workflow for FastAPI service."""

import asyncio
from collections import Counter
from datetime import datetime
from typing import Dict, Any, List
from loguru import logger

from models.api import (
    WorkflowResponse, Report, ReportMetadata, APIError,
    AnalysisConfig, ArticleInput
)
from services.rss_service import RSSService
from services.anthropic_client import AnthropicService
from core.entities import analyze_article_grc_content


# Initialize services
rss_service = RSSService()


def _detect_risk_categories(text: str) -> List[str]:
    """Infer coarse risk themes from article text without using an LLM."""
    catalog = {
        "Regulatory and enforcement activity": [
            "regulator", "regulatory", "compliance", "cisa", "fbi", "ofac",
            "sanction", "privacy", "enforcement", "directive",
        ],
        "Identity and access security": [
            "identity", "credential", "access", "mfa", "password",
            "privilege", "account takeover", "intune",
        ],
        "Third-party and supply chain exposure": [
            "third-party", "third party", "vendor", "supplier",
            "supply chain", "msp",
        ],
        "Vulnerability and patch management": [
            "vulnerability", "zero-day", "zero day", "patch", "cve",
            "exploit", "rce", "flaw", "unauthenticated",
        ],
        "Ransomware and malware operations": [
            "ransomware", "malware", "botnet", "ddos", "extortion",
            "phishing", "trojan", "implant",
        ],
        "Cloud and data protection": [
            "cloud", "sharepoint", "data breach", "data exposure",
            "data leak", "data theft", "storage", "saas",
        ],
    }

    lowered = text.lower()
    matched = []
    for category, keywords in catalog.items():
        if any(keyword in lowered for keyword in keywords):
            matched.append(category)
    return matched


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
        text = "\n".join(filter(None, [article.title, article.summary, article.content]))
        risk_categories = _detect_risk_categories(text)
        has_grc = local.get("has_grc_content", False) or bool(risk_categories)

        local["has_grc_content"] = has_grc
        local["risk_categories"] = risk_categories
        local_signals.append(local)

        regulations.update(local.get("regulations", []))
        frameworks.update(local.get("frameworks", []))
        industries.update(local.get("industries", []))
        regulatory_bodies.update(local.get("regulatory_bodies", []))
        risk_counter.update(risk_categories)

        if has_grc:
            grc_articles.append({
                "title": article.title,
                "url": article.url,
                "reason": _build_article_reason(local, risk_categories),
            })

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


def _build_fallback_report(
    feed_data: Dict[str, Any],
    enriched_articles: List[ArticleInput],
    local_signals: List[Dict[str, Any]],
    analysis_results: Dict[str, Any],
    fallback_reason: str,
) -> str:
    """Create a deterministic Markdown report when Claude is unavailable."""
    total_count = analysis_results.get("summary", {}).get("total_articles", len(enriched_articles))
    grc_count = analysis_results.get("summary", {}).get("grc_relevant_count", 0)
    analysis = analysis_results.get("analysis", {})
    regulations = analysis.get("regulations_mentioned", []) or []
    frameworks = analysis.get("frameworks_referenced", []) or []
    industries = analysis.get("industries_affected", []) or []
    bodies = analysis.get("regulatory_bodies", []) or []
    risk_categories = analysis.get("risk_categories", []) or []

    relevant_pairs = [
        (article, signal)
        for article, signal in zip(enriched_articles, local_signals)
        if signal.get("has_grc_content")
    ]
    if not relevant_pairs:
        relevant_pairs = list(zip(enriched_articles[:8], local_signals[:8]))

    highlights = []
    for article, signal in relevant_pairs[:6]:
        detail = _build_article_reason(signal, signal.get("risk_categories", []))
        highlights.append(f"- [{article.title}]({article.url}) - {detail}.")

    risk_lines = []
    for category in risk_categories[:5]:
        examples = [
            article.title
            for article, signal in relevant_pairs
            if category in signal.get("risk_categories", [])
        ][:2]
        if examples:
            risk_lines.append(f"- {category}: Example signals include {', '.join(examples)}.")
        else:
            risk_lines.append(f"- {category}: Present across the current monitoring set.")
    if not risk_lines:
        risk_lines.append(
            "- Current source articles emphasize operational cyber risk and compliance monitoring."
        )

    recommendation_lines = [
        "- Maintain incident response, disclosure, and evidence-retention readiness for high-severity cyber events.",
        "- Prioritize vulnerability remediation, privileged access hygiene, and external attack-surface review for internet-facing services.",
        "- Review third-party and supplier oversight for notification duties, monitoring coverage, and access restrictions.",
        "- Track regulator and enforcement updates from bodies such as CISA, the FBI, OFAC, and relevant privacy authorities.",
    ]

    regulatory_lines = []
    if regulations or frameworks or bodies:
        if regulations:
            regulatory_lines.append(f"- Explicit regulation references detected: {', '.join(regulations[:6])}.")
        if frameworks:
            regulatory_lines.append(f"- Framework references detected: {', '.join(frameworks[:6])}.")
        if bodies:
            regulatory_lines.append(f"- Regulatory or government bodies mentioned: {', '.join(bodies[:6])}.")
    else:
        regulatory_lines.append(
            "- No explicit regulation codes or named frameworks were detected in the current source set."
        )
        regulatory_lines.append(
            "- Governance and compliance significance is inferred from enforcement, breach, and risk-management reporting patterns."
        )

    industry_lines = []
    if industries:
        industry_lines.append(f"- Industries with explicit mentions: {', '.join(industries[:6])}.")
    else:
        industry_lines.append(
            "- The current feed is broad-based cybersecurity reporting with cross-sector relevance for governance, risk, and compliance teams."
        )

    limitation = fallback_reason or "AI analysis temporarily unavailable"

    return "\n".join([
        f"# GRC Intelligence Report - {datetime.utcnow().strftime('%Y-%m-%d')}",
        f"**Generated:** {datetime.utcnow().isoformat()}Z",
        "GRC Intelligence Report - Deterministic Fallback Summary",
        f"Source: {feed_data.get('title', 'Unknown Feed')}",
        "Analysis Period: Recent articles",
        f"Total Articles Analyzed: {total_count} (Locally flagged as GRC-relevant: {grc_count})",
        "",
        "1) Executive Summary",
        f"- This report was generated using deterministic local analysis because AI generation was temporarily unavailable: {limitation}.",
        f"- The monitored feed continues to surface material GRC monitoring signals across {total_count} current articles.",
        f"- Dominant themes in the current batch include {', '.join(risk_categories[:3]) if risk_categories else 'operational cyber risk, third-party exposure, and regulatory monitoring'}.",
        "- Business impact remains concentrated in incident response readiness, disclosure obligations, control effectiveness, and board-level risk oversight.",
        "",
        "2) Key Regulatory Developments",
        "Observations",
        *regulatory_lines,
        "Implications for Business",
        "- Teams should treat major cyber incidents, sanctions activity, and regulator advisories as compliance-relevant events even when source articles are operational in nature.",
        "- Evidence capture, executive escalation, and breach-notification decision support remain priority governance controls.",
        "",
        "3) Industry Impact Analysis",
        *industry_lines,
        "- Organizations in regulated or data-intensive sectors should expect the same cyber events to trigger legal, contractual, and supervisory scrutiny.",
        "",
        "4) Risk Assessment",
        *risk_lines,
        "",
        "5) Recommendations for Action",
        *recommendation_lines,
        "",
        "6) Source Highlights",
        *highlights,
        "",
        "Notes and limitations",
        "- This fallback keeps the report current using feed content plus local entity extraction while AI generation is unavailable.",
        "- Once the AI backend is restored, the richer narrative report will resume automatically.",
    ])


async def run_grc_analysis_endpoint(feed_url: str, config: AnalysisConfig) -> WorkflowResponse:
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
                    details=feed_data["error"]
                )
            )

        # Step 2: Convert entries to ArticleInput format
        logger.info("Step 2: Processing feed entries")
        articles = []
        from email.utils import parsedate_to_datetime
        for entry in feed_data.get("entries", []):
            try:
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
                    title=entry.get("title", ""),
                    url=entry.get("link", ""),
                    content=entry.get("content", ""),
                    summary=entry.get("description", ""),
                    source=feed_data.get("title", "Unknown Source"),
                    published=published_dt or datetime.now()
                )
                articles.append(article)
            except Exception as e:
                logger.warning(f"Skipping invalid article entry: {e}")
                continue

        logger.info(f"Processed {len(articles)} articles from feed")

        # Step 3: Enrich articles with full content
        logger.info("Step 3: Enriching articles with full content")
        enriched_articles = await rss_service.enrich_articles(articles)

        # Build local analysis upfront — used as fallback if Claude is unavailable
        local_signals, local_analysis = _build_local_analysis(enriched_articles)

        # Step 4: Initialize Anthropic Claude service
        logger.info("Step 4: Initializing Anthropic Claude service")
        fallback_reason = ""
        analysis_results = local_analysis
        used_claude_analysis = False
        anthropic_service = None

        try:
            anthropic_service = AnthropicService()
        except ValueError as e:
            fallback_reason = str(e)
            logger.warning(f"Anthropic service unavailable, falling back to local analysis: {e}")

        # Step 5: Analyze articles for GRC content with Claude
        logger.info("Step 5: Analyzing articles for GRC content")
        if anthropic_service is not None:
            claude_analysis = await anthropic_service.analyze_articles_for_grc(enriched_articles)
            if "error" in claude_analysis:
                fallback_reason = claude_analysis["error"]
                logger.warning(f"GRC analysis failed, using local fallback: {fallback_reason}")
            else:
                analysis_results = claude_analysis
                used_claude_analysis = True

        grc_article_count = analysis_results.get("summary", {}).get("grc_relevant_count", 0)
        logger.info(f"Found {grc_article_count} articles with GRC content")

        # Build per-article output
        identified = set()
        for item in analysis_results.get("grc_articles", []) or []:
            if isinstance(item, dict):
                if item.get("url"):
                    identified.add(item.get("url"))
                if item.get("title"):
                    identified.add(item.get("title"))

        articles_out = []
        for art, local in zip(enriched_articles, local_signals):
            has_grc = local.get("has_grc_content", False) or (art.url in identified) or (art.title in identified)
            articles_out.append({
                "title": art.title,
                "url": art.url,
                "content": art.content,
                "summary": art.summary,
                "source": art.source,
                "published": art.published,
                "has_grc_content": has_grc,
                "regulations": local.get("regulations", []),
                "frameworks": local.get("frameworks", []),
                "industries": local.get("industries", []),
                "regulatory_bodies": local.get("regulatory_bodies", []),
            })

        # Step 6: Generate comprehensive report
        logger.info("Step 6: Generating comprehensive GRC report")
        report_content = ""

        if used_claude_analysis and anthropic_service is not None:
            report_content = await anthropic_service.generate_grc_report(analysis_results, feed_data)
            if not report_content or report_content.startswith("# GRC Intelligence Report - Error"):
                fallback_reason = report_content or "empty report content from Claude"
                report_content = ""

        if not report_content:
            report_content = _build_fallback_report(
                feed_data,
                enriched_articles,
                local_signals,
                analysis_results,
                fallback_reason,
            )
            logger.warning("Generated fallback report because Claude output was unavailable")

        # Step 7: Create response
        logger.info("Step 7: Creating workflow response")

        report = Report(
            title=f"GRC Intelligence Report - {datetime.utcnow().strftime('%Y-%m-%d')}",
            content=report_content,
            generated_at=datetime.utcnow().isoformat() + "Z"
        )

        analysis_data = analysis_results.get("analysis", {})
        metadata = ReportMetadata(
            article_count=len(articles),
            grc_article_count=grc_article_count,
            regulations_mentioned=analysis_data.get("regulations_mentioned", []),
            frameworks_referenced=analysis_data.get("frameworks_referenced", []),
            industries_affected=analysis_data.get("industries_affected", []),
            regulatory_bodies=analysis_data.get("regulatory_bodies", [])
        )

        logger.info("GRC workflow completed successfully")
        return WorkflowResponse(
            status="completed",
            report=report,
            metadata=metadata,
            articles=articles_out
        )

    except Exception as e:
        logger.error(f"Workflow execution failed: {str(e)}")
        return WorkflowResponse(
            status="failed",
            error=APIError(
                code="WORKFLOW_EXECUTION_ERROR",
                message="Workflow execution failed",
                details=str(e)
            )
        )


def extract_from_analysis(analysis_results: Dict[str, Any], key: str) -> List[str]:
    """Extract specific data from analysis results."""
    try:
        return analysis_results.get(key, [])
    except Exception:
        return []
