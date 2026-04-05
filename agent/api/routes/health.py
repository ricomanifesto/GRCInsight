"""Health check endpoints."""

from datetime import datetime
from fastapi import APIRouter, Query
from loguru import logger

from models.api import HealthStatus
from services.anthropic_client import AnthropicService
import os

try:
    import boto3  # Optional, only used if configured
except Exception:  # pragma: no cover
    boto3 = None

try:
    from langchain_core.messages import HumanMessage
except Exception:  # pragma: no cover
    HumanMessage = None

router = APIRouter()


@router.get("/health", response_model=HealthStatus)
async def health_check(deep: bool = Query(default=False, description="Run deeper checks (LLM call, DynamoDB table describe)")):
    """Comprehensive health check."""
    logger.info("Health check requested")

    overall = "healthy"
    services = {}

    # Anthropic Claude readiness: ensure API key present and client can be constructed
    try:
        anthropic_service = AnthropicService()
        # Optional deep LLM call
        if deep and HumanMessage is not None:
            try:
                _ = await anthropic_service._invoke_with_fallbacks([HumanMessage(content="ping")])
                services["llm"] = {"status": "healthy", "provider": "anthropic", "deep": True}
            except Exception as llm_err:
                services["llm"] = {"status": "unhealthy", "provider": "anthropic", "error": str(llm_err)}
                overall = "unhealthy"
        else:
            services["llm"] = {"status": "healthy", "provider": "anthropic"}
    except Exception as e:
        services["llm"] = {"status": "unhealthy", "provider": "anthropic", "error": str(e)}
        overall = "unhealthy"

    # Workflow readiness: trivial OK for now (no background queues here)
    services["workflow"] = {"status": "healthy"}

    # DynamoDB readiness (Lambda mode or explicit table configured)
    try:
        table_name = os.getenv("DDB_TABLE_NAME")
        if table_name and boto3 is not None:
            client = boto3.client("dynamodb")
            client.describe_table(TableName=table_name)
            services["dynamodb"] = {"status": "healthy", "table": table_name}
        elif table_name and boto3 is None:
            services["dynamodb"] = {"status": "unhealthy", "error": "boto3 not available"}
            overall = "unhealthy"
    except Exception as ddb_err:
        services["dynamodb"] = {"status": "unhealthy", "error": str(ddb_err)}
        overall = "unhealthy"

    return HealthStatus(
        status=overall,
        timestamp=datetime.utcnow(),
        services=services,
    )


@router.get("/health/ready")
async def readiness_check():
    """Readiness check for container orchestration."""
    return {"status": "ready", "timestamp": datetime.utcnow()}


@router.get("/health/live")
async def liveness_check():
    """Liveness check for container orchestration."""
    return {"status": "alive", "timestamp": datetime.utcnow()}
