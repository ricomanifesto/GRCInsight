# Editorial Correction Audit Records

`original-reports/<generated-UTC-timestamp>/` retains the exact original
`report.md` and `evidence-manifest.json` for the 23 editorially corrected reports.
These files were copied from
the immutable pre-correction commit
[`fd7bc32d9ead014011c9e3865088d41b9ac4c8dd`](https://github.com/ricomanifesto/GRCInsight/tree/fd7bc32d9ead014011c9e3865088d41b9ac4c8dd/site/archive),
not reconstructed from edited reports. They are historical audit records, not
eligible current content or newly generated reports.

The validator binds both original digests to these bytes, then derives the only
permitted corrected artifacts. It removes whole tagged source records while
preserving retained records, ordering, and metadata. In Markdown it removes
complete promotional paragraphs, list items, and table rows, then inserts the
fixed editorial note without changing any retained bytes. Ambiguous block shapes
fail closed. Three untagged narrative exclusions are bound to the exact snapshot,
original-report digest, and whole-unit digest; a generic phrase or source URL is
not permission to delete prose. Source and narrative removal counts must match
the derived transformation, even if all declared hashes have been updated.

The corrected artifacts and editorial notes remain in `site/`; they do not
replace these audit originals or represent another model run.

Shallow checkouts and offline validator packages must include `audit/` alongside
`site/`, `scripts/`, and the shared `agent/core/content_policy.py` module.
Validation uses only the Python standard library, does not fetch Git history,
and does not contact a network service. To independently verify the retained
bytes, compare each file against the same timestamp's `site/archive/` artifact
at the pinned commit above.

Only `site/` is uploaded by the Pages publication workflow. This directory is
outside that payload and must never be copied or linked into it. The audit
originals are available in repository history/source only, not on the website.
