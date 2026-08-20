# H1C0.R3.01.B1 Capacity Diagnostic Recommendation

Verdict: `R3_01_B1_ROOT_CAUSE_PROVEN`

## Proven Boundaries

- Blocking frontier: `POST_COMPILE_OBSERVATION_TOTAL_BUDGET_EXCEEDED`.
- Run B workload: `15610` logical tasks, `2230` physical groups, `336` physical probes attempted.
- Correct dedup ratio: `15610 / 2230 = 7.0` logical tasks per planned physical group.
- Attempted subset claim satisfaction: `2339 / 2352 = 0.9945`.
- Total budget coherence: `120000 / 2230 = 53.81 ms/probe` required; descriptor advertises `100 ms` per probe, or `223000 ms` sequential for the planned groups.
- Materialization pressure: `7335302` bytes after `336` probes, `0.917` of the 8 MB budget at `0.151` of groups.

## Seven Requested Keys

The seven executable media metadata keys are derived from current code/contract, not from bounded event projection:

`artwork, bitrate, channels, codec, container, duration, sample_rate`

Reason: the contract declares these seven technical media columns; `metadata` is in `MEDIA_METADATA_CANONICAL_KEYS` but is not a contract schema column; media identity keys are in `MEDIA_IDENTITY_CANONICAL_KEYS` and are not part of the seven grouped execution tasks observed in Run B.

## Backend Path Finding

The current backend policy is global-completeness-aware:

`Mutagen -> ffprobe -> native_minimal`

It stops only when all `MEDIA_METADATA_CANONICAL_KEYS` technical keys are observed, or when partial evidence is disallowed. In a bounded 40-file service-equivalent sample, every file attempted exactly `('mutagen', 'ffprobe', 'native_minimal')`. Mutagen produced evidence for `39/40` files; ffprobe was unavailable for `40/40`; native_minimal still ran for `40/40`.

This proves backend over-acquisition relative to a requested-claim-aware execution model.

## Identity Evidence

The bounded sample proves Mutagen can produce governed identity evidence in this environment/corpus subset:

- `track_title`: `7`
- `artist`: `7`
- `album`: `0`
- `album_artist`: `0`

Public Run B did not project per-key evidence counts, so public identity acquisition remains hidden by telemetry.

## Recommendation

Do not run C yet as a dependency comparison and do not apply a blanket budget increase.

Recommended next implementation order:

1. Make post-compile backend stopping requested-claim-aware while preserving evidence/provenance requirements.
2. Cache or pre-resolve unavailable backends per stage so ffprobe absence is not rediscovered for every physical group.
3. Add bounded backend/key telemetry projection from physical results: attempted/successful/fallback backends, backend errors, evidence counts by canonical key and backend.
4. Add checkpointed/ref-backed observation evidence materialization so retained audit evidence does not require full inline materialization before final validation.
5. Only after B/C telemetry and materialization are bounded, consider bounded parallel physical execution.

Simple budget increase is not recommended as the first fix: extrapolated materialized bytes are approximately `48683701` bytes for the full planned group count, far above the current 8 MB materialized observation budget.
