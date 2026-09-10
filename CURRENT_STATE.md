# AIpinho — Current State

_Last reconciled: 2026-09-07 by Lúcio_

## Repository role

`sasandralean-prog/AIpinho` is the runtime/application repository. It is authoritative for AIpinho production code, canonical runtime contracts/config, and validated product/runtime evidence.

External governance/execution authority lives in:

```text
sasandralean-prog/AIpinho-FireTest-Control
```

Unsigned request intake lives in:

```text
sasandralean-prog/AIpinho-Envelope-Requests
```

Control evidence proves bounded Control actions/provenance; it does not replace AIpinho runtime/validation/SpeakerTruth authority.

## Naming correction — strategic Horizons vs Control tranches

The roadmap's `Horizon H1/H2/H3/H4` labels are **planning/maturity categories**, not patch or update identifiers.

```text
Horizon H1 = near-term foundational maturation
Horizon H2 = medium-term tool/operations maturation
Horizon H3 = medium-to-long-term agentic collaboration/initiative
Horizon H4 = long-range exploratory evolution
```

They organize objectives and ideas from short to long planning distance.

They are **not** the same namespace as:

```text
CONTROL-H1
CONTROL-H2
CONTROL-H3
```

`CONTROL-H*` names are concrete implementation/validation tranches in the separate Lúcio Shell/Control Plane. No completion or authority should be inferred across these namespaces.

## Repository snapshot — observed before this documentation refresh

```text
AIpinho main
  a4253226d5af73ffa8eea6279943cce5915fb507

Control main
  dacd3e5afde981e077ef212b7c1072bfea80b8a7

Envelope Requests main
  8ff0632736a01b5faf27e53fcffd12ecbdc3cbca
```

Reobserve live `main` before engineering or execution.

## AIpinho source baseline

Current pre-refresh `main` includes the live multi-endpoint FireTest observer merged in PR #8. The observer corrects an important protocol assumption:

```text
POST /api/v1/chat response
  does not have to synchronously contain task_run_id

fresh correlation/session id
→ chat dispatch
→ independent TaskRun lookup
→ TaskRun/runtime/operator observation
→ terminal/product verdict
```

This tooling is part of the next FireTest baseline; the old observer process from the 06/09 campaign is not.

## Current FireTest status

```text
FireTest 5: NOT_READY
progressive governed re-entry: active as a program
new campaign after 2026-09-07 reset: NOT_STARTED
```

### Latest product attempt — 2026-09-06

```text
Control run: 34059896495
operation: op_firetest5_b_clean_final_20260906T211500Z
Control operation/evidence loop: completed
product verdict: BLOCKED_PRE_TASK
Phase 1: timeout_blocked
HTTP: 200
reason: PUBLIC_RUNTIME_CREATE_RUN_NOT_REACHED
internal_reason: readonly_or_planning
task_run_id: null
terminal result: absent
terminal event: none
observer verdict: CHAT_COMPLETED_WITHOUT_TASK_RUN_ID
SpeakerTruth.safe_to_report_success: false
Phases 2-6: skipped_due_to_prior_block
```

The green Control workflow is evidence of a completed governed diagnostic. It is **not** FireTest product success.

## Clean reset checkpoint — 2026-09-07

Operator-supplied governed reset evidence reports:

```text
RESET_STATUS=CLEAN
TASK_RUNTIME active=0 pending=0 orphaned=0 leases=0
CHAT active=0 pending=0 orphaned=0
active locks/leases=0
official hygiene preview candidates=0
```

Historical cleanup actions:

- `task_run_b81c3ce03ec44212b133b691131a838c` -> `cancelled`, terminal event recorded, history preserved;
- 06/09 FireTest observer -> `cancelled`, terminal event recorded, history preserved;
- historical session `firetest5_capability_observation_20260810` preserved without active request.

Control residue:

```text
in_progress=0
pending=0
stale approvals=20 expired
orphaned grants=4 expired
```

Expired objects are audit residue, not active authority.

Process state:

```text
AIpinho API: OFFLINE
port 9088 listener: none
old Control runner: stopped/disabled
Envelope runner: kept running
unrelated processes killed: 0
```

Integrity:

```text
AIpinho HEAD == origin/main == a4253226d5af73ffa8eea6279943cce5915fb507
worktree_clean=YES
corpus_ok=YES
corpus modified by reset=NO
new FireTest round started=NO
```

This is a clean/cold baseline, not readiness.

## Corpus

Current host orientation:

```text
D:\rafa\novapinhomusic
```

The 07/09 reset reported the paths present and corpus unmodified.

The corpus deliberately contains adversarial fake `.m4a` files. Path, filename, and extension remain locator/routing evidence only. Semantic media identity/structure must come from governed observation.

