# Selected Argon route rehearsal

With the project's locked Python dependencies installed, run:

```sh
python -B scripts/rehearse_selected_model_offline.py --offline-only
```

This exercises the actual report-plan service with one mock POST, a hash-pinned
fictional source pack and a handwritten calibration plan. No feed, article
retrieval, relevance pilot or model inference occurs. The ordinary selected
`google/gemini-4-argon` profile remains disabled. Offline construction requires
the exact mock transport and a synthetic key. Unsupported family variants and
the model's known latest alias are refused before legacy routing.

The fixed policy accepts only text, pins Google AI Studio's standard tier,
disables fallbacks and requests supported parameters, no data collection and ZDR
filtering. It caps applicable token rates at $2/M input and $10/M combined
reasoning/visible output, with zero per-request pricing. Provider eligibility and
effective privacy/retention settings remain unverified. No filter is relaxed on
failure. Current free model defaults and their four zero-price ceilings remain.

The report request uses strict JSON Schema for the current selection object.
The existing parser independently validates exact source quotations, source IDs,
regulatory evidence and executive agenda. The host renderer owns report prose
and citations. Article analysis retains its legacy text contract; strict report
JSON is never imposed on that stage. Paid operations have one transport attempt
and no report repair retry. A future full workflow would still include separate
article-analysis and report-plan operations.

The fixed test proposes an 8,000 combined output allowance and a separate 22,000
conservative input reserve. Ordinary requests retain existing 8k workflow and
16k settings/API output defaults; their input bound derives from the verified
1,048,576 context minus actual output and a 4,096 framing reserve, using complete
messages/schema serialized as UTF-8. This estimate does not attest to the
provider tokenizer and never truncates evidence.

The fixture contains a fictional consultation and supplier-access incident at
reserved `.test` domains. A valid calibration includes a grounded supplier-risk
finding and deliberately abstains from claiming a primary regulatory change.
An all-empty selection is not success. The calibration plan is returned only by
the mock and never sent in a prompt. The script clears inherited credentials and
tracing settings, isolates `.env`/AWS configuration, denies real networking and
exports only bounded hashes, counts and requested-policy metadata. It retains no
raw response and writes no report or publication state. Missing dependencies or
any failed invariant produce a fixed unavailable result. There is no live mode
or activation authority in this command.
