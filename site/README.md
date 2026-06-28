# Site

Static GitHub Pages front end that renders the generated GRC report
(`index.md`) into a navigable, themed reading experience. No build step — the
page loads `index.md` at runtime and renders it in the browser.

## Files

| File | Owns |
|------|------|
| `index.html` | Page shell: header, contents sidebar, mobile section bar, report container, footer. |
| `index.md` | The generated report. Replaced by the report-generation workflow. |
| `static/renderer.js` | **Canonical rendering contract.** Markdown → HTML and URL sanitization. The only place report Markdown is turned into HTML. |
| `static/tags.js` | Compliance term catalog used to highlight frameworks, regulations, risks, controls, and agencies as inline pills. |
| `static/app.js` | Page controller: loads the report, renders it through `renderer`, wraps each section into a card, and wires the reading aids (contents index, section navigation, theme, collapse, copy link). |
| `static/style.css` | Presentation: theme tokens (dark/light), layout, cards, Markdown elements, pills, and reading aids. |

## Rendering contract

`renderer.renderMarkdown(markdown) -> htmlString` is pure (no DOM access), so it
runs identically in the browser and under the Node check. `app.js` consumes it
and never re-implements Markdown rendering; `tags.js` is the single source for
pill categories.

## Checks

```bash
make check-site   # runs both checks below (Python 3.11)
```

- `scripts/check_site_report.py` validates the published artifact: required
  assets are referenced, removed modules stay removed, and `index.md` is a
  valid, public-safe report (title, generated line, sections, no internal
  classification labels).
- `scripts/check_site_renderer.py` runs `renderer.js` and `tags.js` under Node
  and asserts URL sanitization, section normalization, and Markdown rendering —
  including that a paragraph containing bold text renders as a single `<p>`.