## FFmpeg / FFprobe current truth

Keep both observations:

```text
06/09 FireTest execution context:
  ffmpeg=false
  ffprobe=false

07/09 host reset:
  ffmpeg_present=YES
  ffprobe_present=YES
```

The reset did not install, remove, or modify those binaries.

Therefore:

```text
host presence = observed positive infrastructure fact
exact governed child/runtime visibility = pending reproof
AIpinho capability admission/applicability = not proven by installation
semantic observation = not proven by installation
```

Do not “fix” this contradiction by hard-coding an executable path. Reobserve the exact governed environment.

## External Control current state

The Control repository is materially beyond the historical B1.0/G snapshots:

```text
G3_BASELINE_VALIDATED
CONTROL-H1 through H1-E validated
CONTROL-H2 through H2-E validated
CONTROL-H3-A through H3-H accepted at defined scopes
CONTROL-H3-I E2E authority compression live accepted + independently reproduced
CONTROL-H3-J progressive FireTest re-entry started
```

Frozen lower-layer invariants remain:

```text
runner: aipinho-pc
Windows identity: .\aipinho-runner
mode: current_session
process API: CreateProcessW
principal lucio: Ed25519 authenticated
replay: consumed before execution
rerun: not fresh authority
elevation: false ordinary invariant
inherit_secrets: false ordinary invariant
semantic capability + Script Catalog hash binding required
structured lifecycle/evidence required
```

### H3-J1 narrow FireTest admission

Fresh live proof on 2026-09-05:

```text
run: 33933759448
operation: op_h3j_j1_firetest_unit_admission_after_venv_20260905T004300Z
semantic capability: engineering.test.pytest
target: aipinho
network: deny
result: 19 passed in 0.51s
```

This proves a narrow unit surface, not broad/live product readiness.

Control has continued to grow after H3-J1, including a manual-only Desktop Commander remote-command catalog entry/request path. That authority is unrelated to FireTest and grants no implicit product permission.

## Envelope current state

`AIpinho-Envelope-Requests` remains unsigned intake transport into the local broker. Its current pre-refresh `main` contains a recent request to retry the manual-only governed Desktop Commander remote execution.

The Envelope repository:

- does not store the production private key;
- does not sign;
- does not allocate execution authority by request text;
- does not turn a push into generic shell access;
- does not grant FireTest authority.

## Historical B3.5/B3.6 runtime evidence

The reviewed historical slice remains:

```text
H1C0.R3.01.B3.5
R3_01_B3_5_PUBLIC_CANARY_POST_COMPILE_STALL_FORENSICS_READY
reason=POST_COMPILE_CAPABILITY_APPLICABILITY_RESOLUTION_STALLED
```

Key telemetry:

```text
execute_observer_task_count=2
target_entity_ref_count=10000
applicability_completed_count=9144
capability_inapplicable_count=9143
groups_created_count=0
physical_probe_count=0
elapsed_ms=120046
```

Historical structural debt retained:

```text
R3_01_B3_5_P1_CAPABILITY_APPLICABILITY_RESOLUTION_CAPACITY_FRONTIER
```

The next clean FireTest may confirm, refine, or supersede this boundary. Do not close it merely because external Control progressed.

## Readiness-latency corrective

The prior B0.4.1 endpoint-latency issue was localized to eager `PublicRuntimeAPI()` dependency construction. Corrective commit:

```text
d41a7bae664f718fd615c222864db7eeeecb67cf
```

introduced lazy construction and was live-validated with canonical endpoints completing well below the unchanged readiness timeout. Current AIpinho `main` descends from that correction.

Thus `API=OFFLINE` in the reset is a deliberate process state, not automatic evidence that the old latency defect returned.

## Immediate next step

Start the next FireTest as a **fresh campaign**:

```text
1. reobserve all repository heads/worktrees
2. acquire fresh firetest/runtime coordination locks
3. restore the required governed Control runner and AIpinho runtime
4. prove exact source provenance and healthy 9088
5. confirm queues/chat remain clean
6. bind current corpus observation to this campaign
7. prove FFmpeg/FFprobe visibility in the exact governed environment
8. prove normal AIpinho capability admission/applicability
9. submit fresh product request with fresh correlation/session identity
10. independently acquire/observe TaskRun
11. collect Phase 1 truth
12. run Phase 2 only if Phase 1 permits
13. reconcile the observed boundary with historical B3.6 evidence
```

The objective is to discover the next real architectural boundary, not to force a `READY` verdict.

## Authority rule

If this file conflicts with current AIpinho code/config or validated product evidence, those win for AIpinho truth. If it conflicts with Control `CURRENT_STATE.md`/current Control evidence about external governance/execution, Control wins for that external scope.
