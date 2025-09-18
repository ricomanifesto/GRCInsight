# AWS Lambda Deployment

Go Lambda orchestrates API and DynamoDB. Python Lambda analyzes feeds and writes back results. GitHub Actions builds, deploys, and schedules runs.

## Prerequisites

- AWS account with ECR and Lambda access
- AWS CLI and Docker installed
- OpenAI API key

## CI Deploy (recommended)

- Add repo secrets: `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `OPENAI_API_KEY`
- Run `.github/workflows/deploy-lambda.yml` (manual or push to `main`)
- Workflow builds both images with `DOCKER_BUILDKIT=0`, pushes to ECR, updates Lambdas, and smoke‑tests `/health`

## Manual Deploy

```bash
export OPENAI_API_KEY=your-key
export AWS_REGION=us-east-1
export DOCKER_BUILDKIT=0
./scripts/deploy-lambda.sh
```

The script creates ECR repos if missing, builds/pushes images, creates or updates roles and functions, and sets env vars.

## Architecture Constraints

- Images target amd64. Go build sets `GOARCH=amd64`. Python base image is digest‑pinned to amd64.
- BuildKit is disabled to emit Docker schema v2 manifests accepted by Lambda.

## Test

```bash
# Health
aws lambda invoke --function-name grcinsight-go-function \
  --payload '{"httpMethod":"GET","path":"/health"}' health.json && cat health.json

# Generate
aws lambda invoke --function-name grcinsight-go-function \
  --payload '{"httpMethod":"POST","path":"/api/v1/reports/generate","body":"{\"feed_url\":\"https://example.com/feed.xml\"}"}' out.json && cat out.json
```

## Monitoring

```bash
aws logs describe-log-groups --log-group-name-prefix /aws/lambda/grcinsight-go-function
aws cloudwatch get-metric-statistics --namespace AWS/Lambda --metric-name Duration \
  --dimensions Name=FunctionName,Value=grcinsight-go-function \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) --period 300 --statistics Average,Maximum
```

## Cleanup

```bash
aws lambda delete-function --function-name grcinsight-go-function
aws lambda delete-function --function-name grcinsight-python-function
aws ecr delete-repository --repository-name grcinsight-go --force
aws ecr delete-repository --repository-name grcinsight-python --force
aws iam detach-role-policy --role-name grcinsight-lambda-role \
  --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole
aws iam delete-role --role-name grcinsight-lambda-role
```

## Local vs Lambda

- Local: `cmd/server/main.go`, `agent/main.py`
- Lambda: `cmd/lambda/main.go`, `agent/lambda_main.py`
