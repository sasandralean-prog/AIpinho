# FireTest 5

## Purpose

FireTest 5 is an adversarial validation instrument using Pinhoabacaxi Desktop and a real imperfect local music corpus to expose generic AIpinho architectural weaknesses.

It is not a project to perfect a music library scanner.

## Core rule

The fixture may reveal architecture. The architecture may not become fixture-specific.

## What FireTest 5 exposed across H1C0.R2

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
- identity coverage semantics.

## R3.01 / B3.5 canary status

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

FireTest 5 remains `NOT_READY` until B3.6 resolves or further narrows the applicability-resolution capacity/admission frontier.

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
- extension as semantic authority.

Extension may remain a routing hint when semantically justified.

## Phase dependency

If Phase 1 blocks, Phases 2–6 must not pretend to execute.

Expected pattern where applicable:

```text
status = skipped_due_to_prior_block
api_called = false
```

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

## Current FireTest question

Can AIpinho reach governed post-compile observation with a bounded, contract-scoped applicability path, acquire evidence only where justified, preserve provenance, and refuse to convert filename/path/extension into Truth?

## B3.6 canary gate

Do not run full FireTest 5 until B3.6 canary work proves or blocks with a more precise evidence-backed boundary for applicability capacity/admission.
