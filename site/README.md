# GRCInsight Static Site

`site/` is the exact GitHub Pages artifact. The current report and every archive page are rendered before deployment, so the evidence remains readable when JavaScript is unavailable. Browser JavaScript adds the contents index, human-readable date refresh, and an optional dark theme.

Generated report files should be changed through the publication scripts, not edited by hand.

## Files

| Path | Purpose |
|---|---|
| `index.md` | Current generated report. |
| `index.html` | Pre-rendered current report and page shell. |
| `evidence-manifest.json` | Source titles and URLs, CVE coverage, model identity, and the dated SentryDigest issue for the current report. |
| `archive/` | Dated Markdown, evidence manifests, and pre-rendered report pages. |
| `publication-state.json` | Latest publish or retention outcome. |
| `publication-history.json` | Newest-first journal of up to 30 terminal outcomes. |
| `publication-history/` | Human-readable version of that journal. |
| `static/renderer.js` | Shared Markdown-to-report-card renderer and URL sanitizer. |
| `static/app.js` | Optional navigation, date, and theme enhancements. |
| `static/style.css` | Editorial report layout, responsive tables, and print styles. |

## Publication Path

`scripts/compose_site_report.py` accepts a completed stored report and creates `index.md` plus `evidence-manifest.json`. It refuses fallback reports, mismatched source or model records, and citations that were not in the analyzed article set.

`scripts/build_site.py --archive-current` snapshots the current Markdown and evidence manifest, then rebuilds the current page, archive, publication history, and related navigation. `scripts/check_site_report.py` validates the separately maintained sitemap.

`static/renderer.js` is used by both the build and the browser. The controller in `static/app.js` does not contain a second Markdown implementation.

## Checks

```bash
make check-site
```

This runs three checks:

- `scripts/build_site.py --check` fails when committed HTML differs from its Markdown and JSON inputs.
- `scripts/check_site_report.py` checks model and source provenance, citations, archives, publication state, pre-rendering, prose rules, public identity, and interactions.
- `scripts/check_site_renderer.py` runs the shared renderer under Node and checks URL sanitization, report sections, provenance, and Markdown edge cases.

The Pages workflow runs the same gate, captures light and dark screenshots, uploads them for review, and deploys the validated `site/` directory.
