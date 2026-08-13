# Site

Static GitHub Pages front end for the generated GRC report (`index.md`). The
publication workflow pre-renders the current report and its archive before
deployment; browser JavaScript progressively adds navigation, official-reference
pills, collapse controls, copy feedback, and theme behavior.

## Files

| File | Owns |
|------|------|
| `index.html` | Page shell plus the pre-rendered current report. Rebuilt whenever `index.md` changes. |
| `index.md` | The generated report. Replaced by the report-generation workflow. |
| `archive/` | Workflow-maintained dated Markdown snapshots and pre-rendered archive pages. History begins August 13, 2026. |
| `static/renderer.js` | **Canonical rendering contract.** Markdown → complete report-card HTML and URL sanitization. Used in Node and the browser. |
| `static/tags.js` | Unicode-aware catalog for framework, regulation, and agency pills. Every pill has a curated official URL. |
| `static/app.js` | Progressive page controller: refreshes from `index.md` and wires contents, theme, collapse, copy confirmation, and documented shortcuts. |
| `static/style.css` | Presentation: theme tokens (dark/light), layout, cards, Markdown elements, pills, and reading aids. |

## Rendering contract

`renderer.renderReportDocument(markdown) -> htmlString` is pure (no DOM access),
so the build and browser paths produce identical provenance and section cards.
`app.js` never re-implements Markdown rendering; `tags.js` is the single source
for linked pill categories, aliases, and authoritative URLs. The controller does
not replace terms inside existing links or code blocks.

`scripts/compose_site_report.py` accepts a completed stored report response and
creates deterministic public Markdown from report-owned metadata. It fails on
fallback mode or source/model mismatch. `scripts/build_site.py --archive-current`
then snapshots that Markdown and rebuilds current/archive HTML.

## Checks

```bash
make check-site   # runs both checks below (Python 3.11)
```

- `scripts/build_site.py --check` proves committed current/archive HTML matches
  the Markdown inputs.
- `scripts/check_site_report.py` validates provenance, archive consistency,
  model-backed mode, source links, citations, cross-references, prose hygiene,
  separators, pre-rendering, public identity, and interaction contracts.
- `scripts/check_site_renderer.py` runs `renderer.js` and `tags.js` under Node
  and asserts URL sanitization, complete report rendering, section normalization,
  linked-only pills, and Markdown regressions.

The Pages deployment captures dark and light top-of-fold screenshots and uploads
them as a workflow artifact before publishing the same validated `site/` tree.
