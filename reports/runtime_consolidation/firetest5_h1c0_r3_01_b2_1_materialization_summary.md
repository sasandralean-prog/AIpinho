# FireTest 5 H1C0.R3.01 B2.1 Materialization Diagnostic

## Verdict

`R3_01_B2_1_MATERIALIZATION_ROOT_CAUSE_PROVEN`

Run B2 blocked because the post-compile observation stage retained too much governed evidence/result structure inline before downstream semantic validation:

`POST_COMPILE_OBSERVATION_MATERIALIZED_BYTES_BUDGET_EXCEEDED`

The dominant measured contributor is not large raw metadata values. The dominant contributor is structural duplication and fixed per-record overhead, especially repeated `entity_ref` structures in `EvidenceRecord` plus repeated `EvidenceSet.entity_refs`.

## Evidence Source

- Run: `task_run_a757d3160e6d4b3d92c3410936abc0d1`
- Operation: `op_8e751117b72d40529b050dc3e0f5e2fb`
- B2 report commit: `993189f9d991cdba5f38fd13d3ea5ecd3305ec28`
- Base SHA: `f3fec1c74a83a5b0bae08152756c98ae55d64f67`
- Public result: `blocked`
- Terminal event count: 1
- SpeakerTruth safe_to_report_success: false

## B2 Materialization Frontier

- Physical groups planned: 2,230
- Physical probes: 455
- Accepted successful results: 451
- EvidenceRecords accepted: 3,371
- Materialized observation bytes: 7,994,062 / 8,000,000
- Terminal reason: `POST_COMPILE_OBSERVATION_MATERIALIZED_BYTES_BUDGET_EXCEEDED`

## Byte Attribution Sample

Bounded service-equivalent sample:

- Same corpus entity payload from B2
- First 120 corpus media entities sampled
- Real Mutagen backend
- B2 demand model
- Runtime compact `_execution_entity_ref` shape
- Records sampled: 902

Average serialized bytes per record:

| Key | Records | Avg bytes | Median | P95 | Max |
|---|---:|---:|---:|---:|---:|
| metadata | 120 | 1663.86 | 1656 | 1778 | 1875 |
| track_title | 31 | 1844.94 | 1839 | 1959 | 2047 |
| artist | 31 | 1817.35 | 1804 | 1882 | 1936 |
| codec | 120 | 1600.80 | 1589 | 1689 | 1821 |
| duration | 120 | 1605.71 | 1594 | 1694 | 1825 |
| bitrate | 120 | 1597.09 | 1588.5 | 1684 | 1816 |
| sample_rate | 120 | 1607.80 | 1596 | 1696 | 1828 |
| channels | 120 | 1596.80 | 1585 | 1685 | 1817 |
| artwork | 120 | 1603.12 | 1596 | 1689 | 1821 |

`album`, `album_artist`, and `container` were not observed in the B2 accepted evidence counts.

## Component Attribution

Representative averages:

- `metadata.normalized_value`: 65.06 bytes
- `metadata.entity_ref`: 468.90 bytes
- `metadata.provenance`: 227.95 bytes
- `track_title.normalized_value`: 21.71 bytes
- `track_title.entity_ref`: 463.19 bytes
- `track_title.provenance`: 460.94 bytes
- `artist.normalized_value`: 15.48 bytes
- `artist.entity_ref`: 463.19 bytes
- `artist.provenance`: 449.58 bytes

EvidenceSet-level duplication:

- Average EvidenceSet bytes: 16,313.10
- Average sum of record bytes: 12,221.27
- Average EvidenceSet overhead minus records: 4,091.82
- Average `EvidenceSet.entity_refs` bytes: 3,536.65

Classification: `EVIDENCESET_STRUCTURAL_DUPLICATION_IMPACT = MATERIAL`.

## Generic Metadata

`metadata` is not requested by the media inventory artifact contract. It is an internal/descriptive capability evidence key.

Generic metadata inline overretention is proven, but it is not the dominant byte root cause in this corpus:

- B2 retained 451 `metadata` EvidenceRecords.
- Sample `metadata.normalized_value` averaged only 65.06 bytes.
- Identity claim records preserve raw tag provenance through `raw_tag_key`, `raw_tag_value_repr`, `raw_result_id`, backend and semantic mapper fields.

`GENERIC_METADATA_REQUIRED_FOR_CLAIM_TRUTH = DISPROVEN` for the representative identity-bearing sample.

## Capacity Models

Observed B2 current representation estimate:

- 7,994,062 bytes / 455 attempted groups = 17,569.37 bytes per attempted group
- Full 2,230 groups at same density = about 39.18 MB

Ratio model using sampled record sizes:

- Current inline representation: about 39.18 MB full-corpus estimate
- Without inline generic metadata: about 33.81 MB full-corpus estimate
- Ref-backed metadata value only: about 39.36 MB full-corpus estimate

Conclusion: contract-aware filtering of generic metadata is correct, but insufficient alone. Full-corpus inline retention under the current representation is unlikely to fit the 8 MB guardrail.

## Telemetry Findings

Preacceptance physical telemetry loss is proven:

- B2 `physical_probe_count = 455`
- B2 `attempted_backends.mutagen = 454`
- Code path executes a group, measures bytes, then replaces the over-budget result with `_budget_block_result()`.
- `_budget_block_result()` carries an empty `EvidenceSet` and no `observer_payload`.
- `_backend_telemetry()` only counts backend attempts from `result.provenance.observer_payload`.

Required split:

- physical probes attempted
- physical backend attempts
- physical backend successes
- evidence records produced
- evidence records accepted
- evidence records rejected by budget
- accepted results
- policy-rejected results

File success semantics are currently acceptance-oriented: the budget-rejected final physical probe is counted as `files_failed` even if the underlying backend execution may have succeeded and only retention policy rejected it.

Public summary authority break is proven: physical execution telemetry exists in result/event metadata, but the top-level task summary still reports `media_metadata_capability.status = not_configured` because it reads artifact/perception materialization sources that are not reached after the materialization block.

## Root-Cause Gates

- MATERIALIZATION_BYTE_DOMINANT_COMPONENT: PROVEN
- GENERIC_METADATA_INLINE_OVERRETENTION: PROVEN
- GENERIC_METADATA_REQUIRED_FOR_CLAIM_TRUTH: DISPROVEN
- EVIDENCESET_STRUCTURAL_DUPLICATION_IMPACT: MATERIAL
- FULL_CORPUS_INLINE_8MB_FEASIBILITY: UNLIKELY
- PREACCEPTANCE_TELEMETRY_LOSS: PROVEN
- PUBLIC_SUMMARY_AUTHORITY_BREAK: PROVEN
- ROOT_CAUSE_STATUS: PROVEN

## Recommendation

Do not increase the 8 MB budget as the primary correction.

Recommended path:

1. Compact `EvidenceSet` structure so repeated entity refs are stored once and records use a stable entity reference.
2. Add checkpointed/ref-backed post-compile evidence/result retention so downstream validation consumes governed evidence without holding every complete `ObservationExecutionResult` inline.
3. Apply contract/demand-aware inline filtering so unrequested generic metadata is audit/ref-backed, not inline claim evidence.
4. Preserve raw support through an immutable raw support object/ref where needed for audit and replay.
5. Project physical telemetry separately for produced, accepted and rejected evidence.
