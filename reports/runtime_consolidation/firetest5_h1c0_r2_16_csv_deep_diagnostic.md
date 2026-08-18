# H1C0.R2.16 CSV Deep Diagnostic — Before Patch

Root cause status: not_yet_proven.

The observed frontier is `MUSIC_INVENTORY_CSV_STREAMING_STALLED`, but the code and R2.15 traces show ambiguous cardinality domains. `rows_expected` and `rows_rendered` are reused for input entities, projected entities, row loop progress, and post-render/persist summaries.

Initial findings:

- Renderer rebuilds `selected_entities` from `graph_payload` and perception-selected ids.
- Row/cell loop builds the full `rows` list in memory before `csv.writer.writerows(rows)`.
- Current checkpoints expose row/cell progress but not stable row-model identity, order digest, or per-batch elapsed cost.
- R2.15 diagnostic reached music inventory persist; R2.15 final blocked earlier in CSV cell render. Equivalence is not proven because set/order/row-model digests do not exist.
- Payload-ref amplification is physically plausible and requires direct ref byte/hash accounting.

Patch plan: instrument and correct cardinality domains first; then classify cost/stall accurately; then address bounded metrics and payload-ref amplification within the same boundary if evidence supports it.
