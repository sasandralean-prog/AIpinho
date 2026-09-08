# Current Frontier

## Status discipline

This document separates the **latest operational FireTest boundary** from older reviewed runtime-wave evidence. Newer evidence does not erase history; older evidence does not automatically remain the current blocker.

Also preserve the namespace rule:

```text
Horizon H1/H2/H3/H4 = strategic product/maturity planning
CONTROL-H1/H2/H3    = external Control Plane implementation tranches
```

They are not equivalent.

## Current repository snapshot — observed before this documentation refresh, 2026-09-07

```text
AIpinho main
  a4253226d5af73ffa8eea6279943cce5915fb507

AIpinho-FireTest-Control main
  dacd3e5afde981e077ef212b7c1072bfea80b8a7

AIpinho-Envelope-Requests main
  8ff0632736a01b5faf27e53fcffd12ecbdc3cbca
```

Reobserve live heads before executing a new campaign.

## Current FireTest operational state

```text
FireTest 5 global status: NOT_READY
latest product attempt: 2026-09-06
latest product verdict: BLOCKED_PRE_TASK
latest product reason: PUBLIC_RUNTIME_CREATE_RUN_NOT_REACHED
post-campaign reset: RESET_STATUS=CLEAN
new FireTest campaign after reset: NOT_STARTED
AIpinho API/9088: OFFLINE at reset checkpoint
```

The next frontier is therefore not “continue the old observer” and not “install FFmpeg”. It is:

> Start a fresh governed FireTest campaign from the clean baseline, prove exact runtime/tool/corpus preconditions, then determine why the public product request does or does not create a TaskRun and proceed into Phase 1/Phase 2 only as evidence permits.

## Latest product-facing FireTest evidence — 2026-09-06

Control run:

```text
34059896495
```

Operation:

```text
op_firetest5_b_clean_final_20260906T211500Z
```

Observed product outcome:

```text
FIRETEST5_B=BLOCKED_PRE_TASK
Phase 1=status=timeout_blocked
HTTP=200
task_run_id=null
reason=PUBLIC_RUNTIME_CREATE_RUN_NOT_REACHED
internal_reason=readonly_or_planning
terminal_result=absent
terminal_event=none
observer_verdict=CHAT_COMPLETED_WITHOUT_TASK_RUN_ID
SpeakerTruth.safe_to_report_success=false
Phases 2-6=skipped_due_to_prior_block
```

The Control workflow itself completed successfully because it truthfully executed and packaged the governed diagnostic. That green workflow is not product success.

## Observer state

AIpinho main includes the live multi-endpoint observer merged through PR #8. The observer decouples:

```text
chat dispatch
→ correlation/session identity
→ independent TaskRun acquisition
→ read-only runtime observation
→ terminal/product verdict
```

This is now part of the baseline tooling. The observer from the 06/09 campaign was later cancelled/terminalized during reset; the implementation remains in `main`.

## Clean reset — 2026-09-07

Operator-supplied governed reset evidence reports:

```text
RESET_STATUS=CLEAN
TaskRuntime active=0 pending=0 orphaned=0 leases=0
Chat active=0 pending=0 orphaned=0
active coordination locks/leases=0
official hygiene preview candidates=0
historical long-running task -> cancelled + terminal event
06/09 FireTest observer -> cancelled + terminal event
historical audit session preserved
Control in_progress=0 pending=0
stale approvals=20 expired
orphaned grants=4 expired
AIpinho API=OFFLINE
port 9088=no listener
old Control runner=stopped/disabled
Envelope runner=running
unrelated_processes_killed=0
AIpinho head=origin/main=a4253226...
worktree_clean=YES
corpus_ok=YES
FFmpeg host present=YES
FFprobe host present=YES
new round started=NO
```

Expired approvals/grants are retained audit history, not live authority.

## FFmpeg visibility/admission boundary

The 06/09 FireTest execution context reported:

```text
ffmpeg=false
ffprobe=false
```

The 07/09 reset reported host presence:

```text
ffmpeg_present=YES
ffprobe_present=YES
```

Therefore the next campaign must prove the missing bridge rather than assume it:

