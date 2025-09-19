# Developer Guide

This guide summarizes environment setup, provisioning, and how to run tests and a quick end‑to‑end check.

## Prerequisites
- Go 1.21+
- Python 3.10+
- Node: not required
- AWS credentials (for DynamoDB), region set (e.g., `AWS_REGION=us-east-1`)
- Terraform >= 1.5 (for infra)
- jq (for E2E script)

## Infra Provisioning (Terraform)
Provision the articles table + GSIs used by the app.

```
cd configs/terraform/articles-table
terraform init
terraform apply -var "aws_region=us-east-1" -var "articles_table_name=grcinsight-articles"
```

Set environment variables for the services:
- `DDB_TABLE_NAME=grcinsight-reports`
- `ARTICLES_TABLE_NAME=grcinsight-articles`

## Environment Variables
- Python agent
  - `OPENAI_API_KEY` (required for real analysis)
  - `CORS_ALLOWED_ORIGINS` (optional; comma‑separated, or use `.env` with `cors_allowed_origins`)
  - `DDB_TABLE_NAME`, `ARTICLES_TABLE_NAME` if running in Lambda mode and using the status/async paths
- Go API
  - `SERVICE_VERSION` (optional; shows in health output)
  - Python client
    - Lambda mode: `PYTHON_LAMBDA_FUNCTION_NAME`, `PYTHON_INVOKE_ASYNC`
    - HTTP mode: `PYTHON_SERVICE_URL` (defaults to `http://localhost:8081`)

## Run Services Locally
- Python agent (FastAPI)
```
cd agent
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8081
```

- Go API (Gin)
```
go run ./cmd/server
```
(Adjust entrypoint to your project layout if different.)

## Tests
A Makefile provides common tasks.

- Go tests
```
make test-go
```

- Python tests
```
# Optional: install dev deps
pip install -r agent/requirements.txt
pip install -r agent/requirements-dev.txt

# Run tests
make test-agent
```

## End‑to‑End Check
Use the script to generate a report from an RSS feed and verify articles are persisted.

```
FEED_URL="https://example.com/rss" \
API_URL="http://localhost:8080" \
PYTHON_URL="http://localhost:8081" \
make e2e
```

The script:
- (Optional) Deep health check on Python agent
- POST `/api/v1/reports/generate`
- Poll GET `/api/v1/reports/{id}/status`
- GET `/api/v1/reports/{id}/articles`

## Notes
- Default model remains `gpt-5` (runtime fallback is handled in code if unavailable).
- Articles table benefits from GSIs (`by-report-id`, `by-url`); the Terraform module creates these.
- For serverless, use `agent/lambda_main.py` packaged behind API Gateway or direct Lambda invokes.
