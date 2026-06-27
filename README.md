# GRCInsight

<div align="center">
  <img src="assets/images/logo.png" alt="GRCInsight Logo" width="400"/>
</div>

Automated GRC intelligence: monitor RSS feeds, extract regulatory signals, and publish AI‑generated reports.

[Latest Report](https://ricomanifesto.github.io/GRCInsight/)

## Features

- Monitors security feeds and filters for GRC relevance
- Correlates regulations, frameworks, industries, and agencies
- Generates concise reports with summaries and actions
- Automatically triggered by updates to [SentryDigest](https://github.com/ricomanifesto/SentryDigest) repository

## Architecture

- Go Lambda: API, DynamoDB writes, Python Lambda invoke
- Python Lambda: RSS fetch, model-backed analysis, report compose
- GitHub Actions: deploy Lambdas, schedule runs, publish Pages

## Setup

- Python agent deps: `cd agent && uv sync`
- Model gateway: run OpenCode and set `OPENCODE_BASE_URL`
- Model: set `LLM_MODEL=openrouter/provider-model`
- Go config: edit `configs/config.yaml`

## Use Locally

```bash
# Python agent
cd agent && uv run uvicorn main:app --host 0.0.0.0 --port 8081 --reload

# Go API
go run ./cmd/server
```

## Local Checks

```bash
make check
```

## Production

- Deploy: push to `main` or run `.github/workflows/deploy-lambda.yml`
- Secrets: `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `OPENROUTER_API_KEY`
- Runtime variables: `LLM_MODEL=openrouter/provider-model`
- Lambda model-backed analysis calls OpenRouter directly when `OPENROUTER_API_KEY` is configured. Local development can still use OpenCode with `OPENCODE_BASE_URL`.
- Reports: `.github/workflows/lambda-report-generation.yml` writes to `site/` and deploys Pages
