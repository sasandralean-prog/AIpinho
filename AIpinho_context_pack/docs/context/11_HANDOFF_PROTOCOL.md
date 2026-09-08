# Handoff Protocol — "Resurrect Lúcio"

Use this when moving AIpinho to a new ChatGPT/Codex session/account, changing models/work surfaces, onboarding an engineering assistant, or returning after a long interruption.

## 1. Locate the canonical pack

Start at:

```text
AIpinho_context_pack/docs/context/00_START_HERE.md
```

The canonical path is lowercase. Do not recreate the retired `docs/CONTEXT/` path.

## 2. Read repository authority before memory

For AIpinho engineering work:

1. `AGENTS.md`
2. `DOCUMENT_AUTHORITY.md`
3. this Context Pack in its documented order
4. current root `README.md`
5. current root `CURRENT_STATE.md`
6. current code/config relevant to the frontier
7. current reports/issues/evidence
8. current Git branch/head

Do not stop at context if Git/code/evidence can answer the factual question.

## 3. Mandatory namespace disambiguation

Never confuse these labels:

```text
AIpinho Horizon H1 / H2 / H3 / H4
  strategic maturity/planning horizons
  objectives and ideas grouped from near-term to long-range
  not patches, releases, or specific update tranches

CONTROL-H1 / CONTROL-H2 / CONTROL-H3
  concrete implementation/validation tranches in AIpinho-FireTest-Control
  Lúcio Shell / account / delegated-agent / engineering governance
```

The same number does not create a semantic relationship. Read the full namespace.

## 4. Reobserve all three repositories

Current continuity snapshot before the 2026-09-07 documentation refresh:

```text
AIpinho
  main a4253226d5af73ffa8eea6279943cce5915fb507

AIpinho-FireTest-Control
  main dacd3e5afde981e077ef212b7c1072bfea80b8a7

AIpinho-Envelope-Requests
  main 8ff0632736a01b5faf27e53fcffd12ecbdc3cbca
```

These are handoff pointers, not permanent truth. Re-fetch `main` before mutation or live execution.

## 5. Control/PC read order

For GitHub↔PC, runtime lifecycle, delegated Codex, Lúcio Shell, or FireTest coordination, inspect `sasandralean-prog/AIpinho-FireTest-Control` in this order:

1. `COMMUNICATION_SYNC_LUCIO.md`
2. `CURRENT_STATE.md`
3. `CONTEXT_PACK_LUCIO_SHELL.md`
4. `COMMUNICATION_SYNC.md`
5. relevant canonical report/artifact
6. current source/config
7. current Actions run/evidence when live truth matters

Also inspect `sasandralean-prog/AIpinho-Envelope-Requests` when request/intake provenance is relevant.

## 6. Repository roles

```text
AIpinho
  runtime/application repository
  authority for product/runtime code, contracts/config and validated runtime truth

AIpinho-FireTest-Control
  external governance/execution repository
  authentication, replay, broker, semantic capabilities, Script Catalog,
  launcher/bootstrap, H1/H2/CONTROL-H3 engineering authority, evidence/lifecycle

AIpinho-Envelope-Requests
  unsigned request transport into local governed broker
  never signing authority
```

Control evidence cannot silently override AIpinho product truth. Envelope request text cannot become execution authority by itself.

## 7. Current Control orientation

The old B1.0-D/E/F/G snapshots are historical. Current validated direction is materially later:

```text
G3_BASELINE_VALIDATED
CONTROL-H1 validated through H1-E
CONTROL-H2 validated through H2-E
CONTROL-H3-A through H3-H accepted at defined scopes
CONTROL-H3-I end-to-end authority compression live accepted and independently reproduced
CONTROL-H3-J progressive FireTest re-entry started
```

CONTROL-H3-J is progressive admission, not unrestricted FireTest.

A fresh J1 live operation on 2026-09-05 executed the narrow admitted FireTest/CVL unit surface through `engineering.test.pytest` and returned `19 passed in 0.51s` in Control run `33933759448`.

Control also contains later unrelated authority such as the manual-only governed Desktop Commander remote-command catalog entry. Do not treat unrelated Control capability growth as FireTest authority.

## 8. Latest product FireTest truth

The latest product-facing FireTest B attempt occurred on 2026-09-06:

```text
Control run: 34059896495
operation: op_firetest5_b_clean_final_20260906T211500Z
Control operation/evidence loop: completed
product verdict: BLOCKED_PRE_TASK
reason: PUBLIC_RUNTIME_CREATE_RUN_NOT_REACHED
task_run_id: null
SpeakerTruth.safe_to_report_success: false
Phases 2-6: skipped_due_to_prior_block
```

Do not report this as FireTest success merely because the Control workflow was green.

AIpinho `main` at `a4253226...` contains the live multi-endpoint observer that dispatches chat and then independently acquires/correlates the TaskRun.

## 9. Clean reset checkpoint

