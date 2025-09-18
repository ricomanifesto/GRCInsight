"""Refactored LangGraph workflow for FastAPI service."""

import asyncio
from datetime import datetime
from typing import Dict, Any, List
from loguru import logger

from models.api import (
    WorkflowResponse, Report, ReportMetadata, APIError, 
    AnalysisConfig, ArticleInput
)
from services.rss_service import RSSService
from services.openai_client import OpenAIService


# Initialize services
rss_service = RSSService()
openai_service = None  # Will be initialized in the function


async def run_grc_analysis_endpoint(feed_url: str, config: AnalysisConfig) -> WorkflowResponse:
    """
    Main workflow endpoint that orchestrates the complete GRC analysis.
    This replaces the original LangGraph workflow for the microservice architecture.
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
        for entry in feed_data.get("entries", []):
            try:
                article = ArticleInput(
                    title=entry.get("title", ""),
                    url=entry.get("link", ""),
                    content=entry.get("content", ""),
                    summary=entry.get("description", ""),
                    source=feed_data.get("title", "Unknown Source"),
                    published=datetime.now()  # TODO: Parse actual published date
                )
                articles.append(article)
            except Exception as e:
                logger.warning(f"Skipping invalid article entry: {e}")
                continue
        
        logger.info(f"Processed {len(articles)} articles from feed")
        
        # Step 3: Enrich articles with full content
        logger.info("Step 3: Enriching articles with full content")
        enriched_articles = await rss_service.enrich_articles(articles)
        
        # Step 4: Initialize OpenAI service
        logger.info("Step 4: Initializing OpenAI service")
        try:
            openai_service = OpenAIService()
        except ValueError as e:
            logger.error(f"Failed to initialize OpenAI service: {e}")
            return WorkflowResponse(
                status="failed",
                error=APIError(
                    code="OPENAI_INIT_FAILED",
                    message="OpenAI service initialization failed",
                    details=str(e)
                )
            )
        
        # Step 5: Analyze articles for GRC content with OpenAI
        logger.info("Step 5: Analyzing articles for GRC content with OpenAI")
        analysis_results = await openai_service.analyze_articles_for_grc(enriched_articles)
        
        if "error" in analysis_results:
            logger.error(f"GRC analysis failed: {analysis_results['error']}")
            return WorkflowResponse(
                status="failed",
                error=APIError(
                    code="GRC_ANALYSIS_FAILED",
                    message="GRC content analysis failed",
                    details=analysis_results["error"]
                )
            )
        
        grc_article_count = analysis_results.get("summary", {}).get("grc_relevant_count", 0)
        logger.info(f"Found {grc_article_count} articles with GRC content")
        
        # Step 6: Generate comprehensive report
        logger.info("Step 6: Generating comprehensive GRC report")
        report_content = await openai_service.generate_grc_report(analysis_results, feed_data)
        
        if not report_content or "Error" in report_content:
            logger.warning("Report generation had issues, using fallback content")
            if grc_article_count == 0:
                report_content = "# GRC Intelligence Report - No Content Found\n\nNo articles with GRC-related content were found in the current dataset."
        
        # Step 7: Create response
        logger.info("Step 7: Creating workflow response")
        
        report = Report(
            title=f"GRC Intelligence Report - {datetime.utcnow().strftime('%Y-%m-%d')}",
            content=report_content,
            generated_at=datetime.utcnow().isoformat() + "Z"
        )
        
        # Extract metadata from analysis results
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
            metadata=metadata
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
        # This would need to be adapted based on the actual structure
        # of your analysis results
        return analysis_results.get(key, [])
    except Exception:
        return []