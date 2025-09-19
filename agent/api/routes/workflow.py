"""Workflow execution endpoints."""

import os
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


@router.get("/workflow/status/{report_id}")
async def get_workflow_status(report_id: str):
    """Get the status of a workflow execution from DynamoDB (Lambda mode)."""
    table_name = os.getenv("DDB_TABLE_NAME", "grcinsight-reports")
    try:
        import boto3
        from botocore.exceptions import BotoCoreError, ClientError
        ddb = boto3.resource("dynamodb")
        table = ddb.Table(table_name)

        resp = table.get_item(Key={"report_id": report_id})
        item = resp.get("Item")
        if not item:
            raise HTTPException(status_code=404, detail=f"Report {report_id} not found")

        # Normalize response
        status = item.get("status", "unknown")
        created_at = item.get("created_at")
        updated_at = item.get("updated_at")
        generated_at = item.get("generated_at")
        title = item.get("title")

        return {
            "report_id": report_id,
            "status": status,
            "title": title,
            "created_at": created_at,
            "updated_at": updated_at,
            "generated_at": generated_at,
            "metadata": item.get("metadata", {}),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch workflow status from DynamoDB: {e}")
        raise HTTPException(status_code=500, detail=f"Status lookup failed: {str(e)}")
