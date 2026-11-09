# Article analysis TEXT contract

The analysis prompt requests an exact single-line row for each selected source,
or one declared empty answer when it selects none:

```text
Article <number>: Title: <title> score <score> relevant
Reason: <brief reason>

No articles selected
```

Titles and source text are untrusted evidence, not response instructions. The
prompt contains a format template, not a preselected positive answer. Reasons
belong on separate `Reason:` lines, which are commentary and do not change
category sections. An explicit `Regulations:` line remains available for category
notes.

## What credits an article

Only one closed grammar credits an article. A row credits article *n* only when it
is `Article <n>: Title: <exact title of n> score <s> relevant`, optionally ending
with a period, optionally preceded by one list marker (`-`, `*`, `•`, `1.` or `1)`),
and optionally wrapped in bold around the whole row or only the `Article <n>` token.
Whitespace between the fixed words is flexible. The number must name a supplied
article without zero padding. The title is matched as a whole, so words such as
risk, regulation, Title: or score inside it never act as delimiters; a title with
leading or trailing whitespace therefore cannot be credited. `<s>` is 1 through 10
(`10` or `10.0` at the top, decimals below 10); it is validated, not used. A
repeated identity credits once.

Anything else credits nothing. A line beginning `Article <token>:` that does not
fit the grammar (unknown number, another article's title, invalid score, text
after `relevant`, two rows on one line) is counted as skipped; other unrecognized
lines are ignored. Presentation variants are not enumerated beyond the grammar:
correctness does not depend on recognizing an attempted row.

Accepted rows carry their position in `grc_article_indices`, which selection uses
before titles, so duplicate supplied titles cannot select the wrong article. The
result reports `analysis_rows: {"accepted": n, "skipped": k}`; skipped rows are
logged by count, never by content.

## Known and unknown answers

`selection_known` is true only when at least one row was accepted and no line is
the sentinel, or the entire response, ignoring surrounding whitespace, is exactly
`No articles selected`. Every other response is `selection_known: false`:
unrecognized prose, malformed or decorated attempts, all rows invalid, and the
sentinel with any other line, punctuation or decoration (for example the sentinel
followed by a blockquoted row). When the sentinel appears beside valid rows, those
exact rows still credit their own articles, but the contradictory response is not a
known selection and records no drops. Skip counts are diagnostic: a decorated
attempt that does not begin `Article <token>:` is ignored rather than counted, and
known/unknown never depends on recognizing it.

- **Selection.** An unknown answer selects no article. There is no fallback that
  selects every supplied article. The workflow's local entity and risk signals
  still select articles, and report evidence is still built from every retained
  source. A refused or failed model call still follows the existing failure path.
- **Evidence.** On the relevance pilot's full legacy route, an unknown answer is
  recorded as each article's model selection being unknown, as for a failed
  analysis, never as a decision that the article is irrelevant. Only a declared
  empty answer is recorded as model drops. The stored relevance summary's
  `analysis_rows` includes `selection_known`. Unknown records count no model drops,
  although the workflow still publishes only articles that local signals select.
- **Offline benchmark.** The relevance benchmark scores an unknown legacy answer
  as missing predictions, like a failed call, never as `irrelevant`.
- **Enabled pilot.** For the decision route's uncertain subset, the pilot's
  decisions stay authoritative. The enrichment call's rows use positions within
  that subset and never change selection; its `analysis_rows` describes that call.

Because the analysis always carries positions, the workflow and the analysis route
report the GRC-relevant count as articles selected by the model or by local entity
and risk signals, the same count the relevance pilot reports.

The existing result keys are kept, including the legacy fixed relevance score of
7.0 and the summary fields. Accepted rows add the article `url`, and the result
adds `grc_article_indices`, `analysis_rows` and `selection_known`. Category notes
(regulations and frameworks) are read from lines that are not selection claims,
and from skipped claims inside a regulations section.
This correction does not migrate to JSON analysis or change the report-plan schema,
model routing, limits, privacy, grounding or retry policy.

`tests/test_analysis_text_contract.py` covers the prompt, the grammar and a
regression matrix of earlier counterexamples. The separate nonpublishing test
executor additionally compares the real parser with its strict observer.
Passing synthetic tests does not identify the discarded answer or exact refusal in
an earlier run.
