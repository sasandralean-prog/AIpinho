# FireTest 5

## Purpose

FireTest 5 is an adversarial validation instrument using Pinhoabacaxi Desktop and a real imperfect local music corpus to expose generic AIpinho architectural weaknesses.

It is not a project to perfect a music-library scanner.

## Core rule

> The fixture may reveal architecture. The architecture may not become fixture-specific.

Production code must not special-case FireTest, Pinhoabacaxi, corpus paths, `.m4a`, observed row counts, task IDs, filenames, or artifact names merely to pass the scenario.

Path/filename/extension remain locator or routing evidence. Semantic media Truth requires governed observation.

## Historical R3.01 / B3.5 evidence

B3.5 did not execute the full FireTest. Its public canary moved the runtime from a generic post-compile stall to a specific applicability/admission boundary:

```text
status: blocked
reason: POST_COMPILE_CAPABILITY_APPLICABILITY_RESOLUTION_STALLED
SpeakerTruth.safe_to_report_success: false
physical_probe_count: 0
execute_observer_task_count: 2
target_entity_ref_count: 10000
applicability_completed_count: 9144
capability_inapplicable_count: 9143
groups_created_count: 0
elapsed_ms: 120046
```

This remains useful evidence. The open B3.6 question about applicability-resolution capacity/admission is not erased by later FireTest work.

## Operational progression after the 2026-09-04 checkpoint

The workstream was re-entered progressively through external `CONTROL-H3-J` governance.

Important namespace rule:

```text
CONTROL-H3-J
    external Control Plane tranche for progressive FireTest admission

Horizon H3
    long-term AIpinho strategic planning category
```

They are unrelated namespaces.

### H3-J1 narrow unit admission — live passed

On 2026-09-05 the Control Plane executed a fresh authenticated narrow unit-level FireTest/CVL surface:

```text
Control run: 33933759448
operation: op_h3j_j1_firetest_unit_admission_after_venv_20260905T004300Z
semantic capability: engineering.test.pytest
target: aipinho
network: deny
elevation: false
inherit_secrets: false
test: tests/unit/test_cognitive_validation_laboratory_service.py
result: 19 passed in 0.51s
```

This proves only the admitted unit surface. It does not prove live product FireTest readiness.

### Live multi-endpoint observer

AIpinho `main` now includes the FireTest live observer merged through PR #8 at:

```text
a4253226d5af73ffa8eea6279943cce5915fb507
```

The observer separates chat dispatch from later TaskRun acquisition/correlation and observes multiple read-only runtime endpoints. A chat response is no longer assumed to contain the TaskRun identifier synchronously.

## Latest product FireTest attempt — 2026-09-06

The latest bounded FireTest B product attempt was governed by Control and produced a truthful product block:

```text
Control run: 34059896495
operation: op_firetest5_b_clean_final_20260906T211500Z
Control workflow: completed
product verdict: BLOCKED_PRE_TASK
Phase 1 status: timeout_blocked
HTTP: 200
reason: PUBLIC_RUNTIME_CREATE_RUN_NOT_REACHED
internal_reason: readonly_or_planning
task_run_id: null
terminal_result: absent
terminal_event: none
observer_verdict: CHAT_COMPLETED_WITHOUT_TASK_RUN_ID
SpeakerTruth.safe_to_report_success: false
Phases 2-6: skipped_due_to_prior_block
```

A green Control workflow means the governed operation/evidence loop completed; it does **not** turn this product block into FireTest success.

The exact boundary exposed by that run is now more concrete than the old 2026-09-04 planning sentence: the public product request completed without reaching TaskRun creation.

## Corpus state

The expected corpus remains around:

```text
D:\rafa\novapinhomusic
```

The 2026-09-07 reset report observed the corpus paths present, `corpus_ok=YES`, and no corpus file modified by the cleanup operation.

This host observation is stronger than the earlier operator-only orientation, but each new FireTest run should still bind the observed current path/corpus identity into its own evidence rather than hard-code it in production logic.

The corpus contains adversarial fake `.m4a` files. `.m4a` is not semantic authority.

## FFmpeg / FFprobe boundary

Two observations must remain distinct:

### 2026-09-06 FireTest execution context

The bounded FireTest B preconditions reported:

```text
ffmpeg=false
ffprobe=false
```

### 2026-09-07 host reset

The reset reported:

```text
ffmpeg_present=YES
ffprobe_present=YES
```

The binaries were already installed and were not installed, removed, or modified by reset.

Therefore the correct current statement is:

```text
host installation observed = yes
exact governed FireTest visibility = must be reverified
AIpinho governed capability admission = not proven by host presence
semantic media observation = not proven by host presence
```

Do not solve this by assuming PATH, injecting an ad-hoc subprocess path, or treating installation as capability authority.

## Clean reset checkpoint — 2026-09-07

After the 06/09 campaign, a governed cleanup/reset was reported:

```text
RESET_STATUS=CLEAN
TaskRuntime: active=0 pending=0 orphaned=0 leases=0
Chat: active=0 pending=0 orphaned=0
active locks/leases=0
official hygiene preview candidates=0
AIpinho API: OFFLINE
port 9088: no listener
old Control runner: stopped/disabled
Envelope runner: kept running
unrelated processes killed=0
tracked AIpinho: HEAD == origin/main == a4253226...
worktree_clean=YES
corpus_ok=YES
new FireTest round: not started
```

The historical long-running TaskRun `task_run_b81c3ce03ec44212b133b691131a838c` and the 06/09 observer were terminalized as `cancelled` and preserved for audit. The historical `firetest5_capability_observation_20260810` session remains preserved without an active request.

Expired stale Control approvals/grants are audit residue, not current execution authority.

`RESET_STATUS=CLEAN` means **clean operational baseline**, not `FireTest READY`.

## Current FireTest status

```text
FireTest 5 global status: NOT_READY
new campaign after reset: NOT_STARTED
AIpinho API: OFFLINE
clean runtime/chat queues: YES
corpus host presence/integrity: YES
FFmpeg/FFprobe host presence: YES
FFmpeg/FFprobe exact governed visibility/admission: PENDING REPROOF
latest product boundary: PUBLIC_RUNTIME_CREATE_RUN_NOT_REACHED
```

## Re-entry protocol for the next campaign

1. Reobserve all three repository heads and tracked state.
2. Acquire fresh `firetest` and any required `runtime`/test coordination locks.
3. Start/enable the required Control runner and AIpinho runtime through governed lifecycle authority.
4. Verify port `9088`, health, exact runtime source provenance, and no stale queue residue.
5. Reobserve corpus path/presence and bind that observation to the new campaign.
6. Reobserve FFmpeg/FFprobe executable visibility in the exact execution context and confirm normal AIpinho capability admission/evidence semantics.
7. Submit a **fresh** FireTest product request with a new correlation/session identity.
8. Observe TaskRun creation independently from chat response.
9. Collect Phase 1 truth. Execute Phase 2 only if Phase 1 permits continuation.
10. Classify the next architectural boundary without FireTest-specific production logic.
11. If applicability/capacity behavior reappears, reconcile it with the historical B3.6 evidence rather than hiding it.

## READY semantics

A wave or Control gate being accepted does not make FireTest globally ready.

```text
Control operation completed != product fulfilled
Task terminalized != semantic success
binary installed != capability admitted
observer exists != product path works
unit admission passed != broad/live FireTest passed
```

The next useful outcome may be progress or another honest block. Both are valid diagnostics if evidence and terminal semantics are correct.
