# Report and article history

Report outcomes and analyzed source articles are kept as durable, queryable
history in the existing DynamoDB tables (`grcinsight-reports`,
`grcinsight-articles`). This page describes how history is written, read and
exported, and what each state means.

## Lifecycle

1. The Go service admits a generation job: it creates the report row with
   `status = processing` and a random `job_id`, refusing to overwrite an
   existing report id.
2. The Python workflow runs (asynchronous Lambda invocation in production;
   synchronous generation calls the same writer through
   `POST /api/v1/workflow/reports/{report_id}/run`).
3. The report writer (`agent/history/writeback.py`) stores evidence first, then
   completes the row exactly once.

Only the report writer completes a report. Go records failures it observes
(for example a failed invocation) and only while the row is still open.
Every report update is conditional on
`status IN (pending, processing) AND attribute_not_exists(outcome_sha256)`, so
a final outcome is never rewritten by a retry, a duplicate delivery, a late
worker or the Go service.

### Completion identity

Completion is bound to the admitted job (`job_id` on the row; rows created
before job ids exist bind to the report id). Lambda request ids are recorded as
`completion_invocation_id` for diagnosis only, because retries and duplicate
deliveries are not guaranteed to reuse them. A request for a different job is
refused before anything is written.

### Decisions

| Decision | Meaning | Lambda/HTTP status |
|---|---|---|
| `committed` | This job's outcome is now final | 200 |
| `reused` | The identical outcome was already final (duplicate delivery) | 200 |
| `stale_completion_refused` | Same job, different result; the first outcome stays | 409 |
| `foreign_completion_refused` | Another job owns this report | 409 |
| `already_terminal_refused` | The row was already terminal (cancelled or legacy) | 409 |
| `report_missing` | No such report row | 409 |
| `evidence_failure_recorded` | Evidence could not be stored or verified; the report was finalized as `failed` with a reason | 500 |
| `integrity_failure` | A stored outcome no longer matches its digest | 500 |

`status` keeps its existing meaning (`completed` or `failed`) for publication.
`terminal_outcome` adds the distinction publication already enforces:
`model_completed`, `refused_fallback` or `failed`. A fallback refusal is never
treated as intelligence.

If the store itself is unreachable, the row stays `processing`; publication
waits and keeps the last accepted report, and export reports it as `incomplete`.

## Stored items

- **Report row** (existing item, new fields on completion): `job_id`,
  `terminal_outcome`, `terminal_reason`, `completion_run_id`,
  `completion_invocation_id`, `article_revision_ids`, `appearance_set_sha256`,
  `completed_at` and `outcome_sha256`, a SHA-256 over the canonical JSON of the
  outcome fields.
- **Article revision** (`record_kind = article_revision`): keyed
  `arev#<url key>#<content digest>`, created only if absent. It holds the
  retained title, summary and feed content (up to 50,000 characters, with the
  captured length and digest when truncated), the evidence kind (`full_text`
  means the complete feed-item content as captured; `excerpt`;
  `metadata_only`), `published_at` only when the feed supplied a date, and the
  first capture time, job and report. Changed content is a new revision; the
  old one is never rewritten.
- **Report appearance** (`record_kind = report_article_appearance`): keyed by
  report, appearance-set digest and position. It links a report to a revision
  with the generated classification. Only the set the report row binds counts.

Revisions carry no `report_id`, so they do not enter the `by-report-id` index;
appearances do.

## Reading

`GET /api/v1/reports/{id}/articles?page=&per_page=` (at most 100 per page)
returns legacy rows as stored and, for history reports, only the bound
appearances in position order. Each history article's text is read from its
revision with one strongly consistent `GetItem` per article on the page and
returned only if the revision's digest verifies. Each article carries
`evidence_status`:

| `evidence_status` | Meaning |
|---|---|
| `intact` | Text served from a verified revision |
| `corrupt` | The revision does not match its digest; no text is served |
| `missing` | The referenced revision is absent |
| `unbound` | The report has no final outcome yet |
| `legacy` | A row written before history; returned as stored |

`published_known` is `false` when the feed gave no date; `published` is then
the zero time rather than an invented one. A report listing reads at most
1,000 article rows.

## Export

```bash
cd agent
python -m history export --stream reports  --table grcinsight-reports  --limit 5
python -m history export --stream articles --table grcinsight-articles --limit 25 \
  [--cursor <next_cursor>] [--updated-since 2026-11-01T00:00:00Z] [--include-text]
```

Each call issues one bounded `Scan` page (1–200 items) and prints a page of
`grcinsight.intelligence-export.v1` records with an opaque `next_cursor`.
Records carry a stable `record_id`, a `record_revision` and a `record_digest`;
replaying the same data yields identical records. Integrity is re-verified on
every read (`intact`, `corrupt` or `unverifiable_legacy`), and rows written
before history are exported with `provenance_class = legacy_unknown` rather
than reconstructed. Report content appears only for verified model reports and
legacy model reports labelled `legacy_unverified`. Export never asserts that a
report was published.

`--updated-since` is a filter applied to scanned items, not an index query: it
reduces output, not read cost. `grcinsight-reports` uses provisioned capacity
(1 RCU at the time of writing), so keep report pages small and avoid running
exports while a report generation is being polled.

A synthetic, deterministic fixture of every state (duplicates, a changed
revision, interrupted completion, refusals, fallback, failure, corruption and
legacy rows) is produced by:

```bash
python -m history fixture --out /tmp/grc-history-fixture
```

## Verifying a deployment

After a report completes:

1. `GET /api/v1/reports/{id}` shows `status`, `terminal_outcome` and `job_id`.
2. `GET /api/v1/reports/{id}/articles` lists articles with
   `evidence_status = intact`.
3. An export page containing the report shows `integrity.status = intact`
   and `conclusion_status = verified` only for a model report.
