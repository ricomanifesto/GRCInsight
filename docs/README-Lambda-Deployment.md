# AWS Lambda Deployment

GRCInsight runs two container-based Lambda functions:

- `grcinsight-go-function` handles the API and DynamoDB access.
- `grcinsight-python-function` fetches feeds and performs model-backed analysis.

The Go function invokes the Python function for report generation.

## Prerequisites

- AWS CLI and Docker.
- An AWS account with ECR, Lambda, IAM, DynamoDB, and CloudWatch access.
- Existing `grcinsight-reports` and `grcinsight-articles` DynamoDB tables.
- An OpenRouter API key.
- amd64 container support.

## GitHub Actions Deployment

`.github/workflows/deploy-lambda.yml` runs on pushes to `main` and by manual trigger. Configure:

- Repository secrets: `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `OPENROUTER_API_KEY`.
- Repository variable: `LLM_MODEL`, using `openrouter/provider-model` format. If unset, the workflow uses `openrouter/nvidia/nemotron-3-ultra-550b-a55b:free`.

The workflow:

1. Verifies the shared reporting-identity files.
2. Creates the two ECR repositories if needed.
3. Builds and pushes amd64 images tagged with the commit SHA and `latest`.
4. Updates the existing Lambda functions and their environment variables.
5. Waits for both functions to become active.
6. Invokes the Go `/health` route and requires a healthy response.

The workflow updates Lambda functions; it does not create missing functions or their execution role.

## Manual Deployment

The manual script can create missing ECR repositories, the shared Lambda role, and the two functions before updating them:

```bash
export AWS_REGION=us-east-1
export OPENROUTER_API_KEY=...
export LLM_MODEL=openrouter/nvidia/nemotron-3-ultra-550b-a55b:free
export DOCKER_BUILDKIT=0
./scripts/deploy-lambda.sh
```

The script changes AWS resources and pushes container images. Review it and confirm the active AWS account before running it.

## Container Constraints

- Both images target `linux/amd64`.
- The Go build sets `GOARCH=amd64`.
- The Python Lambda base image is pinned by digest.
- Docker BuildKit is disabled so Lambda receives Docker schema v2 image manifests.

## Smoke Checks

Health route:

```bash
aws lambda invoke \
  --function-name grcinsight-go-function \
  --payload '{"httpMethod":"GET","path":"/health"}' \
  --cli-binary-format raw-in-base64-out \
  health.json
jq . health.json
```

Start a report:

```bash
aws lambda invoke \
  --function-name grcinsight-go-function \
  --payload '{"httpMethod":"POST","path":"/api/v1/reports/generate","body":"{\"feed_url\":\"https://example.com/feed.xml\"}"}' \
  --cli-binary-format raw-in-base64-out \
  report.json
jq . report.json
```

The report request is asynchronous in the production configuration. Use the returned report ID with `GET /api/v1/reports/{id}` to read its status.

## Logs

```bash
aws logs describe-log-groups \
  --log-group-name-prefix /aws/lambda/grcinsight-
```

Use CloudWatch Logs to inspect a failed health check or report request. Do not publish raw provider errors; the public site exposes only allowlisted refusal categories.
