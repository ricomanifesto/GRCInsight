# GRCInsight

<div align="center">
  <img src="assets/images/logo.png" alt="GRCInsight Logo" width="400"/>
</div>

GRCInsight turns regulatory and security feeds into audit-ready GRC intelligence, with framework mapping, agency signals, industry relevance, and concise action-oriented reports.

**[Latest Report](https://ricomanifesto.github.io/GRCInsight/)**

## What It Does

GRCInsight monitors security and regulatory feeds, filters for governance, risk, and compliance relevance, and publishes generated reports for review. It is designed to translate raw feed activity into signals a reviewer can map to obligations, frameworks, industries, agencies, and next actions.

## Report Coverage

Generated reports can include:

- regulatory and agency signals
- framework and control relevance
- affected industries
- concise summaries
- action-oriented findings
- published Pages output

## Relationship to SentryDigest

GRCInsight can be triggered by updates from [SentryDigest](https://github.com/ricomanifesto/SentryDigest), using security-news updates as one input for GRC-focused analysis.

## Architecture

- **Go Lambda:** API handling, DynamoDB writes, and Python Lambda invocation.
- **Python Lambda:** RSS fetch, model-backed analysis, and report composition.
- **GitHub Actions:** Lambda deployment, scheduled report generation, and GitHub Pages publishing.

## Setup

Install Python agent dependencies:

```bash
cd agent
uv sync
```

Configure model access:

```bash
export OPENCODE_BASE_URL=http://127.0.0.1:4096
export LLM_MODEL=openrouter/provider-model
```

Edit Go service configuration in `configs/config.yaml`.

## Use Locally

Run the Python agent:

```bash
cd agent
uv run uvicorn main:app --host 0.0.0.0 --port 8081 --reload
```

Run the Go API:

```bash
go run ./cmd/server
```

## Local Checks

```bash
make check
```

## Production

- Deploy by pushing to `main` or running `.github/workflows/deploy-lambda.yml`.
- Required secrets: `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `OPENROUTER_API_KEY`.
- Runtime variable: `LLM_MODEL=openrouter/provider-model`.
- Lambda model-backed analysis calls OpenRouter directly when `OPENROUTER_API_KEY` is configured.
- Local development can still use OpenCode with `OPENCODE_BASE_URL`.
- `.github/workflows/lambda-report-generation.yml` writes reports to `site/` and deploys GitHub Pages.
