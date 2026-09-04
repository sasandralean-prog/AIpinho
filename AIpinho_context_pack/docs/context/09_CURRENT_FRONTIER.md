# Current Frontier

## Canonical runtime state

```text
H1C0.R2 = H1C0_R2_READY_FOR_R3
H1C0.R3.01 = OPEN

Latest reviewed slice:
H1C0.R3.01.B3.5

Latest reviewed verdict:
R3_01_B3_5_PUBLIC_CANARY_POST_COMPILE_STALL_FORENSICS_READY

FireTest 5:
NOT_READY, not executed in B3.5

C gate:
CORRECTIVE_REQUIRED_BEFORE_C
```

## Operational FireTest re-entry checkpoint — 2026-09-04

The reviewed B3.5 state above remains valid runtime history, but the practical FireTest workstream had later been parked at a more concrete product-test boundary:

```text
branch: agent/codex/firetest-c-ffmpeg-full-phase-diagnostic
head:   cb3846bdbc2372150ba8164a667ef8ef7921cb7e
checkpoint: FireTest C / FFmpeg full-phase diagnostic
```

The next FireTest product-test objective is:

```text
admit/configure FFmpeg as a governed AIpinho capability
→ execute FireTest against the adversarial music corpus
→ obtain truthful Phase 1 evidence
→ if Phase 1 permits continuation, obtain truthful Phase 2 evidence
→ diagnose the next architectural boundary
```

The previous music-corpus directory must not be assumed to exist. Operator-provided current orientation is approximately:

```text
D:\Rafa\músicas
```

The corpus contains deliberately adversarial fake `.m4a` files. Before execution, the external governed runner must verify the actual host path and corpus presence. The path and `.m4a` extension are fixture/location evidence, not semantic media Truth.

## Git/report baseline

Repository:
`https://github.com/sasandralean-prog/AIpinho`

Default branch:
`main`

Base main for B3.5:
`50af6491b78e662bbd3390a59400aec6f0eb0bb1`

B3.5 branch:
`agent/codex/r3-01-b3-5-postcompile-stall-route-boundary`

B3.5 reviewed/report-corrected head before this context update:
`9d5e06c9d2cd8d0a885e53855bd100b4c7a84105`

FireTest-C historical diagnostic branch:
`agent/codex/firetest-c-ffmpeg-full-phase-diagnostic`

FireTest-C recorded head:
`cb3846bdbc2372150ba8164a667ef8ef7921cb7e`

## Current public truth

B3.5 moved the canary from:

```text
POST_COMPILE_OBSERVATION_EXECUTION_STALLED
```

to:

```text
POST_COMPILE_CAPABILITY_APPLICABILITY_RESOLUTION_STALLED
```

This is a forensic success, not FireTest success.

Current reviewed canary telemetry:

```text
task_run_id                         task_run_10a7ad7dabca4687bcebbe5cba30ce25
operation_id                        op_42cafcfaa0654bf299011345171199dc
status                              blocked
reason_code                         POST_COMPILE_CAPABILITY_APPLICABILITY_RESOLUTION_STALLED
terminal_blocking_event_count        1
SpeakerTruth.safe_to_report_success false
physical_probe_count                0

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

## Current issues

```text
P0: none observed
P1: R3_01_B3_5_P1_CAPABILITY_APPLICABILITY_RESOLUTION_CAPACITY_FRONTIER
P2: none blocking after report projection correction
```

Resolved P2:
- `P2_B3_5_REPORT_PROJECTION_INCOMPLETE_FOR_GROUPING_APPLICABILITY_TELEMETRY`
- `R3_01_B3_4_P2_PUBLIC_CHAT_ROUTE_SCHEMA_COLLISION_OR_HANDLER_PRECEDENCE`

## Route boundary

```text
/api/v1/chat          = canonical ChatRequest route
/api/v1/runtime/chat  = PublicRuntimeRequest chat route
/api/v1/analyze       = PublicRuntimeRequest analyze bridge used by canary
```

## R3.01 central question

Not:

> How can AIpinho fill title/artist/album?

But:

> How can AIpinho acquire governed observations that support semantic identity claims, preserve provenance, and distinguish unsupported/missing/failed evidence without using filename/path/extension as Truth?

## B3.6 capacity question retained as historical/open diagnostic context

```text
Why do 2 execute_observer tasks expand to 10000 target entity refs,
perform 9144 applicability decisions,
classify 9143 as inapplicable by extension,
create 0 groups,
consume 120046ms,
and reach 0 physical probes?
```

That evidence remains important. Re-entering at FireTest C does not waive it. The FFmpeg-backed diagnostic must either show that the applicability/admission path is now sufficient for the bounded product flow or reproduce/replace it with a more precise evidence-backed boundary.

## Immediate next product-test frontier

```text
1. governably verify the corpus path on the host (expected around D:\Rafa\músicas)
2. verify the fake-.m4a adversarial corpus exists
3. inspect/reconcile the FireTest-C branch against current main before reuse
4. admit/configure FFmpeg through AIpinho's normal capability model
5. run the bounded FireTest C product diagnostic
6. collect Phase 1 truth
7. execute Phase 2 only if Phase 1 permits it
8. classify the resulting boundary without FireTest-specific production logic
```

## Historical R2.18 context

R2.18 row-level validation can observe semantic identity fields and row evidence refs. It established that stable entity identity is not semantic media identity.

That history remains authority for the no-filename/path/extension-Truth rule, but it is no longer by itself the current operational FireTest checkpoint.
