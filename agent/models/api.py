"""Pydantic models for API requests and responses."""

from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


# Request Models
class AnalysisConfig(BaseModel):
    """Configuration for GRC analysis."""
    model: str = "gpt-5"
    max_tokens: int = 4000
    focus_areas: List[str] = Field(default_factory=list)


class ArticleInput(BaseModel):
    """Input model for an article to be analyzed."""
    title: str
    url: str
    content: str
    summary: str = ""
    source: str = ""
    published: datetime


class ArticleRecord(ArticleInput):
    """Article with extracted GRC analysis details."""
    has_grc_content: bool = False
    regulations: List[str] = Field(default_factory=list)
    frameworks: List[str] = Field(default_factory=list)
    industries: List[str] = Field(default_factory=list)
    regulatory_bodies: List[str] = Field(default_factory=list)


class WorkflowRequest(BaseModel):
    """Request model for running the complete GRC workflow."""
    feed_url: str = Field(..., description="URL of the RSS feed to analyze")
    config: AnalysisConfig = Field(default_factory=AnalysisConfig)


class AnalysisRequest(BaseModel):
    """Request model for analyzing specific articles."""
    articles: List[ArticleInput]
    config: AnalysisConfig = Field(default_factory=AnalysisConfig)


# Response Models
class APIError(BaseModel):
    """Error response model."""
    code: str
    message: str
    details: Optional[str] = None


class AnalysisResult(BaseModel):
    """Analysis result for a single article."""
    article_url: str
    has_grc_content: bool
    regulations: List[str] = Field(default_factory=list)
    frameworks: List[str] = Field(default_factory=list)
    industries: List[str] = Field(default_factory=list)
    regulatory_bodies: List[str] = Field(default_factory=list)
    risk_levels: List[str] = Field(default_factory=list)


class AnalysisSummary(BaseModel):
    """Summary of analysis results."""
    total_articles: int
    grc_articles: int
    top_regulations: List[str] = Field(default_factory=list)
    top_frameworks: List[str] = Field(default_factory=list)
    affected_industries: List[str] = Field(default_factory=list)


class AnalysisResponse(BaseModel):
    """Response model for analysis requests."""
    status: str
    results: List[AnalysisResult] = Field(default_factory=list)
    summary: AnalysisSummary
    error: Optional[APIError] = None


class ReportMetadata(BaseModel):
    """Metadata for generated reports."""
    article_count: int
    grc_article_count: int
    regulations_mentioned: List[str] = Field(default_factory=list)
    frameworks_referenced: List[str] = Field(default_factory=list)
    industries_affected: List[str] = Field(default_factory=list)
    regulatory_bodies: List[str] = Field(default_factory=list)


class Report(BaseModel):
    """Generated GRC report."""
    title: str
    content: str
    generated_at: datetime
    metadata: Optional[ReportMetadata] = None


class WorkflowResponse(BaseModel):
    """Response model for workflow execution."""
    status: str
    report_id: Optional[str] = None
    report: Optional[Report] = None
    error: Optional[APIError] = None
    metadata: Optional[ReportMetadata] = None
    articles: Optional[List[ArticleRecord]] = None


class HealthStatus(BaseModel):
    """Health status response."""
    status: str
    timestamp: datetime
    version: str = "1.0.0"
    services: Dict[str, Any] = Field(default_factory=dict)


class RSSFeedResponse(BaseModel):
    """RSS feed fetch response."""
    title: str
    description: str = ""
    link: str = ""
    last_updated: str = ""
    entry_count: int
    entries: List[Dict[str, Any]] = Field(default_factory=list)
    error: Optional[str] = None
