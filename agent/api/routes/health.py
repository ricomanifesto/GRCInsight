"""Health check endpoints."""

from datetime import datetime
from fastapi import APIRouter
from loguru import logger

from models.api import HealthStatus

router = APIRouter()


@router.get("/health", response_model=HealthStatus)
async def health_check():
    """Comprehensive health check."""
    logger.info("Health check requested")
    
    # TODO: Add actual service checks (OpenAI API, etc.)
    services = {
        "openai": {"status": "healthy"},  # Will implement actual check
        "workflow": {"status": "healthy"},
    }
    
    return HealthStatus(
        status="healthy",
        timestamp=datetime.utcnow(),
        services=services
    )


@router.get("/health/ready")
async def readiness_check():
    """Readiness check for container orchestration."""
    return {"status": "ready", "timestamp": datetime.utcnow()}


@router.get("/health/live") 
async def liveness_check():
    """Liveness check for container orchestration."""
    return {"status": "alive", "timestamp": datetime.utcnow()}