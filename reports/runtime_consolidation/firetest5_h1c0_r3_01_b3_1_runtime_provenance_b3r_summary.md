# FireTest 5 H1C0.R3.01 B3.1 Runtime Provenance + B3R

## Verdicts

- `R3_01_B3_1_STALE_RUNTIME_PROVEN`
- `FIRETEST5_R3_01_B3R_BLOCKED_WITH_NEW_FRONTIER_PROVEN`

## Root Cause

Original B3 was served by a stale API process. PID `18944` was created at `2026-08-20T08:46:41-03:00`, while the Slice 4 source base `08a7028047b0d0b216a576a68cd178085bfec9b0` was committed at `2026-08-21T10:44:59-03:00`. That process could not have loaded the final Slice 4 code.

A second local checkout exists at `C:\Users\rafae\Documents\GitHub\AIpinho`; after restart, the live API process provenance is `C:\Dev\AIpinho` by process cwd and pidfile. The original process cwd/import root is not recoverable because it was stopped before the two-checkout evidence arrived. No code was copied or synchronized between repositories.

## Repository Comparison

- `C:\Dev\AIpinho`: branch `agent/codex/r3-01-b3-post-slice4-mutagen`, HEAD `74f35547a691cf6be1d552406544ca388e57b007`, origin/main `08a7028047b0d0b216a576a68cd178085bfec9b0`, `0 behind / 1 ahead`.
- `C:\Users\rafae\Documents\GitHub\AIpinho`: branch `agent/codex/r3-01-b3-post-slice4-mutagen`, HEAD `08a7028047b0d0b216a576a68cd178085bfec9b0`, origin/main `08a7028047b0d0b216a576a68cd178085bfec9b0`, `0 behind / 0 ahead`.

## Restart + Canary

Restart used the documented scripts from `C:\Dev\AIpinho`. Current process PID `15424` has cwd `C:\Dev\AIpinho`, executable `C:\Program Files\Python311\python.exe`, and command line `['C:\\Program Files\\Python311\\python.exe', '-m', 'uvicorn', 'aipinho.main:app', '--host', '0.0.0.0', '--port', '9088']`.

Slice 4 canary run `task_run_40669d95118040d58fab1f77932f925d` passed the schema gate:

```json
{
  "checkpoint_count": 1,
  "checkpoint_bytes": 6620,
  "inline_materialized_bytes": 4963,
  "evidence_records_produced": 4,
  "evidence_records_accepted": 4,
  "evidence_records_rejected": 0,
  "physical_probe_count": 1,
  "files_attempted": 1
}
```

It persisted one checkpoint payload of 6620 bytes.

## B3R Public Run

- task_run_id: `task_run_fb5e41300c3e43c9b7353e91c1c01569`
- operation_id: `op_634f30723a184308b9f91682e8b412ed`
- status: `blocked`
- reason: `POST_COMPILE_OBSERVATION_CONSECUTIVE_EXECUTION_FAILURES_EXCEEDED`
- terminal_event_count: `1`
- SpeakerTruth.safe_to_report_success: `False`

## B3R Telemetry

- physical groups: `2230`
- physical probes: `940`
- physical successes/failures: `918` / `22`
- evidence records produced: `6852`
- evidence records accepted: `5934`
- evidence records rejected: `918`
- checkpoint_count: `918`
- checkpoint_bytes: `8813500`
- checkpoint_write_failures: `0`
- inline_materialized_bytes: `4829307` / `8000000`
- checkpoint payload files observed: `918`
- max single checkpoint observed: `13426` bytes
- max records per checkpoint observed: `8`

## Evidence From Checkpoints

- by backend: `{'mutagen': 5934}`
- by key: `{'artist': 214, 'artwork': 918, 'bitrate': 918, 'channels': 918, 'codec': 916, 'duration': 918, 'sample_rate': 918, 'track_title': 214}`
- semantic identity: `track_title=214`, `artist=214`, `album=0`, `album_artist=0`

## B2 / Original B3 / B3R

| Metric | B2 | Original B3 | B3R |
| --- | ---: | ---: | ---: |
| reason | `POST_COMPILE_OBSERVATION_MATERIALIZED_BYTES_BUDGET_EXCEEDED` | `POST_COMPILE_OBSERVATION_MATERIALIZED_BYTES_BUDGET_EXCEEDED` | `POST_COMPILE_OBSERVATION_CONSECUTIVE_EXECUTION_FAILURES_EXCEEDED` |
| probes | 455 | 455 | 940 |
| successes | 451 | 451 | 918 |
| failures | 4 | 4 | 22 |
| inline bytes | 7994062 | 7994062 | 4829307 |
| checkpoint_count | 0 | 0 | 918 |
| checkpoint_bytes | 0 | 0 | 8813500 |
| track_title evidence | 108 | 108 | 214 |
| artist evidence | 108 | 108 | 214 |

Original B3 running effective Slice 4 runtime: **NO**.

B2 materialized-bytes frontier eliminated after verified restart: **YES**. B3R remained below the 8 MB inline budget and persisted 918 evidence checkpoints.

## New Frontier

`POST_COMPILE_OBSERVATION_CONSECUTIVE_EXECUTION_FAILURES_EXCEEDED`

The next gate should diagnose the 22 physical failures / consecutive unsupported-format sequence after 940 probes. Do not change dependency state, budgets, or concurrency until that mechanism is classified.
