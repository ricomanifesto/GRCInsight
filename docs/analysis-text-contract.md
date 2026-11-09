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

The parser recognizes canonical rows before looking for section keywords. Thus
words such as risk, regulation, framework, industries, score and Title: remain
part of the exact supplied title. Existing compatible decimal scores below 10
remain recognized; `10` is the supported spelling of the upper endpoint.

A canonical row credits an article only when its number names a supplied
article, its title equals that article's title exactly, and its score is valid.
A row that fails any of these checks credits no article: an unknown or
zero-padded number, a title that belongs to another article, a mismatched title,
or an invalid or nonfinite score. Such rows are skipped and counted; the
remaining valid rows are kept. A repeated identity counts once and its repeats
are skipped. The result reports `analysis_rows: {"accepted": n, "skipped": k}`,
and skipped rows are logged by count, never by content.

When canonical rows were attempted and none is usable, the analysis is refused
with "no usable article analysis rows". It never falls through to the legacy
fallback that selects every supplied article, so an unusable answer cannot
become an apparently successful analysis. A refused analysis follows the
existing failure path: the report run retains the last published report.

The existing analysis result shape is preserved, including its legacy fixed
relevance score of 7.0 and summary fields. This correction does not migrate to
JSON analysis, change the report-plan schema, or change model routing, limits,
privacy, grounding or retry policy.

Legacy free-form handling remains for responses with no canonical row. It may
recognize inline reasons or fall back to all original articles when it recognizes
no row. Neither behavior proves the
closed fictional test's required source-bound analysis. That observer still
rejects inline reasons, bullets, Markdown, split rows, missing supplier control
and unsupported identities without normalization. It remains stricter than the
legacy parser outside the advertised canonical language. Duplicate supplied
titles and title-based downstream selection retain their existing limitations;
this is not a general analysis parser redesign.

`tests/test_analysis_text_contract.py` covers the generated prompt and parser.
The separate nonpublishing test executor additionally compares the real parser
with its strict observer and exercises the two-stage host flow. Passing synthetic
tests does not identify the discarded answer or exact refusal in an earlier run.
