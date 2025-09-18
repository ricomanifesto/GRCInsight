"""GRC analysis endpoints."""

from fastapi import APIRouter, HTTPException
from loguru import logger

from models.api import AnalysisRequest, AnalysisResponse, APIError
# from core.analyze import analyze_articles_endpoint  # TODO: Implement this function

router = APIRouter()


@router.post("/analyze", response_model=AnalysisResponse)
async def analyze_articles(request: AnalysisRequest):
    """Analyze articles for GRC content."""
    logger.info(f"Starting analysis of {len(request.articles)} articles")
    
    try:
        # TODO: Implement actual analysis
        # For now, return a mock response
        from models.api import AnalysisSummary
        result = AnalysisResponse(
            status="success",
            results=[],
            summary=AnalysisSummary(
                total_articles=len(request.articles),
                grc_articles=0
            )
        )
        
        logger.info("Article analysis completed successfully (mock)")
        return result
        
    except Exception as e:
        logger.error(f"Article analysis failed: {str(e)}")
        return AnalysisResponse(
            status="failed",
            results=[],
            summary={"total_articles": 0, "grc_articles": 0},
            error=APIError(
                code="ANALYSIS_ERROR",
                message="Article analysis failed",
                details=str(e)
            )
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