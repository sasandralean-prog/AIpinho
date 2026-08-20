# FireTest 5 H1C0.R3.01 B2 Post-Slice-3 Mutagen Validation

## Verdict

`FIRETEST5_R3_01_B2_BLOCKED_WITH_NEW_FRONTIER_PROVEN`

Run B2 validated the Slice 3 acquisition change under the natural Mutagen-present / ffprobe-absent environment, then blocked at a new first frontier:

`POST_COMPILE_OBSERVATION_MATERIALIZED_BYTES_BUDGET_EXCEEDED`

FireTest 5 remains `NOT_READY`. R3.01 remains open.

## Baseline

- Base SHA: `f3fec1c74a83a5b0bae08152756c98ae55d64f67`
- Branch: `agent/codex/r3-01-b2-post-slice3-mutagen`
- Public run: `task_run_a757d3160e6d4b3d92c3410936abc0d1`
- Operation: `op_8e751117b72d40529b050dc3e0f5e2fb`
- Python: `C:\Program Files\Python311\python.exe`, 3.11.6
- Mutagen: available, 1.48.1, user-site package
- ffprobe: unavailable
- native_minimal: available, technical metadata only

## Public Result

- Status: `blocked`
- Reason: `POST_COMPILE_OBSERVATION_MATERIALIZED_BYTES_BUDGET_EXCEEDED`
- Phase/frontier: `artifact_render` / `POST_COMPILE_OBSERVATION_EXECUTION`
- Terminal event count: 1
- SpeakerTruth safe_to_report_success: false

## Typed Demand

Slice 3 made media identity a first-class observation demand:

- Logical tasks: 24,530
- Physical groups: 2,230
- Logical tasks per group: 11
- Requested keys: artwork, bitrate, channels, codec, container, duration, sample_rate, track_title, artist, album, album_artist
- Media identity group: ANY_OF(track_title, artist, album, album_artist), minimum 1 evidenced claim
- Required non-identity claims observed in B2 contract telemetry: none
- Optional enrichment claims: artwork, bitrate, channels, codec, container, duration, sample_rate

## Post-Compile Execution

- Files planned: 2,230
- Physical probes attempted: 455
- Files succeeded: 451
- Files failed: 4
- Probe progress ratio: 20.40%
- Goals satisfied: 2,920
- Goals unsatisfied: 21,610
- Fanout claim count: 2,920
- EvidenceRecords accepted: 3,371
- Materialized observation bytes: 7,994,062 / 8,000,000

## Backend Behavior

Authoritative physical telemetry:

- Configured: true
- Available: true
- Execution status: partial
- Mutagen attempts/successes: 454 / 451
- ffprobe physical attempts/successes: 0 / 0
- native_minimal physical attempts/successes: 0 / 0
- Fallback backends used: none projected
- Backend errors: FFPROBE_NOT_AVAILABLE=346, MEDIA_BACKEND_UNSUPPORTED_FORMAT=3

The remaining ffprobe unavailable count is telemetry from unavailable-backend handling; it is not evidence that ffprobe was used as a successful physical fallback.

## Evidence

- Total media EvidenceRecords: 3,371
- Evidence by backend: mutagen=3,371
- Technical evidence total: 3,155
- Semantic identity evidence total: 216
- track_title: 108
- artist: 108
- album: 0
- album_artist: 0

The run proves Mutagen identity acquisition at the EvidenceRecord level. It does not prove downstream row claim binding because materialization blocked before row semantic validation.

## B vs B2

| Metric | Run B | Run B2 |
|---|---:|---:|
| Base SHA | 84d091df... | f3fec1c... |
| Logical tasks | 15,610 | 24,530 |
| Physical groups | 2,230 | 2,230 |
| Probes attempted | 336 | 455 |
| Probes succeeded | 335 | 451 |
| EvidenceRecords | 3,083 | 3,371 |
| Materialized bytes | 7,335,302 | 7,994,062 |
| Probe progress | 15.07% | 20.40% |
| Terminal reason | TOTAL_BUDGET_EXCEEDED | MATERIALIZED_BYTES_BUDGET_EXCEEDED |
| Terminal events | 1 | 1 |
| SpeakerTruth safe | false | false |
| track_title evidence | not projected | 108 |
| artist evidence | not projected | 108 |
| album evidence | not projected | 0 |
| album_artist evidence | not projected | 0 |

Slice 3 materially improved physical acquisition progress and removed the previous total-time frontier as the first blocker. The new first blocker is materialized evidence byte budget.

## Root-Cause Gates

- SLICE3_PHYSICAL_ACQUISITION_IMPROVEMENT: PROVEN
- MUTAGEN_IDENTITY_PATH: PROVEN for EvidenceRecord acquisition; downstream binding NOT_REACHED
- BACKEND_OVER_ACQUISITION_REGRESSION: PASS
- TELEMETRY_PROJECTION: FAIL
- MATERIALIZATION_FRONTIER: PROVEN
- TIME_BUDGET_FRONTIER: CLEARED_AS_FIRST_FRONTIER
- DOWNSTREAM_IDENTITY_BINDING: NOT_REACHED
- ROOT_CAUSE_STATUS: PROVEN

## Issues

- P0: 0
- P1: 1, materialized observation byte budget frontier
- P2: 2, public summary projection contradiction and missing bounded claim-level sample before materialization block
- P3: 0

## Deviations

- Claim-level row-validation and opaque/untagged samples were not available because the run blocked before row claim binding and row semantic validation.
- Backend was restarted before public execution to establish a clean healthy runtime on the required main SHA.
- Runtime startup updated `config/skills/registry/skills_index.json` `updated_at` only; the tracked config file was restored to HEAD before commit.

## Recommended Next Experiment

Do not run C yet. Diagnose and correct post-compile observation materialization/retention before introducing ffprobe as another variable.
