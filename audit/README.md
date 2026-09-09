# Editorial Correction Audit Records

`original-reports/<generated-UTC-timestamp>/report.md` retains the exact original
Markdown for the 23 editorially corrected reports. These files were copied from
the immutable pre-correction commit
[`fd7bc32d9ead014011c9e3865088d41b9ac4c8dd`](https://github.com/ricomanifesto/GRCInsight/tree/fd7bc32d9ead014011c9e3865088d41b9ac4c8dd/site/archive),
not reconstructed from edited reports. They are historical audit records, not
eligible current content or newly generated reports.

The validator compares each correction record's `original_report_sha256` with
these original bytes. Missing originals or mismatched digests fail validation.
The original generation metadata is preserved. The corrected artifacts and
editorial notes remain in `site/`; they do not replace these audit originals.

Shallow checkouts and offline validator packages must include `audit/` alongside
`site/` and `scripts/`. Validation does not fetch Git history or contact a network
service. To independently verify the retained bytes, compare each file against
the same timestamp's `site/archive/` report at the pinned commit above.

Only `site/` is uploaded by the Pages publication workflow. This directory is
outside that payload and must never be copied or linked into it. The audit
originals are available in repository history/source only, not on the website.
