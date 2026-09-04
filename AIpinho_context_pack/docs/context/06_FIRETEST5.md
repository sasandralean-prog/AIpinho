# FireTest 5

## Purpose

FireTest 5 is an adversarial validation instrument using Pinhoabacaxi Desktop and a real imperfect local music corpus to expose generic AIpinho architectural weaknesses.

It is not a project to perfect a music library scanner.

## Core rule

The fixture may reveal architecture. The architecture may not become fixture-specific.

## Current operational checkpoint — 2026-09-04

The practical FireTest workstream had advanced beyond the older high-level B3.5 orientation and was parked at the **FireTest C / FFmpeg full-phase diagnostic boundary**.

Historical branch retained for that checkpoint:

```text
branch: agent/codex/firetest-c-ffmpeg-full-phase-diagnostic
head:   cb3846bdbc2372150ba8164a667ef8ef7921cb7e
last recorded commit: test(firetest): record phase c diagnostic evidence
```

The next intended product-test step is not to declare FireTest ready. It is to introduce/admit **FFmpeg as a governed AIpinho capability** and then run the FireTest far enough to obtain evidence-backed diagnosis of **Phase 1 and Phase 2**.

Operational intent:

```text
FFmpeg capability admitted through normal AIpinho governance
→ FireTest product request
→ Phase 1 executes or blocks honestly
→ if Phase 1 permits continuation, Phase 2 executes or blocks honestly
→ collect runtime/evidence/validation/SpeakerTruth
→ diagnose the next real architectural frontier
```

No production code may special-case FireTest, Pinhoabacaxi, the corpus path, `.m4a`, FFmpeg output, row counts, or artifact names merely to make the scenario pass.

## Local music corpus update

The previous local music-corpus location must no longer be assumed valid. The old folder may have been moved or deleted.

The new expected location is approximately:

```text
D:\Rafa\músicas
```

This path is **operator-provided orientation, not yet observed host evidence**. Before the next FireTest execution, the governed local runner must discover/verify the actual directory and bind the observed path into the test request/evidence rather than hard-code an unverified path into production logic.

The corpus consists of deliberately adversarial **fake `.m4a` files**. Their `.m4a` extension must remain only locator/routing context. The test is specifically useful because semantic/media truth must come from governed observation (for example an admitted FFmpeg-backed capability), not from trusting the extension or filename.

## What FireTest 5 exposed across H1C0.R2/R3 work

- result finalization;
- terminality;
- artifact worker stalls;
- perception payload compilation;
- fact projection;
- source binding;
- persistence;
- payload refs;
- CSV streaming;
- cardinality ambiguity;
- run-to-run determinism;
- cell lookup complexity;
- identity coverage semantics;
- governed observation capability configuration;
- post-compile capability applicability/admission capacity.

## R3.01 / B3.5 canary history

Full FireTest 5 was not executed in B3.5.

B3.5 ran a public canary through `/api/v1/analyze`:

```text
task_run_id                         task_run_10a7ad7dabca4687bcebbe5cba30ce25
operation_id                        op_42cafcfaa0654bf299011345171199dc
status                              blocked
reason_code                         POST_COMPILE_CAPABILITY_APPLICABILITY_RESOLUTION_STALLED
terminal_blocking_event_count        1
SpeakerTruth.safe_to_report_success false
physical_probe_count                0
```

The canary proved that B3.5 removed the previous generic post-compile stall boundary and exposed a more specific capacity/admission frontier before physical probes.

This remains valid historical runtime evidence, but it must not erase the later operational FireTest-C/FFmpeg checkpoint described above.

## B3.5 telemetry

```text
task_count                          25
tasks_seen                          9
deferred_task_count                 7
execute_observer_task_count          2
target_entity_ref_count             10000
capability_lookup_attempted          2
capability_availability_checked      2
applicability_started_count          9144
applicability_completed_count        9144
applicability_failed_count           0
capability_applicable_count          0
capability_inapplicable_count        9143
capability_applicability_unknown_count 0
capability_inapplicable_reasons      MEDIA_CAPABILITY_EXTENSION_NOT_DECLARED_BY_BACKENDS: 9143
groups_created_count                0
backend_snapshot_started            false
backend_snapshot_completed          false
before_physical_probe_emitted        false
elapsed_ms                          120046
```

## Forbidden fixture logic

Production code should not branch on:
- `FireTest`;
- `Pinhoabacaxi`;
- local corpus paths;
- specific artifact names;
- observed row counts;
- task IDs;
- filenames;
- `.m4a` as semantic truth;
- extension as semantic authority.

Extension may remain a routing hint when semantically justified.

## Phase dependency

If Phase 1 blocks, Phases 2–6 must not pretend to execute.

Expected pattern where applicable:

```text
status = skipped_due_to_prior_block
api_called = false
```

The next FFmpeg-backed FireTest-C diagnostic is specifically intended to produce truthful evidence for Phase 1 and, only when Phase 1 permits it, Phase 2.

## READY semantics

`READY` for a wave means the current architectural boundary is closed. It does not automatically mean FireTest 5 is globally ready.

At the end of R2:

```text
H1C0.R2 = H1C0_R2_READY_FOR_R3
FireTest 5 = NOT_READY
```

In B3.5:

```text
B3.5 forensic slice = READY after review
FireTest 5 = NOT_READY
C gate = CORRECTIVE_REQUIRED_BEFORE_C
```

At the restored operational checkpoint:

```text
FireTest C / FFmpeg diagnostic = next product-test frontier
FFmpeg governed capability     = required/admission work
Phase 1 + Phase 2 diagnosis    = intended next evidence
FireTest 5 global READY        = NOT CLAIMED
```

## Current FireTest question

Can AIpinho admit and execute a governed media-observation capability such as FFmpeg, use it against an adversarial corpus without trusting filename/path/extension as Truth, preserve provenance, and terminalize Phase 1 and Phase 2 with evidence-backed semantic reasons?

## Re-entry rule

Before the next product FireTest run:

1. verify the actual corpus directory on the local host (expected around `D:\Rafa\músicas`);
2. verify the adversarial fake-`.m4a` fixture is present;
3. admit/configure FFmpeg through normal AIpinho capability governance rather than an ad-hoc subprocess bypass;
4. use the external Control runner only as governed engineering/execution infrastructure; Control evidence does not replace AIpinho runtime truth;
5. run the FireTest product path and accept either honest progress or an evidence-backed block as the diagnostic result.
