"""Workflow execution endpoints."""

from datetime import datetime
from fastapi import APIRouter, HTTPException
from loguru import logger

from models.api import WorkflowRequest, WorkflowResponse, APIError
from core.workflow import run_grc_analysis_endpoint

router = APIRouter()


@router.post("/workflow/run", response_model=WorkflowResponse)
async def run_workflow(request: WorkflowRequest):
    """Execute the complete GRC analysis workflow."""
    logger.info(f"Starting workflow execution for feed: {request.feed_url}")
    
    try:
        # Execute the real GRC analysis workflow
        result = await run_grc_analysis_endpoint(request.feed_url, request.config)
        
        logger.info("Workflow execution completed successfully")
        return result
        
    except Exception as e:
        logger.error(f"Workflow execution failed: {str(e)}")
        return WorkflowResponse(
            status="failed",
            error=APIError(
                code="WORKFLOW_ERROR",
                message="Workflow execution error",
                details=str(e)
            )
        )


@router.get("/workflow/status/{workflow_id}")
async def get_workflow_status(workflow_id: str):
    """Get the status of a workflow execution."""
    # TODO: Implement workflow status tracking
    return {
        "workflow_id": workflow_id,
        "status": "completed",  # Placeholder
        "timestamp": datetime.utcnow()
    }