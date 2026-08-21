# FireTest 5 H1C0.R3.01 B3 Post-Slice4 Mutagen Diagnostic

## Verdict

`FIRETEST5_R3_01_B3_BLOCKED_WITH_NEW_FRONTIER_PROVEN`

B3 was a valid public diagnostic run on `agent/codex/r3-01-b3-post-slice4-mutagen` at `08a7028047b0d0b216a576a68cd178085bfec9b0`. The environment matched the B3 baseline: Python 3.11.6, Mutagen 1.48.1 importable, ffprobe unavailable, and native_minimal available.

The run blocked governedly with exactly one terminal event. `SpeakerTruth.safe_to_report_success` remained false.

## Public Run

- task_run_id: `task_run_724cad824d564da2b47433c8ce9b36c8`
- operation_id: `op_9833059d3a504fea8cc0cde45da0ce6f`
- result endpoint: HTTP 200
- status: `blocked`
- reason: `POST_COMPILE_OBSERVATION_MATERIALIZED_BYTES_BUDGET_EXCEEDED`
- phase: `phase_1`
- terminal_event_count: `1`

## Corpus

- candidate entity count: `2286`
- selected corpus/library entities: `2272`
- row-materialized entities: `2230`
- project-like contamination count: `0`
- selected not row-materialized gap: `42`
- source root roles: `{'library_root': 2272, None: 14}`

## Demand And Execution

- logical task count: `24530`
- physical group count: `2230`
- requested canonical key count: `11`
- media_identity ANY_OF: `track_title`, `artist`, `album`, `album_artist`, minimum 1 evidenced claim
- required non-identity claims: none projected for this run
- optional enrichment keys from contract authority: `artwork`, `bitrate`, `channels`, `codec`, `container`, `duration`, `sample_rate`

## Post-Compile Execution

- groups planned: `2230`
- physical probes attempted: `455`
- physical successes: `451`
- physical failures: `4`
- progress ratio: `455/2230` = `20.40%`
- goals satisfied: `2920`
- goals unsatisfied: `21610`
- fanout claim count: `2920`

## Backends

- availability snapshot: Mutagen available, ffprobe unavailable, native_minimal available
- Mutagen attempts: `454`
- Mutagen successes: `451`
- ffprobe physical attempts: `0`
- native_minimal physical attempts: `0`
- fallback backends used: `{}`
- backend errors: `{'FFPROBE_NOT_AVAILABLE': 346, 'MEDIA_BACKEND_UNSUPPORTED_FORMAT': 3}`

## Evidence

- total media EvidenceRecords projected: `3371`
- evidence by backend: `{'mutagen': 3371}`
- evidence by key: `{'codec': 449, 'duration': 451, 'bitrate': 451, 'sample_rate': 451, 'channels': 451, 'metadata': 451, 'artwork': 451, 'track_title': 108, 'artist': 108}`
- track_title: `108`
- artist: `108`
- album: `0`
- album_artist: `0`

## Checkpoint Retention

Slice 4's intended checkpoint retention was not observable in the B3 public run:

- checkpoint refs/counters projected: `false`
- evidence checkpoint payload files under this run: `0`
- run-local payload_refs observed: one entity/projection payload, `6048763` bytes
- checkpoint_count: `0 observed`
- checkpoint_bytes: `0 observed`
- resolver calls: not projected; no checkpoint refs observed
- max EvidenceRecords resolved at once: not projected; no checkpoint refs observed

The public path therefore still governed the observation stage by inline materialized bytes.

## Inline Retention

- inline materialized observation bytes: `7994062` / `8000000`
- final EvidenceSet.records count: not projected
- final checkpoint_refs count: not projected
- final governed record_count: not projected
- post-execution evidence referenced count event: `2681`

## Semantic Materialization

- AttributeObservation count after post-execution materialization: `55750`
- KnowledgeRecord count: not projected before block
- SemanticAssertion count: not projected before block
- SemanticSelfReview evidence count: not projected before block
- SemanticCoverage2: not projected before block
- row semantic validation reached: `false`
- semantic identity evidence ratio: not reached/not projected

## B2 Comparison

| Metric | B2 | B3 |
| --- | ---: | ---: |
| physical groups | 2230 | 2230 |
| logical tasks | 24530 | 24530 |
| probes attempted | 455 | 455 |
| probes succeeded | 451 | 451 |
| probes failed | 4 | 4 |
| Mutagen attempts | 454 | 454 |
| ffprobe attempts | 0 | 0 |
| native_minimal attempts | 0 | 0 |
| EvidenceRecords | 3371 | 3371 |
| inline materialized bytes | 7994062 | 7994062 |
| terminal reason | `POST_COMPILE_OBSERVATION_MATERIALIZED_BYTES_BUDGET_EXCEEDED` | `POST_COMPILE_OBSERVATION_MATERIALIZED_BYTES_BUDGET_EXCEEDED` |
| terminal_event_count | 1 | 1 |
| SpeakerTruth safe | False | False |
| track_title evidence | 108 | 108 |
| artist evidence | 108 | 108 |
| album evidence | 0 | 0 |
| album_artist evidence | 0 | 0 |

Old B2 frontier eliminated: **NO**.

## First Governing Frontier

`POST_COMPILE_OBSERVATION_MATERIALIZED_BYTES_BUDGET_EXCEEDED` remains the governing public frontier. The more specific B3 finding is that Slice 4's ref-backed evidence retention was not effective or not wired into the public runtime path: no checkpoint refs/counters were projected and no evidence checkpoint payloads were persisted for the run.

## Recommendation

Do not run C yet, and do not change the dependency condition. The next gate should diagnose/fix why the public post-compile execution path still accumulates inline observation materialization instead of emitting governed evidence checkpoint receipts under the real corpus path.
