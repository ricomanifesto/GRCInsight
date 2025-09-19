"""FastAPI server for GRCInsight Python Agent Service."""

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from api.routes import workflow, analysis, health, rss
from config.settings import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan events."""
    logger.info("Starting GRCInsight Python Agent Service")
    logger.info(f"OpenAI API Key configured: {'Yes' if settings.openai_api_key else 'No'}")
    yield
    logger.info("Shutting down GRCInsight Python Agent Service")


# Create FastAPI application
app = FastAPI(
    title="GRCInsight Python Agent",
    description="AI-powered GRC analysis service using LangGraph workflows",
    version="1.0.0",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router, prefix="/api/v1", tags=["health"])
app.include_router(workflow.router, prefix="/api/v1", tags=["workflow"])
app.include_router(analysis.router, prefix="/api/v1", tags=["analysis"])
app.include_router(rss.router, prefix="/api/v1", tags=["rss"])

# Root endpoint
@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "GRCInsight Python Agent Service",
        "version": "1.0.0",
        "status": "running"
    }


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.reload,
        log_level=settings.log_level.lower(),
    )
