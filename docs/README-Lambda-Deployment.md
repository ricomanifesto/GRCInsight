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
- Optional repository variables: `GRC_RELEVANCE_MODE`, `GRC_RELEVANCE_MIN_PROBABILITY`,
  and `GRC_RELEVANCE_TIMEOUT_SECONDS`. The workflow forwards them to the Python
  Lambda and otherwise uses the application's `off`, `0.95`, and `4` defaults.
  Mode must be `off`, `shadow`, or `enabled`; minimum probability must be between
  0.5 and 1, and timeout must be greater than 0 and at most 10 seconds. Invalid
  values stop the workflow before image builds or Lambda updates.

The workflow:

1. Verifies the shared reporting-identity files.
2. Verifies preprovisioned ECR repositories and their existing Lambda retrieval grants without replacing policies.
3. Builds and pushes amd64 images tagged with the commit SHA and `latest`.
4. Updates the existing Lambda functions and their environment variables.
5. Waits for both functions to become active.
6. Verifies image references and checks Go health. If Go reserved concurrency is zero, it explicitly defers Go API health and checks only Python's non-inference health path; it never restores concurrency.

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

Manual authentication can use existing `aws configure` credentials or a selected
profile, as well as an already exported AWS key pair/session token. The explicit
manual helper mode delegates authentication to the same AWS CLI through only
`HOME`, `AWS_PROFILE`, `AWS_DEFAULT_PROFILE`, `AWS_CONFIG_FILE`,
`AWS_SHARED_CREDENTIALS_FILE`, and already present key-pair/token variables. Python
does not read, export or copy credentials from those files. Existing profile
credential processes, role assumption or SSO-cache behavior may run or refresh as
the CLI normally does; this is not a static/no-refresh credential resolver. No
login, profile creation or permission change is performed by the helper.

The script reuses its read-only STS identity check through that exact helper auth
context before any ECR, image or Lambda mutation. Missing/partial credentials,
invalid configuration or authentication failure stop before effects; no existing
Lambda is needed for this bootstrap preflight. It verifies identity, not all later
resource permissions. Unsupported ambient web-identity/container role selectors
are refused rather than silently choosing another credential path.

Both STS and Lambda helper requests use fixed, TLS-verified `us-east-1` endpoints,
overriding configured service endpoint URLs. Child environments do not inherit
proxy, debug or OpenRouter-key variables and disable the pager. A non-database
history destination is exported at the start for all manual AWS descendants,
including direct existence checks/waiters, so CLI history cannot persist private
configuration responses. The helper sends environment JSON only over stdin and retains the
single-attempt RevisionId-CAS merge. GitHub Actions continues to use isolated
explicit environment credentials and `/dev/null` config files; it does not enable
manual profile mode. The broader manual bootstrap effects still require separate
operator review and are not the normal existing-function release path.

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