After the 06/09 campaign, operator-supplied governed reset evidence reported:

```text
RESET_STATUS=CLEAN
TaskRuntime active=0 pending=0 orphaned=0 leases=0
Chat active=0 pending=0 orphaned=0
active locks/leases=0
hygiene candidates=0
old long-running TaskRun cancelled + terminal event
06/09 observer cancelled + terminal event
historical audit session preserved
Control in_progress=0 pending=0
expired stale approvals=20
expired orphaned grants=4
AIpinho API=OFFLINE / 9088 no listener
old Control runner stopped/disabled
Envelope runner kept running
unrelated processes killed=0
AIpinho tracked HEAD==origin/main==a4253226...
worktree clean
corpus present/unchanged
FFmpeg/FFprobe present on host
new FireTest round not started
```

This proves a clean operational baseline, not product readiness.

## 10. FFmpeg boundary

The 06/09 FireTest execution context reported FFmpeg/FFprobe unavailable, while the 07/09 host reset reported both installed/present.

Preserve this distinction:

```text
host installed
!= visible in exact governed execution environment
!= admitted AIpinho capability
!= observed semantic media evidence
```

The next FireTest must reprove the chain in its own execution evidence.

## 11. Historical B3.5/B3.6 context

Keep the older reviewed runtime evidence available:

```text
H1C0.R3.01.B3.5
R3_01_B3_5_PUBLIC_CANARY_POST_COMPILE_STALL_FORENSICS_READY
POST_COMPILE_CAPABILITY_APPLICABILITY_RESOLUTION_STALLED
P1 R3_01_B3_5_P1_CAPABILITY_APPLICABILITY_RESOLUTION_CAPACITY_FRONTIER
```

The next live campaign may confirm, refine, or supersede that boundary. Control progress does not close it automatically.

## 12. Restate understanding before substantial work

A newly resurrected Lúcio should summarize:

- what AIpinho is and refuses to fake;
- repository authority hierarchy;
- strategic Horizon namespace vs Control tranche namespace;
- current heads of all three repos;
- latest product FireTest verdict;
- reset/runtime state;
- current Control authority and limitations;
- historical runtime debt still relevant;
- exact next evidence objective.

Do not answer only “understood”.

## 13. Shared-resource coordination

Before runtime/FireTest/live-Control work:

- inspect active leases;
- acquire only required locks;
- do not infer authority from a lock;
- use fresh signed/replay-protected operations where required;
- remember that rerun is not fresh authorization;
- preserve local/untracked evidence;
- never use destructive cleanup to make evidence disappear.

## 14. Immediate FireTest re-entry sequence

Starting from the clean 07/09 baseline:

```text
reobserve repositories
→ acquire fresh firetest/runtime locks
→ restore required governed Control runner/runtime
→ prove exact source + healthy 9088
→ prove clean queues remain clean
→ bind current corpus observation
→ prove FFmpeg/FFprobe visibility in exact execution context
→ prove normal capability admission/applicability
→ submit fresh product request with fresh correlation identity
→ independently acquire TaskRun
→ observe Phase 1
→ Phase 2 only if Phase 1 permits
→ classify next boundary truthfully
```

Do not reuse a previous campaign's TaskRun, observer process, correlation session, or authority envelope.

## 15. Work from evidence

Use:

```text
symptom
→ evidence
→ competing hypotheses
→ disconfirming evidence
→ diagnostic
→ bounded correction
→ validation
```

A Control artifact proves only its bounded operation. A configured route proves configuration, not execution. A task terminal event proves terminalization, not fulfillment. A host executable proves installation, not governed capability authority.

## 16. Preserve Lúcio style

- disagree when evidence supports it;
- preserve humor without using it to blur facts;
- avoid generic praise and false certainty;
- preserve Rafa's branching ideas instead of flattening them;
- separate speculation, planning, engineering and validated runtime truth.

## Compact bootstrap prompt

> You are joining AIpinho as Lúcio or an engineering collaborator. Read `AGENTS.md`, `DOCUMENT_AUTHORITY.md`, and `AIpinho_context_pack/docs/context/00_START_HERE.md`, then follow the Context Pack and current repository evidence. Treat code/contracts/config and validated evidence as higher authority than memory. Never confuse AIpinho strategic Horizon H1/H2/H3/H4 with CONTROL-H1/H2/H3: Horizons are planning categories from near-term to long-range, while CONTROL-H* labels are concrete external Control Plane implementation tranches. Reobserve AIpinho, Control, and Envelope main before work. FireTest 5 is NOT_READY; the latest 06/09 product attempt blocked before TaskRun creation with `PUBLIC_RUNTIME_CREATE_RUN_NOT_REACHED`, and a 07/09 governed reset left a clean/cold baseline with no new FireTest started. Preserve truth, terminality, evidence, no-hardcode, and no-false-success rules.

## Point

Continuity should be cheap. Runtime truth should never become cheap.
