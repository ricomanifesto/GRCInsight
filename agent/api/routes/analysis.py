"""GRC analysis endpoints."""

from fastapi import APIRouter, HTTPException
from loguru import logger

from models.api import (
    AnalysisRequest,
    AnalysisResponse,
    AnalysisResult,
    AnalysisSummary,
    APIError,
)
from services.openai_client import OpenAIService
from core.entities import analyze_article_grc_content

router = APIRouter()


@router.post("/analyze", response_model=AnalysisResponse)
async def analyze_ar(request: AnalysisRequest):
    """Analyze articles for GRC content using OpenAIService."""
    logger.info(f"Starting analysis of {len(request.articles)} articles")

    try:
        # Initialize OpenAI service
        try:
            openai_service = OpenAIService()
        except ValueError as init_err:
            logger.error(f"OpenAI service initialization failed: {init_err}")
            return AnalysisResponse(
                status="failed",
                results=[],
                summary=AnalysisSummary(
                    total_articles=len(request.articles),
                    grc_articles=0,
                    top_regulations=[],
                    top_frameworks=[],
                    affected_industries=[],
                ),
                error=APIError(
                    code="OPENAI_INIT_FAILED",
                    message="OpenAI service initialization failed",
                    details=str(init_err),
                ),
            )

        # Run analysis
        analysis = await openai_service.analyze_articles_for_grc(request.articles)

        if "error" in analysis:
            logger.error(f"GRC analysis error: {analysis['error']}")
            return AnalysisResponse(
                status="failed",
                results=[],
                summary=AnalysisSummary(
                    total_articles=len(request.articles),
                    grc_articles=0,
                    top_regulations=[],
                    top_frameworks=[],
                    affected_industries=[],
                ),
                error=APIError(
                    code="GRC_ANALYSIS_FAILED",
                    message="GRC analysis failed",
                    details=str(analysis.get("error")),
                ),
            )

        # Build a quick lookup of identified GRC articles by URL/title
        identified = analysis.get("grc_articles", []) or []
        identified_urls = {item.get("url", "") for item in identified if item.get("url")}
        identified_titles = {item.get("title", "") for item in identified if item.get("title")}

        # Map per-article results (augment with local entity extraction)
        results = []
        for art in request.articles:
            has_grc = (art.url in identified_urls) or (art.title in identified_titles)
            # Local entity extraction to populate details regardless of LLM output
            try:
                local = analyze_article_grc_content(art.model_dump())
            except Exception:
                local = {
                    "regulations": [],
                    "frameworks": [],
                    "industries": [],
                    "regulatory_bodies": [],
                    "risk_levels": [],
                }

            results.append(
                AnalysisResult(
                    article_url=art.url,
                    has_grc_content=has_grc or bool(local.get("has_grc_content")),
                    regulations=local.get("regulations", []),
                    frameworks=local.get("frameworks", []),
                    industries=local.get("industries", []),
                    regulatory_bodies=local.get("regulatory_bodies", []),
                    risk_levels=[r.get("level", "") for r in local.get("risk_levels", []) if isinstance(r, dict)],
                )
            )

        # Build summary from analysis aggregates
        summary_data = analysis.get("summary", {})
        analysis_data = analysis.get("analysis", {})
        summary = AnalysisSummary(
            total_articles=summary_data.get("total_articles", len(request.articles)),
            grc_articles=summary_data.get("grc_relevant_count", 0),
            top_regulations=analysis_data.get("regulations_mentioned", []) or [],
            top_frameworks=analysis_data.get("frameworks_referenced", []) or [],
            affected_industries=analysis_data.get("industries_affected", []) or [],
        )

        logger.info("Article analysis completed successfully")
        return AnalysisResponse(status="success", results=results, summary=summary)

    except Exception as e:
        logger.error(f"Article analysis failed: {str(e)}")
        return AnalysisResponse(
            status="failed",
            results=[],
            summary=AnalysisSummary(
                total_articles=len(request.articles),
                grc_articles=0,
                top_regulations=[],
                top_frameworks=[],
                affected_industries=[],
            ),
            error=APIError(
                code="ANALYSIS_ERROR",
                message="Article analysis failed",
                details=str(e),
            ),
        )


@router.post("/extract/entities")
async def extract_entities(text: str):
    """Extract GRC entities from text."""
    logger.info("Extracting entities from text")
    
    try:
        # Import here to avoid circular imports
        from core.entities import extract_entities
        
        entities = extract_entities(text)
        
        return {
            "status": "success",
            "entities": entities
        }
        
    except Exception as e:
        logger.error(f"Entity extraction failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Entity extraction failed: {str(e)}"
        )
