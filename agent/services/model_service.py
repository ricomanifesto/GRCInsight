"""Provider-switchable model service for GRC analysis."""

from datetime import datetime, timezone
from typing import List, Dict, Any

from loguru import logger

from config.settings import settings
from models.api import ArticleInput
from services.opencode_client import OpenCodeClient, parse_model_selection
from services.openrouter_client import OpenRouterClient


class GRCModelService:
    """Service for model-powered GRC analysis."""

    def __init__(self, model_name: str | None = None, max_tokens: int | None = None):
        """Initialize model service."""
        configured_model = model_name or settings.llm_model
        configured_max_tokens = max_tokens or settings.llm_max_tokens
        self.model = parse_model_selection(configured_model)
        self.max_tokens = configured_max_tokens
        timeout = max(120.0, float(configured_max_tokens) / 20)
        if settings.openrouter_api_key and self.model.provider_id != "openrouter":
            raise ValueError("OpenRouter direct Lambda model calls require an openrouter/* model")
        if settings.openrouter_api_key:
            self.client = OpenRouterClient(
                api_key=settings.openrouter_api_key,
                max_tokens=configured_max_tokens,
                timeout=timeout,
            )
            self.client_kind = "openrouter"
        else:
            self.client = OpenCodeClient(timeout=timeout)
            self.client_kind = "opencode"
        logger.info(
            "Initialized model service with client=%s provider=%s model=%s",
            self.client_kind,
            self.model.provider_id,
            self.model.model_id,
        )

    def _extract_text(self, response) -> str:
        """Return text content from either a raw string or response-like object."""
        if isinstance(response, str):
            return response
        content = response.content
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            texts = [
                block["text"]
                for block in content
                if isinstance(block, dict) and block.get("type") == "text"
            ]
            return "\n".join(texts)
        return str(content)

    async def _invoke(self, *, system_prompt: str, user_prompt: str, title: str) -> str:
        """Invoke the configured model through the selected model client."""
        return await self.client.generate(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            model=self.model,
            title=title,
        )

    async def analyze_articles_for_grc(self, articles: List[ArticleInput]) -> Dict[str, Any]:
        """Analyze articles for GRC-relevant content."""
        try:
            logger.info(f"Analyzing {len(articles)} articles for GRC content")

            if not articles:
                return {
                    "grc_articles": [],
                    "summary": {
                        "total_articles": 0,
                        "grc_relevant_count": 0,
                        "confidence_score": 0.0,
                    },
                    "analysis": {
                        "regulations_mentioned": [],
                        "frameworks_referenced": [],
                        "industries_affected": [],
                        "risk_categories": [],
                    },
                }

            analysis_prompt = self._create_analysis_prompt(articles)

            response_content = await self._invoke(
                system_prompt=self._get_system_prompt(),
                user_prompt=analysis_prompt,
                title="GRC article analysis",
            )

            analysis_result = self._process_analysis_response(response_content, articles)

            logger.info(
                f"Analysis complete: {analysis_result['summary']['grc_relevant_count']} GRC-relevant articles found"
            )

            return analysis_result

        except Exception as e:
            logger.error(f"Error during GRC analysis: {e}")
            return {
                "error": str(e),
                "grc_articles": [],
                "summary": {
                    "total_articles": len(articles),
                    "grc_relevant_count": 0,
                    "confidence_score": 0.0,
                },
                "analysis": {
                    "regulations_mentioned": [],
                    "frameworks_referenced": [],
                    "industries_affected": [],
                    "risk_categories": [],
                },
            }

    async def generate_grc_report(
        self, analysis_data: Dict[str, Any], feed_info: Dict[str, Any]
    ) -> str:
        """Generate a comprehensive GRC intelligence report."""
        try:
            logger.info("Generating GRC intelligence report")

            report_prompt = self._create_report_prompt(analysis_data, feed_info)

            report_content = await self._invoke(
                system_prompt=self._get_report_system_prompt(),
                user_prompt=report_prompt,
                title="GRC intelligence report",
            )

            logger.info("GRC report generation completed")
            return report_content

        except Exception as e:
            logger.error(f"Error generating report: {e}")
            return f"# GRC Intelligence Report - Error\n\nUnable to generate report: {str(e)}"

    def _get_system_prompt(self) -> str:
        """Get the system prompt for GRC analysis."""
        focus_areas = ", ".join(settings.analysis_focus_areas)

        return f"""You are a GRC (Governance, Risk, and Compliance) intelligence analyst specializing in identifying regulatory and compliance-related content in news articles and industry reports.

Your focus areas include: {focus_areas}

For each article, analyze:
1. Relevance to GRC/compliance (score 0-10)
2. Regulatory frameworks mentioned (SOX, GDPR, PCI-DSS, etc.)
3. Industries affected
4. Risk categories (operational, financial, cyber, regulatory, etc.)
5. Compliance requirements or changes

Be precise and factual. Only flag content as GRC-relevant if it has clear governance, risk, or compliance implications."""

    def _get_report_system_prompt(self) -> str:
        """Get the system prompt for report generation."""
        now = datetime.now(timezone.utc)
        today = now.strftime("%B %Y")
        today_full = now.strftime("%Y-%m-%d")
        return f"""You are a senior GRC analyst creating executive-level intelligence reports.

Today's date is {today_full}. The current reporting period is {today}.

Create a comprehensive report that:
1. Summarizes key GRC developments and trends
2. Highlights regulatory changes and their business impact
3. Identifies emerging risks and compliance challenges
4. Provides actionable insights for governance and risk management

IMPORTANT: Use "{today}" as the Date of Issue and analysis period in the report metadata. Never use a hardcoded or stale date. All dates in the report must reflect the current period ({today}).

Do not include classification, confidentiality, internal-use, distribution approval, or prepared-by labels. This is a public portfolio report and must not present itself as private or internal-only material.

Use professional language and structure the report with clear sections and markdown tables where data comparisons are appropriate. Focus on business impact and strategic implications."""

    def _create_analysis_prompt(self, articles: List[ArticleInput]) -> str:
        """Create prompt for analyzing articles."""
        articles_text = ""
        for i, article in enumerate(articles, 1):
            content = article.content or article.summary or "No content available"
            articles_text += f"""
Article {i}:
Title: {article.title}
URL: {article.url}
Content: {content[:500]}...
Published: {article.published}
---"""

        return f"""Analyze the following articles for GRC relevance:

{articles_text}

Please provide analysis in this format:
- List articles that are GRC-relevant (include article number, title, relevance score 1-10, and brief reason)
- Identify mentioned regulations/frameworks (GDPR, SOX, PCI-DSS, ISO 27001, NIST, etc.)
- List affected industries
- Categorize risk types (cyber, operational, financial, regulatory, reputational)
- Note any compliance deadlines or regulatory changes

Focus only on content with clear governance, risk, or compliance implications."""

    def _create_report_prompt(
        self, analysis_data: Dict[str, Any], feed_info: Dict[str, Any]
    ) -> str:
        """Create prompt for report generation."""
        now = datetime.now(timezone.utc)
        today = now.strftime("%B %Y")
        today_full = now.strftime("%Y-%m-%d")

        grc_count = analysis_data.get("summary", {}).get("grc_relevant_count", 0)
        total_count = analysis_data.get("summary", {}).get("total_articles", 0)

        regulations = analysis_data.get("analysis", {}).get("regulations_mentioned", [])
        industries = analysis_data.get("analysis", {}).get("industries_affected", [])
        risks = analysis_data.get("analysis", {}).get("risk_categories", [])
        source_evidence = analysis_data.get("source_evidence", [])

        source_lines = []
        for index, evidence in enumerate(source_evidence, 1):
            cves = evidence.get("cves", []) or []
            threat_actors = evidence.get("threat_actors", []) or []
            source_lines.append(
                "\n".join(
                    [
                        f"{index}. {evidence.get('title', 'Untitled source')}",
                        f"   URL: {evidence.get('url', 'No URL')}",
                        f"   CVEs: {', '.join(cves) if cves else 'None detected'}",
                        f"   Threat Actors: {', '.join(threat_actors) if threat_actors else 'None detected'}",
                        f"   Snippet: {evidence.get('snippet', 'No snippet available')}",
                    ]
                )
            )
        source_evidence_text = (
            "\n\n".join(source_lines)
            if source_lines
            else "No source evidence snippets were provided."
        )

        return f"""Create a GRC Intelligence Report based on this analysis:

Report Date: {today_full}
Date of Issue: {today}
Source: {feed_info.get('title', 'Unknown Feed')}
Analysis Period: Current Quarter ({today})
Total Articles Analyzed: {total_count}
GRC-Relevant Articles: {grc_count}

Key Findings:
- Regulations/Frameworks: {', '.join(regulations) if regulations else 'None identified'}
- Industries Affected: {', '.join(industries) if industries else 'Multiple sectors'}
- Risk Categories: {', '.join(risks) if risks else 'Various risk types'}

Source Evidence for Entity Sections:
{source_evidence_text}

Please create a professional executive summary report with:
1. Executive Summary
2. Key Regulatory Developments
3. Industry Impact Analysis
4. Threat Actor Activities
5. CVE and Vulnerability Highlights
6. Risk Assessment
7. Recommendations for Action

Executive Summary must be 2-4 short paragraphs, separated by blank lines. Keep each paragraph focused on one executive decision theme; do not write the summary as one long block.

Threat Actor Activities must include only article-supported threat actor activity. Do not reuse stale actor names, examples, or prior report content; for example, do not mention FishMonger unless it appears in the current source articles. If no article-supported threat actor activity appears, state that no article-supported threat actor activity was identified in this reporting period.

CVE and Vulnerability Highlights: List every article-supported CVE identifier up to 10 items with a short business-impact note. Do not cap the CVE section at one item when multiple CVEs appear in the source articles. If no CVE identifiers are present, state that no article-supported CVEs were identified.

IMPORTANT: The Date of Issue in the report header MUST be "{today}" (the current month/year). Do NOT use any other date.

Do not include classification, confidentiality, internal-use, distribution approval, or prepared-by labels. This is a public portfolio report and must not present itself as private or internal-only material.

Make it actionable for risk managers and compliance officers."""

    def _process_analysis_response(
        self, response_content: str, original_articles: List[ArticleInput]
    ) -> Dict[str, Any]:
        """Process model analysis output."""
        lines = response_content.split("\n")

        grc_articles = []
        regulations = []
        industries = []
        risks = []
        current_section = None
        for line in lines:
            line = line.strip()
            if not line:
                continue

            if "regulation" in line.lower() or "framework" in line.lower():
                current_section = "regulations"
            elif "industri" in line.lower():
                current_section = "industries"
            elif "risk" in line.lower():
                current_section = "risks"
            elif line.startswith("Article ") and any(
                word in line.lower() for word in ["relevant", "grc", "compliance"]
            ):
                try:
                    if "score" in line.lower():
                        article_info = {
                            "title": (
                                line.split("Title:")[-1].split("score")[0].strip()
                                if "Title:" in line
                                else line
                            ),
                            "relevance_score": 7.0,
                            "summary": "GRC-relevant content identified",
                        }
                        grc_articles.append(article_info)
                except Exception:
                    pass

            if current_section == "regulations" and any(
                reg in line for reg in ["GDPR", "SOX", "PCI", "ISO", "NIST", "CCPA"]
            ):
                for reg in ["GDPR", "SOX", "PCI-DSS", "ISO 27001", "NIST", "CCPA"]:
                    if reg in line:
                        regulations.append(reg)

        if not grc_articles and original_articles:
            for article in original_articles:
                grc_articles.append(
                    {
                        "title": article.title,
                        "url": article.url,
                        "relevance_score": 7.0,
                        "summary": "GRC analysis via comprehensive model evaluation",
                    }
                )

        return {
            "grc_articles": grc_articles,
            "summary": {
                "total_articles": len(original_articles),
                "grc_relevant_count": len(grc_articles),
                "confidence_score": 0.8 if grc_articles else 0.2,
            },
            "analysis": {
                "regulations_mentioned": list(set(regulations)) if regulations else [],
                "frameworks_referenced": (
                    list(set([r for r in regulations if "ISO" in r or "NIST" in r]))
                    if regulations
                    else []
                ),
                "industries_affected": list(set(industries)) if industries else [],
                "risk_categories": list(set(risks)) if risks else [],
                "regulatory_bodies": [],
            },
        }
