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
- Python Lambda: RSS fetch, AI analysis, report compose
- GitHub Actions: deploy Lambdas, schedule runs, publish Pages

## Setup

- Python deps: `pip install -r requirements.txt`
- OpenAI key: `echo OPENAI_API_KEY=your-key > .env`
- Go config: edit `configs/config.yaml`

## Use Locally

```bash
# Python agent
cd agent && uvicorn main:app --host 0.0.0.0 --port 8081 --reload

# Go API
go run ./cmd/server
```

## Production

- Deploy: push to `main` or run `.github/workflows/deploy-lambda.yml`
- Secrets: `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `OPENAI_API_KEY`
- Reports: `.github/workflows/lambda-report-generation.yml` writes to `site/` and deploys Pages

## Legacy

Legacy single‑process Python lives under `legacy/`. Prefer the Go/Python Lambdas.
