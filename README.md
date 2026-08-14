# GRCInsight

<div align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="assets/images/logo-lockup-dark.png">
    <img src="assets/images/logo-lockup-light.png" alt="GRCInsight" width="440">
  </picture>
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

GRCInsight can be triggered by updates from [SentryDigest](https://github.com/ricomanifesto/SentryDigest), using security-news updates as one input for GRC-focused analysis. Each published source handoff targets the dated SentryDigest issue identified by the feed's UTC build timestamp, so an immutable GRC report never depends on the rolling digest page. Reporting-card fragments are checked against a byte-identical copy of SentryDigest's versioned `contracts/reporting-identity-v1.json` contract.

## Architecture

- **Go Lambda:** API handling, DynamoDB writes, and Python Lambda invocation.
- **Python Lambda:** RSS fetch, model-backed analysis, and report composition.
- **GitHub Actions:** Lambda deployment, scheduled report generation, deterministic site composition, visual review evidence, and GitHub Pages publishing.

## Setup

Install Python agent dependencies:

```bash
cd agent
uv sync
```

Configure model access:

```bash
export OPENROUTER_API_KEY=your-openrouter-api-key
export LLM_MODEL=openrouter/nvidia/nemotron-3-ultra-550b-a55b:free
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
- Model-backed analysis calls OpenRouter directly in local and Lambda environments.
- Report provenance distinguishes the configured OpenRouter route from the
  upstream model returned with the successful report completion. Publication
  fails closed when that resolved model identity is absent or remains a router
  alias.
- Every published report exposes `evidence-manifest.json`, including the feed,
  resolved model, feed-owned digest issue, exact source title/URL pairs, CVE
  coverage, and stable links to the corresponding dated SentryDigest items.
- `.github/workflows/lambda-report-generation.yml` refuses fallback output,
  composes report-owned provenance into `site/index.md`, preserves a dated
  archive snapshot, pre-renders the current/archive pages, validates the result,
  and commits the artifact to `main`.
- `.github/workflows/deploy-site.yml` is the single Pages deployment owner. It
  revalidates the committed artifact, captures dark and light top-of-fold review
  images, uploads that evidence to the workflow run, and deploys `site/`.