```text
host binary presence
→ exact governed child/runtime visibility
→ normal AIpinho capability admission/applicability
→ governed observation execution
→ evidence/provenance
→ semantic claims
```

Do not hard-code a host path merely to make FireTest pass.

## Control Plane state relevant to re-entry

Current external Control progression is materially ahead of old Context Pack snapshots:

```text
G3_BASELINE_VALIDATED
CONTROL-H1 through H1-E validated
CONTROL-H2 through H2-E validated
CONTROL-H3-A through H3-H accepted at defined scopes
CONTROL-H3-I E2E authority compression live accepted and independently reproduced
CONTROL-H3-J progressive FireTest re-entry started
```

H3-J1 narrow FireTest/CVL unit admission has fresh live proof:

```text
Control run: 33933759448
operation: op_h3j_j1_firetest_unit_admission_after_venv_20260905T004300Z
semantic capability: engineering.test.pytest
result: 19 passed in 0.51s
```

This admits a narrow unit surface only. Broad product execution remains evidence-gated.

Control main has continued to evolve after that campaign, including a manual-only governed Desktop Commander remote-command catalog entry. That later authority is unrelated to FireTest and must not be treated as FireTest admission.

## Envelope state

`AIpinho-Envelope-Requests` remains unsigned intent transport into the local broker. It is never signing authority. Its current main includes a recent manual-only Desktop Commander request; that does not widen FireTest or AIpinho runtime authority.

## Historical B3.5/B3.6 evidence retained

The last reviewed B3.5 forensic slice remains historically valid:

```text
H1C0.R3.01.B3.5
R3_01_B3_5_PUBLIC_CANARY_POST_COMPILE_STALL_FORENSICS_READY
status=blocked
reason=POST_COMPILE_CAPABILITY_APPLICABILITY_RESOLUTION_STALLED
execute_observer_task_count=2
target_entity_ref_count=10000
applicability_completed_count=9144
capability_inapplicable_count=9143
groups_created_count=0
physical_probe_count=0
elapsed_ms=120046
```

Historical open structural question:

```text
R3_01_B3_5_P1_CAPABILITY_APPLICABILITY_RESOLUTION_CAPACITY_FRONTIER
```

B3.6 asks why a small number of observer tasks expands into thousands of applicability decisions and zero probes/groups. The next live FireTest may confirm this remains causal, show that newer admission/tool work bypassed that exact boundary legitimately, or expose a more precise blocker. Do not pre-close it from Control progress alone.

## Readiness/runtime latency corrective retained

A separate B0.4.1 diagnostic found public readiness latency caused by eager `PublicRuntimeAPI()` dependency construction. The corrective `d41a7bae664f718fd615c222864db7eeeecb67cf` introduced lazy construction and was live-validated without timeout inflation. Current AIpinho `main` descends from that corrective.

Therefore API `OFFLINE` at the reset checkpoint means the runtime is deliberately stopped, not that the old readiness-latency bug is automatically back.

## Immediate next campaign

```text
1. reobserve all repository heads and tracked state
2. acquire fresh firetest/runtime coordination locks
3. start required Control runner/runtime through governed lifecycle
4. prove exact runtime source and healthy 9088 state
5. prove clean queue/chat state remains clean
6. bind current corpus observation
7. prove FFmpeg/FFprobe visibility in exact governed environment
8. prove capability admission/applicability rather than host installation alone
9. submit fresh product request with fresh correlation identity
10. independently acquire/observe TaskRun
11. collect Phase 1 truth
12. execute Phase 2 only if Phase 1 permits
13. reconcile resulting boundary with historical B3.6 evidence
```

## Current P0/P1/P2 interpretation

No new P0 is asserted by this context refresh.

The historical B3.5 applicability-capacity P1 remains open evidence debt until newer product/runtime evidence closes or supersedes it. The 06/09 `PUBLIC_RUNTIME_CREATE_RUN_NOT_REACHED` boundary is the immediate operational diagnostic to reproduce/explain in the fresh campaign; do not prematurely assign a permanent architectural priority without the new clean-baseline evidence.

## Final rule

The next FireTest is a diagnostic, not a ceremony to obtain `READY`.

A truthful new block is acceptable. A false success is not.
