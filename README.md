# GRCInsight

<div align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="assets/images/logo-lockup-dark.png">
    <img src="assets/images/logo-lockup-light.png" alt="GRCInsight" width="440">
  </picture>
</div>

GRCInsight reads security and regulatory news and publishes a report for governance, risk, and compliance review.

**[Read the latest GRC report](https://grcinsight.ricomanifesto.com/)**

## What the Report Shows

- The source event and why it may matter.
- Relevant regulations, frameworks, agencies, and industries.
- Evidence links back to the original article and the dated [SentryDigest](https://github.com/ricomanifesto/SentryDigest) issue.
- Suggested review or follow-up actions.
- The model and source records used to create the report.

The site keeps dated reports and a [publication history](https://grcinsight.ricomanifesto.com/publication-history/) of recorded publication and retention outcomes. Runs that fail before either outcome is recorded do not appear in that history.

## How It Works

1. The Go service accepts report requests, stores report state in DynamoDB, and invokes the Python service.
2. The Python service fetches RSS articles, filters for GRC relevance, and asks the configured OpenRouter model to compose a report.
3. The report workflow retrieves the result and checks its model identity, source issue, citations, and analysis mode.
4. Only a model-backed report with complete source and model records is published. A completed fallback-mode report keeps the last verified report and records a short refusal category. Other generation or provenance failures also keep the last verified report, but exit before adding a history event.
5. A static builder creates the current page, dated archive, evidence manifest, and publication-history page before GitHub Pages deploys them.

New reports separate **Sourced Regulatory Changes** from **Evidence and Decisions**. Regulatory rows require a supported primary publisher, a matching source excerpt, a complete change phrase with exact source casing, and jurisdiction text matching a complete phrase with exact source casing or `Unknown`. The bounded publisher policy and row contract live in `agent/core/report_evidence.py`; source mentions and security news alone cannot establish a regulatory change. Source excerpts are retained in the evidence manifest for publication validation.

**Document effective date** is copied from publisher metadata, never inferred from prose. For selected FederalRegister.gov Rule documents, ingestion reads the public [document API](https://www.federalregister.gov/developers/documentation/api/v1) and retains its `effective_on` field, document identity, API URL, and retrieval timestamp. The prompt, stored report metadata, and evidence manifest share that receipt. Report generation and offline publication validation require the exact recorded date. Text-only sources, unsupported publishers, null dates, and failed lookups display `Unknown`; their source excerpts remain available. Lookups use a fixed HTTPS endpoint, no redirects, and a five-second total budget capped by the remaining invocation deadline. This is the publisher's document-level date, not an interpretation of a particular provision's deadline or legal applicability.

Report contract v6 is written for compliance, risk, audit and control owners. The model writes three bounded narrative fields: one or two executive paragraphs that group findings into themes and lead with the most important development, and for each finding a headline and a short statement of why it matters for control assurance. Validation repairs or drops problems instead of refusing the report:

- Narrative fields become plain single lines: markup, links and line breaks are removed. Missing fields receive application fallbacks, such as a summary built from the finding headlines, and paragraphs cite only sources with a kept finding or regulatory change.
- A finding focus or quotation that differs from its source only in case, quotes, dashes or spacing is restored to the source's spelling. A focus that is not in the excerpt is kept as a plain review label. An evidence origin is taken from where the quotation actually appears.
- A finding whose quotation cannot be found in its source, or that has an unknown control, is dropped, and an unknown priority becomes medium. A regulatory row that fails the primary-source rules below is dropped. Sector mappings and extra fields are ignored.
- The report is refused only when no finding or regulatory change survives. That refusal keeps the field-level diagnostic so the existing retry can correct it.

Grounding rules are advisory and logged as warnings, so they can be tightened against real output. They flag figures (including magnitudes written as words) that are absent from a cited source, along with acronyms, calendar names and capitalized names after a sentence's first word. They also flag CVE identifiers or severity scores, second-person exposure claims, and obligation, penalty, deadline, compliance-duty or regulator-notification language that the cited source does not use. Repeated quotations and style limits are flagged as well. Warnings name the field and rule without echoing the text.

Up to six findings retain one source ID each, an exact article-field excerpt and its `summary` or `content` origin, an exact short identifying focus (at most eight words and 80 characters, shorter than its evidence passage), a dominant control and a review priority. Each headline begins with its focus, followed by a present-tense verb, so the words that distinguish findings come first. Every finding then shows the same fields in the same order: review priority with control area and owner, why it matters, source evidence, evidence to request, decision trigger and reference controls. Owners, evidence requests, triggers and the ISO/IEC 27001:2022 Annex A and NIST CSF 2.0 reference controls are application-owned review aids, not compliance determinations. One scope note replaces per-line inference labels. Findings follow the order the narrative introduces them, then priority. Identical findings share one entry with all their citations; a quotation already in the regulatory table is referenced without being repeated. Sector-only mappings are refused: the contract has no independently evidenced sector-consequence field, so it omits an Industry section instead of supplying unsupported relevance.

Editorial checks are separate from factual grounding. A v6 report has one or two cited narrative paragraphs, an application scope note that states conditional applicability, the fixed finding structure, and distinct brief, evidence and source sections. Each quotation appears once as source evidence. Whole-report recomposition rejects any body that the retained plan does not reproduce exactly. Archived v3, v4 and v5 publications continue to verify with the renderer of their own contract version.

Finding headlines and significance text in a v6 report use the citations on that finding's source-evidence line. CVE validation and reader-surface checks derive this context only when the entire body exactly reproduces the retained plan; every identifier must still occur in the finding's own source inventory. Other report text retains the same-line citation requirement. The generated-site regression covers composition, publication state, rendering, current-report validation and archive validation together. Stored Markdown, source identities and archived reports are not rewritten.

The reader's camelCase leak heuristic preserves spelling inside exact validated v6 source quotations, including publisher and vendor names. Generated prose and metadata remain checked, and all other citation and reader checks still apply to quotations.

Ingestion retains up to two article receipts with their `summary` or `content` origins separately from headline identity. Each receipt contains the original field (`raw_text`, at most 4096 UTF-8 bytes), extraction version 1, and at most 700 characters of extracted text cut at a word boundary. The shared static-text boundary tokenizes raw HTML before decoding text-node entities, so references cannot alter attribute or tag boundaries. It extracts balanced supported HTML, preserves inline word continuity and block spacing, and excludes comments and hidden/non-content subtrees. It refuses oversized input, nested encoding, ambiguous or unknown markup, invisible control/format characters, stylesheets and presentation-dependent class/style/id attributes. This conservative subset can refuse useful publisher content; it does not execute scripts, fetch resources, or infer CSS visibility.

Findings quote the exact extracted text. Publication re-runs extraction from the retained raw field and version and requires identical text, so a normalization label alone cannot attest a quote. The headline passes through the same boundary only for copy detection; its original identity is unchanged. Canonical character-stream comparison rejects whole, partial and repeated headline copies despite typography or word splitting. It is not an editorial relevance score. Raw receipts and the selected origin survive storage, composition, manifest and offline validation; the model sees only extracted eligible passages. Historical origins are never reconstructed from a flattened snippet.

Generation and composition reject empty/category-only plans, missing or ambiguous article origins, title-only evidence, unavailable source IDs, unsupported excerpts/focuses, and arbitrary narrative fields. A regulatory-only report remains valid when its primary-source table passes the regulatory evidence gate. The plan, source snippets, model provenance, and dated Digest identity are retained unchanged in storage and the evidence manifest. Publication requires the exact deterministic rendering and contract v5, including after a rebase. Failed generation or validation retains the last successful report; it cannot manufacture a replacement summary. Exhausted plan-validation retries carry an actionable diagnostic as `report_quality`, distinct from a provider-provenance refusal.

The catalog and renderer in `agent/core/report_plan.py` are versioned: contracts v3 and v4 remain available for exact verification of existing publications, not for new publication. Historical Markdown and manifests are not upgraded. No free-form model narrative, invented IDs, or model-authored date fields are accepted. Exact quote correspondence is a mechanical grounding check, not proof of a source's truth, a complete quotation, an appropriate model-selected priority, or legal applicability. Prompts require preservation of conditions, negation, and uncertainty; editorial evaluation remains necessary.

Retained source positions and original URL identities remain unchanged through storage and publication, including repeated URLs. Markdown destination escaping happens only when rendering links, so it cannot change SentryDigest reporting fragments or shift the plan's source numbers.

The reading view uses compact numbered citations with full accessible titles, keyed by source title and URL so repeated URLs with different titles keep distinct highlights. Source Highlights keeps the complete source links and dated Digest context. Archived Markdown and evidence manifests retain their original bytes; archived HTML is rebuilt with the current reader. Older reports disclose that their regulatory context predates the separate evidence check. Failed-refresh notices derive both displayed timestamps from publication state and keep diagnostics under expandable details.

The reading view adds a review map below the executive summary when a contract v5 plan exactly reproduces the report. It groups the same deduplicated findings by control area and links each to its supporting evidence and decision. Priorities are explicitly inferred review priorities, not measured risk. The map adds no model calls or domain claims. Reports without eligible findings or a matching plan remain readable without a map. The browser preserves the pre-rendered report as one snapshot; reload the page to read a newer publication.

The stable article links shared with SentryDigest and SentryInsight follow SentryDigest's [reporting identity contract](https://github.com/ricomanifesto/SentryDigest/blob/main/contracts/README.md).

## Run It Locally

You need Go 1.24, Python 3.11, and [`uv`](https://docs.astral.sh/uv/). Copy `.env.example` to `.env` and replace the placeholder values before calling model or AWS services.

For model-backed analysis, set:

```bash
export OPENROUTER_API_KEY=...
export LLM_MODEL=openrouter/nvidia/nemotron-3-ultra-550b-a55b:free
```

The prepared `openrouter/google/gemini-4-argon` profile pins `google-vertex/global`
(provider Google), with the default service tier, no fallback, collection denied,
ZDR filtering and text price ceilings of $2/M input and $10/M combined output.
It remains disabled for live execution; only the explicit offline mock path is
available. The free model default is unchanged. ZDR eligibility does not mean
zero retention: Vertex can retain flagged prompts for safety for up to 90 days,
without training. Review effective provider/account policy and obtain separate
data, retention and budget approval before any future live activation. A policy
refusal must stop without relaxing filters or changing account settings.

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

### Optional article relevance pilot

Article analysis can use `typesafe/jev-1.13` through OpenRouter's Decisions API.
The pilot is server-configured and **off by default** in the application. The
production Lambda deploy defaults to `shadow` unless the `GRC_RELEVANCE_MODE`
repository variable says otherwise. In shadow or enabled
mode, each report run copies the bounded relevance log lines (counts, labels,
probabilities and URL hashes, never article text) into its job summary. It uses the existing
`OPENROUTER_API_KEY`; shadow and enabled modes can incur paid inference charges,
even when the report model uses a free route.

- `GRC_RELEVANCE_MODE=off`: the existing generative analysis, with no decision calls.
- `GRC_RELEVANCE_MODE=shadow`: run both analyses and retain the original result.
  Log aggregate decision timing, resolved models, usage and uncertainty counts,
  plus per-article selection records. Shadow does not run the enrichment call,
  so when decisions are usable its records are a conditional counterfactual
  (`selection_basis: conditional_on_enrichment`): what enabled mode would select
  for the same decisions if enrichment succeeded. They do not show completion,
  the output after a failed call, or timing. Records for a full fallback come
  from the legacy result shadow returned (`selection_basis: observed`).
- `GRC_RELEVANCE_MODE=enabled`: apply selection policy `keep-uncertain-v2`.
  - A relevant or irrelevant decision whose selected-label probability meets
    `GRC_RELEVANCE_MIN_PROBABILITY` (default `0.95`) is accepted.
  - When the decisions are complete and valid, every uncertain or
    insufficient-evidence article stays selected, including when every
    article is uncertain.
  - Those articles still go to one generative call, the whole batch when all
    are uncertain, which only enriches report aggregates; its prose selections
    never change article selection. A failed call remains an analysis error
    for the existing caller to handle, and its selections stay unknown.
  - All articles accepted as irrelevant is a valid zero selection, with no
    generative call.
  - Unavailable or invalid decisions fall back to the existing analysis for the
    entire batch.
  - The threshold is a starting value, not a measured guarantee.
  - `keep-uncertain-v1` sent an all-uncertain batch to the existing analysis,
    whose prose selections could drop every article. Version 2 corrects that.

Each enabled or shadow call records one entry per article position, with no
article text. An entry holds:

- the SHA256 of the URL, the raw label, probabilities and confidence;
- the route, its disposition and the reason for any full fallback;
- the model selection, with the entity and risk-category overrides kept separate;
- the effective selections of the report workflow (entity OR risk category OR
  model) and of `/analyze` (entity OR model).

An unknown model selection is never recorded as a drop. Cost unavailable from the
provider stays null. Each call also checks the keep contract against the raw
labels and probabilities, so an uncertain result cannot pass by being relabeled
a full fallback; the count of violating positions is logged as `keep_violations`.

The decision rubric includes concrete security and operational events, control
or audit findings, enforcement and regulatory obligations. Abstract commentary,
promotions and fictional events alone do not qualify; missing or ambiguous
evidence remains uncertain. A named regulation is not required for relevance.

The decision path handles up to 64 articles in batches of at most 12, with at
most three requests in flight. Each request is capped at 24,000 UTF-8 bytes and
each response at 128 KiB. It sees at most 200 title characters and the first 500
characters of content, or summary when content is empty. Its total timeout is
`GRC_RELEVANCE_TIMEOUT_SECONDS` (default four, maximum ten), further bounded by
the caller deadline with one second reserved for fallback. Failed or uncertain
decisions add overhead; the existing fallback is not guaranteed to finish within
the remaining caller budget. No decision requests remain running after fallback.

Article positions preserve identity even when titles repeat. Existing local
entity signals remain positive; the workflow also retains its existing local
risk signals. Counts reflect the effective selection. Relevance probabilities
are not relevance scores, legal applicability, or incident severity. Report
authoring, retained evidence and publication validation stay on their existing
paths, and no source is dropped from report evidence by this pilot.

Use independently reviewed cases to compare quality and speed before activation:

```bash
# Each record has an ArticleInput object and an expected label:
# relevant, irrelevant, or insufficient_evidence. Labels never enter model inputs.
cd agent
uv run python ../scripts/benchmark_relevance.py cases.json
# Explicitly make paid calls, without generating or publishing a report:
uv run python ../scripts/benchmark_relevance.py cases.json --run-paid --repeats 3
```

The first command validates a JSON array of `{"article": {...}, "expected": "relevant"}`
without network calls. The second reports per-batch p50/p95 times, recall, false
positives and missing results for the current model, the actual enabled path
including subset fallback, and a local entity baseline. It alternates paired
execution order with a fresh service and time budget for each measured path, and
reports the fraction of batches and articles requiring fallback. Raw three-label
quality and decision usage come from those same enabled calls; final selections
are binary. Measurements do
not include report generation, workflow risk overrides or publication, and small
replay samples do not establish production p95. Cost unavailable from a
provider/client is reported as null. Failed partial batches can still be billed.
Logs contain aggregate diagnostics, never article bodies or credentials. Live
benchmark results and deployment configuration are required before claiming
production speed or quality improvements.

Paid replays also report an `uncertainty` block: completed pairs, pairs with
errors, the fraction of completed pairs where the enabled path was faster, and
its distribution-free 95% half-width, which is restated in `limits`. Choose
sample sizes before collecting cases with `core/evaluation_design.py` or its
offline CLI:

```bash
# Hoeffding size for a +/-0.10 one-sided bound at 95%, and label budgets:
python3 scripts/evaluation_design.py --epsilon 0.10 --delta 0.05 --sided one \
  --population 71 --counts 20 50 150
```

Outcomes are scaled to [0, 1]. When cases are archived feed issues sampled
without replacement, pass `--population` to apply Serfling's finite-population
factor; the helper recommends a census when the required sample reaches the
pool size, and a census has no sampling error. These bounds pre-register sample
sizes; Wilson or exact intervals remain the reported estimator for observed
rates, especially near zero.

### Repository validation

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

### Static artifact

`scripts/build_static_artifact.py` copies the tracked `site/` tree of one commit, byte for byte, into `builds/<sha256>/artifact/` with a prebuilt `deploy/.vercel/output/` layout whose config is only `{"version": 3}`. It refuses files that differ from that commit, symlinks, private or implementation files, incomplete archive entries, and JSON or XML that does not parse. That commit's own `make check-site` gate must pass on the copy before the build is accepted. `current.json` names the accepted build. A failed, interrupted or concurrent build leaves the accepted build in place.

```bash
make static-artifact REVISION="$(git rev-parse HEAD)" ARTIFACT_STORE=<store> ARTIFACT_RECEIPTS=<receipts-dir>
make test-static-artifact
```

The store and the receipts directory must be outside the repository. Route acceptance for a built store is `scripts/tests/static_artifact_acceptance.py`. Reader acceptance in `scripts/tests/artifact_browser/` uses an existing Playwright 1.62.1 install, since this repository has no Node manifest.

## Deployment and Publishing

- [Lambda deployment guide](docs/README-Lambda-Deployment.md)
- [Static-site contract](site/README.md)
- [DynamoDB articles-table module](configs/terraform/articles-table/README.md)

`.github/workflows/deploy-lambda.yml` runs for changes to Lambda image inputs on `main`, or by manual trigger. It requires preprovisioned ECR repositories and verifies existing Lambda retrieval access without creating repositories or replacing policies. It deploys the Go and Python Lambda images and verifies their image references. Environment updates merge deployment-owned fields with the current map using a fresh RevisionId; secret-bearing JSON goes through a stdin pipe. Reads, updates and verification polls use the same unqualified base function ARN, with responses required to identify that exact ARN and unpublished `$LATEST` version. Uncertain writes stop for inspection and are not automatically replayed. If Go reserved concurrency is zero, API health is explicitly deferred and only the Python non-inference health path is invoked. CI never restores concurrency; operator restoration and a subsequent Go health check remain separate. Normal nonpaused releases retain the Go health smoke test. The manual `scripts/deploy-lambda.sh` remains a bootstrap tool with broader ECR/IAM effects; it is not the normal existing-function release path.

`.github/workflows/lambda-report-generation.yml` runs after a SentryDigest dispatch, daily at 13:00 UTC, or by manual trigger. Every unowned OpenRouter chat route disables provider fallbacks and enforces zero prompt, completion, request, and image price ceilings, including caller-selected aliases or IDs without a `:free` suffix. The documented `:online` modifier and standalone/combined `@preset/` references are refused because they can add separately billed server search/tools outside those token ceilings. Output is bounded to a positive integer of at most 16,000 tokens at the API and transport boundaries. The default route is `openrouter/nvidia/nemotron-3-ultra-550b-a55b:free`; selected paid profiles remain disabled outside synthetic offline rehearsal. This transport fence does not provide caller authentication or an aggregate budget. AWS credentials and `OPENROUTER_API_KEY` are required repository secrets.

Generation admission settles once a successful retrieval identifies the requested report as `completed` or `failed`, even when composition or publication subsequently fails. A refused report records `not-published`, preserves the last-good publication and retains input deduplication; later distinct inputs can proceed. Transport errors, mismatched responses and polling timeouts remain unresolved and reattach the saved handle. Publication success is separate from generation and validation success.

An omitted Go request output cap defaults to 16,000 before any processing record
is created or Python payload is serialized. Explicit invalid caps are rejected at
JSON binding; Python retains its strict positive 16,000-token cap. Manual deployment
preserves configured AWS CLI/profile authentication through an explicit filtered
mode and performs its matching read-only identity preflight before mutations; see
the [deployment guide](docs/README-Lambda-Deployment.md).

`.github/workflows/deploy-site.yml` is the only Pages deployment workflow. It validates the committed `site/` directory, captures light and dark screenshots, and deploys that same artifact.
