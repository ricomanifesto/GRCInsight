"""Lambda handler for GRCInsight Python Agent Service."""

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger
from mangum import Mangum

from api.routes import workflow, analysis, health, rss
import boto3
from datetime import datetime, timezone
from config.settings import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan events for Lambda."""
    logger.info("Starting GRCInsight Python Lambda Service")
    logger.info(f"OpenAI API Key configured: {'Yes' if settings.openai_api_key else 'No'}")
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
    docs_url="/docs" if not os.getenv('AWS_LAMBDA_FUNCTION_NAME') else None,
    redoc_url="/redoc" if not os.getenv('AWS_LAMBDA_FUNCTION_NAME') else None,
)

# Add CORS middleware (more restrictive for production Lambda)
# Allow override via settings; default more restrictive in Lambda
if os.getenv('AWS_LAMBDA_FUNCTION_NAME'):
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allowed_origins if settings.cors_allowed_origins else ["https://ricomanifesto.github.io"],
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
        "runtime": "AWS Lambda" if os.getenv('AWS_LAMBDA_FUNCTION_NAME') else "Local"
    }


# Create Mangum handler for AWS Lambda
mangum_handler = Mangum(app, lifespan="off")


def handler(event, context):
    """
    Lambda handler that supports both API Gateway events and direct invocations.
    """
    import asyncio
    import json

    # Check if this is a direct Lambda invocation (not API Gateway)
    if 'httpMethod' not in event and 'requestContext' not in event:
        # Direct Lambda invocation from Go Lambda
        logger.info("Handling direct Lambda invocation")

        # Handle health check
        if event.get('health_check'):
            return {
                'statusCode': 200,
                'body': {'status': 'healthy', 'message': 'Python Lambda is running'}
            }

        # Handle workflow request
        if 'feed_url' in event:
            try:
                from core.workflow import run_grc_analysis_endpoint
                from models.api import AnalysisConfig

                # Extract parameters
                feed_url = event['feed_url']
                config_data = event.get('config', {})

                # Create config object with proper defaults
                focus_areas = config_data.get('focus_areas')
                if focus_areas is None:
                    focus_areas = ['governance', 'compliance']

                config = AnalysisConfig(
                    model=config_data.get('model', 'gpt-5'),
                    max_tokens=config_data.get('max_tokens', 4000),
                    focus_areas=focus_areas
                )

                # Run the workflow
                logger.info(f"Starting GRC workflow for {feed_url}")
                result = asyncio.run(run_grc_analysis_endpoint(feed_url, config))

                # If invoked with report_id, perform DynamoDB writeback (async pattern)
                report_id = event.get('report_id')
                if report_id:
                    try:
                        table_name = os.getenv('DDB_TABLE_NAME', 'grcinsight-reports')
                        ddb = boto3.resource('dynamodb')
                        table = ddb.Table(table_name)

                        now_iso = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')

                        # Build metadata map from result.metadata if present
                        metadata = None
                        if result.metadata is not None:
                            md = result.metadata
                            metadata = {
                                'article_count': md.article_count,
                                'grc_article_count': md.grc_article_count,
                                'regulations_mentioned': md.regulations_mentioned or [],
                                'frameworks_referenced': md.frameworks_referenced or [],
                                'industries_affected': md.industries_affected or [],
                                'regulatory_bodies': md.regulatory_bodies or [],
                            }

                        update_expr = [
                            'SET #title = :title',
                            '#content = :content',
                            '#status = :status',
                            'updated_at = :updated_at',
                            'generated_at = :generated_at',
                        ]
                        expr_attr_names = {
                            '#title': 'title',
                            '#content': 'content',
                            '#status': 'status',
                        }
                        expr_attr_values = {
                            ':title': result.report.title if result.report else f'GRC Intelligence Report - {now_iso[:10]}',
                            ':content': result.report.content if result.report else '# No content',
                            ':status': 'completed' if result.status == 'completed' else 'failed',
                            ':updated_at': now_iso,
                            ':generated_at': now_iso,
                        }
                        if metadata is not None:
                            update_expr.append('metadata = :metadata')
                            expr_attr_values[':metadata'] = metadata

                        table.update_item(
                            Key={'report_id': report_id},
                            UpdateExpression=', '.join(update_expr),
                            ExpressionAttributeNames=expr_attr_names,
                            ExpressionAttributeValues=expr_attr_values,
                            ConditionExpression='attribute_exists(report_id)'
                        )
                        logger.info(f"DynamoDB updated for report {report_id}")

                        # Optionally persist analyzed articles to the articles table
                        try:
                            articles = []
                            if result.articles is not None:
                                # Pydantic model to dict list
                                articles = [a if isinstance(a, dict) else a.model_dump() for a in result.articles]
                            articles_table_name = os.getenv('ARTICLES_TABLE_NAME', 'grcinsight-articles')
                            if articles and articles_table_name:
                                atable = ddb.Table(articles_table_name)

                                def fnv1a_32(data: str) -> int:
                                    h = 2166136261
                                    for ch in data.encode('utf-8'):
                                        h ^= ch
                                        h = (h * 16777619) & 0xFFFFFFFF
                                    return h

                                now_iso = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
                                date_prefix = now_iso[:10].replace('-', '')
                                with atable.batch_writer() as batch:
                                    for a in articles:
                                        url = a.get('url', '')
                                        nid = fnv1a_32(url) if url else 0
                                        art_id = f"a_{date_prefix}_{nid:08x}"
                                        item = {
                                            'article_id': art_id,
                                            'numeric_id': nid,
                                            'report_id': report_id,
                                            'title': a.get('title', ''),
                                            'url': url,
                                            'content': a.get('content', '')[:50000],
                                            'summary': a.get('summary', ''),
                                            'source': a.get('source', ''),
                                            'published': (a.get('published') if isinstance(a.get('published'), str) else now_iso),
                                            'created_at': now_iso,
                                            'updated_at': now_iso,
                                            'has_grc_content': bool(a.get('has_grc_content', False)),
                                            'regulations': a.get('regulations', []) or [],
                                            'frameworks': a.get('frameworks', []) or [],
                                            'industries': a.get('industries', []) or [],
                                            'regulatory_bodies': a.get('regulatory_bodies', []) or [],
                                        }
                                        batch.put_item(Item=item)
                                logger.info(f"Persisted {len(articles)} articles to {articles_table_name}")
                        except Exception as art_err:
                            logger.warning(f"Failed to persist articles: {art_err}")

                        # For async invocations, return simple success response
                        return {
                            'statusCode': 200,
                            'body': {
                                'status': 'completed',
                                'report_id': report_id,
                                'message': 'Report generated and saved to DynamoDB'
                            }
                        }
                    except Exception as ddb_err:
                        logger.error(f"Failed to update DynamoDB for report {report_id}: {ddb_err}")
                        return {
                            'statusCode': 500,
                            'body': {
                                'status': 'failed',
                                'report_id': report_id,
                                'error': str(ddb_err)
                            }
                        }

                # For sync invocations (no report_id), return full result
                return {
                    'statusCode': 200,
                    'body': json.loads(result.json())
                }

            except Exception as e:
                logger.error(f"Workflow execution failed: {str(e)}")
                return {
                    'statusCode': 500,
                    'body': {'error': str(e), 'status': 'failed'}
                }

        # Unknown direct invocation format
        return {
            'statusCode': 400,
            'body': {'error': 'Invalid direct invocation format', 'status': 'failed'}
        }

    # API Gateway event - use Mangum
    return mangum_handler(event, context)


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
