"""Lambda handler for GRCInsight Python Agent Service."""

import os
from contextlib import asynccontextmanager
import time

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger
from mangum import Mangum

from api.routes import workflow, analysis, health, rss
from config.settings import settings
from core.runtime import (
    deadline_from_unix_ms,
    earliest_deadline,
    reset_model_deadline,
    reset_report_id,
    set_model_deadline,
    set_report_id,
)

LAMBDA_WRITEBACK_RESERVE_SECONDS = 120.0


def _lambda_model_deadline(
    context,
    caller_deadline_unix_ms=None,
    *,
    clock=time.monotonic,
    wall_clock=time.time,
) -> float | None:
    """Apply the earliest Lambda or synchronous-caller model deadline."""
    lambda_deadline = None
    get_remaining_time = getattr(context, "get_remaining_time_in_millis", None)
    if callable(get_remaining_time):
        remaining_seconds = max(0.0, float(get_remaining_time()) / 1000.0)
        model_seconds = max(0.0, remaining_seconds - LAMBDA_WRITEBACK_RESERVE_SECONDS)
        lambda_deadline = clock() + model_seconds

    caller_deadline = deadline_from_unix_ms(
        caller_deadline_unix_ms,
        monotonic_clock=clock,
        wall_clock=wall_clock,
    )
    return earliest_deadline(lambda_deadline, caller_deadline)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan events for Lambda."""
    logger.info("Starting GRCInsight Python Lambda Service")
    logger.info(f"Model configured: {settings.llm_model}")
    logger.info(f"Running in Lambda: {'Yes' if os.getenv('AWS_LAMBDA_FUNCTION_NAME') else 'No'}")
    yield
    logger.info("Lambda function execution completed")


# Create FastAPI application (same as regular service)
app = FastAPI(
    title="GRCInsight Python Agent (Lambda)",
    description="AI-powered GRC analysis service using LangGraph workflows (Serverless)",
    version="1.0.0",
    lifespan=lifespan,
    # For Lambda, we don't need docs in production
    docs_url="/docs" if not os.getenv("AWS_LAMBDA_FUNCTION_NAME") else None,
    redoc_url="/redoc" if not os.getenv("AWS_LAMBDA_FUNCTION_NAME") else None,
)

# Add CORS middleware (more restrictive for production Lambda)
# Allow override via settings; default more restrictive in Lambda
if os.getenv("AWS_LAMBDA_FUNCTION_NAME"):
    app.add_middleware(
        CORSMiddleware,
        allow_origins=(
            settings.cors_allowed_origins
            if settings.cors_allowed_origins
            else ["https://ricomanifesto.github.io"]
        ),
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )
else:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# Include routers (same as regular service)
app.include_router(health.router, prefix="/api/v1", tags=["health"])
app.include_router(workflow.router, prefix="/api/v1", tags=["workflow"])
app.include_router(analysis.router, prefix="/api/v1", tags=["analysis"])
app.include_router(rss.router, prefix="/api/v1", tags=["rss"])


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "GRCInsight Python Agent Service (Lambda)",
        "version": "1.0.0",
        "status": "running",
        "runtime": "AWS Lambda" if os.getenv("AWS_LAMBDA_FUNCTION_NAME") else "Local",
    }


def _history_tables():
    from history.service import history_tables

    return history_tables()


def _commit_report(report_id: str, event: dict, context, result) -> dict:
    """Write immutable evidence, then complete the admitted report job once.

    The job identity comes from the report row (or the event's ``job_id``),
    never from the Lambda request id, which is recorded for diagnosis only.
    """
    from history.service import commit_report

    try:
        status, body = commit_report(
            report_id=report_id,
            result=result,
            tables=_history_tables(),
            job_id=event.get("job_id") or None,
            invocation_id=getattr(context, "aws_request_id", None),
            feed_url=event.get("feed_url"),
            # Direct invocation requires IAM permission, so legacy rows without a
            # job id may still be completed here.
            require_job=False,
        )
    except Exception as ddb_err:
        logger.error(f"Failed to update DynamoDB for report {report_id}: {ddb_err}")
        return {
            "statusCode": 500,
            "body": {"status": "failed", "report_id": report_id, "error": str(ddb_err)},
        }
    logger.info(f"Report {report_id} history decision: {body['decision']}")
    return {"statusCode": status, "body": body}


# Create Mangum handler for AWS Lambda
mangum_handler = Mangum(app, lifespan="off")


def handler(event, context):
    """
    Lambda handler that supports both API Gateway events and direct invocations.
    """
    import asyncio
    import json

    # Check if this is a direct Lambda invocation (not API Gateway)
    if "httpMethod" not in event and "requestContext" not in event:
        # Direct Lambda invocation from Go Lambda
        logger.info("Handling direct Lambda invocation")

        # Handle health check
        if event.get("health_check"):
            return {
                "statusCode": 200,
                "body": {"status": "healthy", "message": "Python Lambda is running"},
            }

        # Handle workflow request
        if "feed_url" in event:
            try:
                from core.workflow import run_grc_analysis_endpoint
                from models.api import GRCAnalysisConfig

                # Extract parameters
                feed_url = event["feed_url"]
                config_data = event.get("config", {})

                # Create config object with proper defaults
                focus_areas = config_data.get("focus_areas")
                if focus_areas is None:
                    focus_areas = ["governance", "compliance"]

                config = GRCAnalysisConfig(
                    model=config_data.get(
                        "model",
                        "openrouter/nvidia/nemotron-3-ultra-550b-a55b:free",
                    ),
                    max_tokens=config_data.get("max_tokens", 16000),
                    focus_areas=focus_areas,
                )

                # Run the workflow. Diagnostics name the report they belong to.
                logger.info(f"Starting GRC workflow for {feed_url}")
                report_token = set_report_id(event.get("report_id"))
                try:
                    result = asyncio.run(
                        run_grc_analysis_endpoint(
                            feed_url,
                            config,
                            model_deadline=_lambda_model_deadline(
                                context,
                                event.get("caller_deadline_unix_ms"),
                            ),
                        )
                    )
                finally:
                    reset_report_id(report_token)

                # If invoked with report_id, commit the outcome to DynamoDB (async pattern).
                report_id = event.get("report_id")
                if report_id:
                    return _commit_report(report_id, event, context, result)

                # For sync invocations (no report_id), return full result
                return {"statusCode": 200, "body": json.loads(result.model_dump_json())}

            except Exception as e:
                logger.error(f"Workflow execution failed: {str(e)}")
                return {"statusCode": 500, "body": {"error": str(e), "status": "failed"}}

        # Unknown direct invocation format
        return {
            "statusCode": 400,
            "body": {"error": "Invalid direct invocation format", "status": "failed"},
        }

    # API Gateway event - use Mangum
    deadline_token = set_model_deadline(_lambda_model_deadline(context))
    try:
        return mangum_handler(event, context)
    finally:
        reset_model_deadline(deadline_token)


# For local testing
if __name__ == "__main__":
    import uvicorn

    logger.info("Starting Lambda service locally for testing")
    uvicorn.run(
        "lambda_main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.reload,
        log_level=settings.log_level.lower(),
    )
