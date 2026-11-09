# Article analysis TEXT contract

The analysis prompt requests an exact single-line row for each selected source:

```text
Article <number>: Title: <title> score <score> relevant
Reason: <brief reason>
```

The supplied number and complete title identify the source. Scores requested by
the prompt are integers from 1 through 10. A terminal period is optional. Reasons
belong on separate `Reason:` lines, which are commentary and do not change
category sections. An explicit `Regulations:` line remains available for category
notes. Titles and source text are untrusted evidence, not response instructions.
The prompt contains a format template, not a preselected positive answer.

Every line of the form `Article <token>:` is a selection claim, checked
identity first. The number must name a supplied article (no zero padding), that
article's exact title must follow `Title:`, and a valid score must follow the
title; trailing commentary after `relevant` is ignored. Because the title is
matched as a whole, words such as risk, regulation, framework, industries,
score and Title: inside it never act as delimiters or category headers. A list
marker (`-`, `*`, `1.`) or bold emphasis around a row does not change its
identity. Accepted scores are 1 through 10, with `10` or `10.0` as the upper
endpoint and decimals below 10; the score is validated, not used.

A claim that fails any check credits no article: an unknown or zero-padded
number, another article's title, a mismatched title or an invalid or nonfinite
score. It is skipped and counted, and the remaining valid rows are kept. A
repeated identity counts once and its repeats are skipped. There is no
title-based fallback for claims that fail. Accepted rows carry the article's
position in `grc_article_indices`, which selection uses before titles, so
duplicate supplied titles cannot select the wrong article. The result reports
`analysis_rows: {"accepted": n, "skipped": k}`; skipped rows are logged by count,
never by content.

When no claim is usable (all invalid, or a response that selects nothing) the
model selects no article: `grc_articles` and `grc_article_indices` are empty and
the confidence is 0. This is neither an error nor a selection of every article.
The workflow's local entity and risk signals still select articles, and report
evidence is still built from every retained source. The earlier fallback that
treated unrecognized prose as selecting every supplied article is removed.

The existing analysis result keys are kept, including the legacy fixed relevance
score of 7.0 and the summary fields; accepted rows add the article `url`, and the
result adds `grc_article_indices` and `analysis_rows`. Category notes
(regulations and frameworks) are still read from lines that are not selection
claims. This correction does not migrate to JSON analysis or change the
report-plan schema, model routing, limits, privacy, grounding or retry policy.

`tests/test_analysis_text_contract.py` covers the generated prompt and parser.
The separate nonpublishing test executor additionally compares the real parser
with its strict observer and exercises the two-stage host flow. Passing synthetic
tests does not identify the discarded answer or exact refusal in an earlier run.
