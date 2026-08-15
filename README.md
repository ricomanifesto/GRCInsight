# GRCInsight

<div align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="assets/images/logo-lockup-dark.png">
    <img src="assets/images/logo-lockup-light.png" alt="GRCInsight" width="440">
  </picture>
</div>

GRCInsight reads security and regulatory news and publishes a report for governance, risk, and compliance review.

**[Read the latest GRC report](https://ricomanifesto.github.io/GRCInsight/)**

## What the Report Shows

- The source event and why it may matter.
- Relevant regulations, frameworks, agencies, and industries.
- Evidence links back to the original article and the dated [SentryDigest](https://github.com/ricomanifesto/SentryDigest) issue.
- Suggested review or follow-up actions.
- The model and source records used to create the report.

The site keeps dated reports and a [publication history](https://ricomanifesto.github.io/GRCInsight/publication-history/) of recorded publication and retention outcomes. Runs that fail before either outcome is recorded do not appear in that history.

## How It Works

1. The Go service accepts report requests, stores report state in DynamoDB, and invokes the Python service.
2. The Python service fetches RSS articles, filters for GRC relevance, and asks the configured OpenRouter model to compose a report.
3. The report workflow retrieves the result and checks its model identity, source issue, citations, and analysis mode.
4. Only a model-backed report with complete source and model records is published. A completed fallback-mode report keeps the last verified report and records a short refusal category. Other generation or provenance failures also keep the last verified report, but exit before adding a history event.
5. A static builder creates the current page, dated archive, evidence manifest, and publication-history page before GitHub Pages deploys them.

The stable article links shared with SentryDigest and SentryInsight follow SentryDigest's [reporting identity contract](https://github.com/ricomanifesto/SentryDigest/blob/main/contracts/README.md).

## Run It Locally

You need Go 1.24, Python 3.11, and [`uv`](https://docs.astral.sh/uv/). Copy `.env.example` to `.env` and replace the placeholder values before calling model or AWS services.

For model-backed analysis, set:

```bash
export OPENROUTER_API_KEY=...
export LLM_MODEL=openrouter/nvidia/nemotron-3-ultra-550b-a55b:free
```

Start the Python service:

```bash
cd agent
uv sync --locked
uv run uvicorn main:app --host 0.0.0.0 --port 8081 --reload
```

Start the Go API from the repository root:

```bash
go run ./cmd/server
```

Before starting it, configure AWS credentials. Make the `grcinsight-reports` DynamoDB table available in the configured region, or point `DATABASE_ENDPOINT` at a compatible local DynamoDB instance with that table. Startup calls `DescribeTable` and exits if the reports table is unavailable.

The Go service listens on port 8080 and calls the Python service at `http://localhost:8081` by default. Edit `configs/config.yaml` or use environment variables to change those settings.

## Checks

```bash
make check
```

This checks Go formatting and tests; Python tests, linting, formatting, and types; and the committed site. The site checks prove that generated HTML matches its Markdown and JSON inputs, citations belong to the analyzed source set, archive and publication state agree, and the shared renderer handles links and report sections safely.

Focused commands are also available:

```bash
make test-go
make test-agent
make check-site
```

## Deployment and Publishing

- [Lambda deployment guide](docs/README-Lambda-Deployment.md)
- [Static-site contract](site/README.md)
- [DynamoDB articles-table module](configs/terraform/articles-table/README.md)

`.github/workflows/deploy-lambda.yml` runs on every push to `main` or by manual trigger. It deploys the Go and Python Lambda images and checks the Go health endpoint.

`.github/workflows/lambda-report-generation.yml` runs after a SentryDigest dispatch, daily at 13:00 UTC, or by manual trigger. The default route is `openrouter/nvidia/nemotron-3-ultra-550b-a55b:free`; set the repository variable `LLM_MODEL` to override it. AWS credentials and `OPENROUTER_API_KEY` are required repository secrets.

`.github/workflows/deploy-site.yml` is the only Pages deployment workflow. It validates the committed `site/` directory, captures light and dark screenshots, and deploys that same artifact.
