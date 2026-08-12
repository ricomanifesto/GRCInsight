"""Health check endpoints."""

from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Query
from loguru import logger

from models.api import HealthStatus
from services.model_service import GRCModelService
import os

boto3: Any | None = None
try:
    import boto3 as _boto3  # Optional, only used if configured

    boto3 = _boto3
except Exception:  # pragma: no cover
    pass

router = APIRouter()


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


@router.get("/health", response_model=HealthStatus)
async def health_check(
    deep: bool = Query(
        default=False, description="Run deeper checks (LLM call, DynamoDB table describe)"
    )
):
    """Comprehensive health check."""
    logger.info("Health check requested")

    overall = "healthy"
    services = {}

    # Model readiness: ensure config is valid and the client can be constructed.
    try:
        model_service = GRCModelService()
        if deep:
            try:
                _ = await model_service._invoke(
                    system_prompt="Return a one-word health response.",
                    user_prompt="ping",
                    title="GRCInsight health check",
                )
                services["llm"] = {
                    "status": "healthy",
                    "provider": model_service.model.provider_id,
                    "model": model_service.model.model_id,
                    "deep": True,
                }
            except Exception as llm_err:
                services["llm"] = {
                    "status": "unhealthy",
                    "provider": model_service.model.provider_id,
                    "model": model_service.model.model_id,
                    "error": str(llm_err),
                }
                overall = "unhealthy"
        else:
            services["llm"] = {
                "status": "healthy",
                "provider": model_service.model.provider_id,
                "model": model_service.model.model_id,
            }
    except Exception as e:
        services["llm"] = {"status": "unhealthy", "error": str(e)}
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
        timestamp=_utc_now(),
        services=services,
    )


@router.get("/health/ready")
async def readiness_check():
    """Readiness check for container orchestration."""
    return {"status": "ready", "timestamp": _utc_now()}


@router.get("/health/live")
async def liveness_check():
    """Liveness check for container orchestration."""
    return {"status": "alive", "timestamp": _utc_now()}
