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

New reports separate **Sourced Regulatory Changes** from **Evidence and Decisions**. Regulatory rows require a supported primary publisher, a matching source excerpt, a complete change phrase with exact source casing, and jurisdiction text matching a complete phrase with exact source casing or `Unknown`. The bounded publisher policy and row contract live in `agent/core/report_evidence.py`; source mentions and security news alone cannot establish a regulatory change. Source excerpts are retained in the evidence manifest for publication validation.

**Document effective date** is copied from publisher metadata, never inferred from prose. For selected FederalRegister.gov Rule documents, ingestion reads the public [document API](https://www.federalregister.gov/developers/documentation/api/v1) and retains its `effective_on` field, document identity, API URL, and retrieval timestamp. The prompt, stored report metadata, and evidence manifest share that receipt. Report generation and offline publication validation require the exact recorded date. Text-only sources, unsupported publishers, null dates, and failed lookups display `Unknown`; their source excerpts remain available. Lookups use a fixed HTTPS endpoint, no redirects, and a five-second total budget capped by the remaining invocation deadline. This is the publisher's document-level date, not an interpretation of a particular provision's deadline or legal applicability.

Report contract v5 requires an executive decision agenda above the source findings. The model selects a compatible decision frame and one to three supported lead sources in review order. The application writes a connected, answer-first narrative that identifies the management decision, conditional applicability, proposed priorities and evidence limits. The brief is normally two or three paragraphs; length limits prevent empty or padded output, rather than forcing a fixed word count. Arbitrary model-authored narrative remains prohibited.

Up to six findings retain one source ID each, an exact article-field excerpt and its `summary` or `content` origin, an exact short focus (at most eight words and 80 characters), a dominant control and an inferred priority. Each source excerpt appears once in supporting evidence. Evidence and Decisions combines the control implication, conditional priority, accountable function, evidence request and decision trigger for each finding. Identical findings share one entry with all their citations; a quotation already in the regulatory table is referenced without being repeated. Separate risk and recommendation sections are omitted because they would duplicate those entries. Sector-only mappings are refused: the current contract has no independently evidenced sector-consequence field, so it omits an Industry section instead of supplying unsupported relevance.

Editorial checks are separate from factual grounding. A publishable v5 report needs a supported executive frame, one to three distinct lead sources, a concise narrative opening, conditional applicability, citations alongside the agenda, and distinct brief/evidence/source sections. Whole-report recomposition rejects generic substitutions, excerpt-only summaries and rephrased duplicate sections. Repeated source citations and necessary identifiers remain valid. These checks constrain known failure patterns; they do not prove semantic novelty, correct ranking or the quality of every future judgment.

Ingestion retains up to two article receipts with their `summary` or `content` origins separately from headline identity. Each receipt contains the original field (`raw_text`, at most 4096 UTF-8 bytes), extraction version 1, and at most 700 characters of extracted text cut at a word boundary. The shared static-text boundary tokenizes raw HTML before decoding text-node entities, so references cannot alter attribute or tag boundaries. It extracts balanced supported HTML, preserves inline word continuity and block spacing, and excludes comments and hidden/non-content subtrees. It refuses oversized input, nested encoding, ambiguous or unknown markup, invisible control/format characters, stylesheets and presentation-dependent class/style/id attributes. This conservative subset can refuse useful publisher content; it does not execute scripts, fetch resources, or infer CSS visibility.

Findings quote the exact extracted text. Publication re-runs extraction from the retained raw field and version and requires identical text, so a normalization label alone cannot attest a quote. The headline passes through the same boundary only for copy detection; its original identity is unchanged. Canonical character-stream comparison rejects whole, partial and repeated headline copies despite typography or word splitting. It is not an editorial relevance score. Raw receipts and the selected origin survive storage, composition, manifest and offline validation; the model sees only extracted eligible passages. Historical origins are never reconstructed from a flattened snippet.

Generation and composition reject empty/category-only plans, missing or ambiguous article origins, title-only evidence, unavailable source IDs, unsupported excerpts/focuses, and arbitrary narrative fields. A regulatory-only report remains valid when its primary-source table passes the regulatory evidence gate. The plan, source snippets, model provenance, and dated Digest identity are retained unchanged in storage and the evidence manifest. Publication requires the exact deterministic rendering and contract v5, including after a rebase. Failed generation or validation retains the last successful report; it cannot manufacture a replacement summary. Exhausted plan-validation retries carry an actionable diagnostic as `report_quality`, distinct from a provider-provenance refusal.

The catalog and renderer in `agent/core/report_plan.py` are versioned: contracts v3 and v4 remain available for exact verification of existing publications, not for new publication. Historical Markdown and manifests are not upgraded. No free-form model narrative, invented IDs, or model-authored date fields are accepted. Exact quote correspondence is a mechanical grounding check, not proof of a source's truth, a complete quotation, an appropriate model-selected priority, or legal applicability. Prompts require preservation of conditions, negation, and uncertainty; editorial evaluation remains necessary.

Retained source positions and original URL identities remain unchanged through storage and publication, including repeated URLs. Markdown destination escaping happens only when rendering links, so it cannot change SentryDigest reporting fragments or shift the plan's source numbers.

The reading view uses compact numbered citations with full accessible titles, keyed by source title and URL so repeated URLs with different titles keep distinct highlights. Source Highlights keeps the complete source links and dated Digest context. Archived Markdown and evidence manifests retain their original bytes; archived HTML is rebuilt with the current reader. Older reports disclose that their regulatory context predates the separate evidence check. Failed-refresh notices derive both displayed timestamps from publication state and keep diagnostics under expandable details.

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

`.github/workflows/lambda-report-generation.yml` runs after a SentryDigest dispatch, daily at 13:00 UTC, or by manual trigger. Requests to `:free` model routes (and the free router) disable provider fallbacks and enforce zero prompt, completion, request, and image price ceilings. The default route is `openrouter/nvidia/nemotron-3-ultra-550b-a55b:free`; set the repository variable `LLM_MODEL` to override it. AWS credentials and `OPENROUTER_API_KEY` are required repository secrets.

`.github/workflows/deploy-site.yml` is the only Pages deployment workflow. It validates the committed `site/` directory, captures light and dark screenshots, and deploys that same artifact.
