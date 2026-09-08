# AIpinho Context Pack — START HERE

## Purpose

This directory preserves continuity across ChatGPT/Codex sessions, model changes, long pauses, engineering-agent handoffs, and work surfaces.

It is a structured memory/orientation layer. It is **not runtime authority** and it is not permission to override current code, contracts, configuration, Git state, or validated evidence.

## Read order

For engineering assistants, read `AGENTS.md` and `DOCUMENT_AUTHORITY.md` before the Context Pack.

1. `00_START_HERE.md`
2. `01_AIPINHO_PHILOSOPHY.md`
3. `02_LUCIO_RAFA_WORKING_RELATIONSHIP.md`
4. `03_ENGINEERING_WORKFLOW.md`
5. `04_PROMPT_STYLE.md`
6. `05_RUNTIME_ARCHITECTURE_MAP.md`
7. `06_FIRETEST5.md`
8. `07_H1_TO_H4_ROADMAP.md`
9. `08_WAVE_LEDGER.md`
10. `09_CURRENT_FRONTIER.md`
11. `10_IDEA_LAB.md`
12. `11_HANDOFF_PROTOCOL.md`
13. `current_state.json`

## Authority hierarchy

When sources disagree, prefer:

1. current production code and canonical contracts/config;
2. validated runtime/e2e evidence at the claimed scope;
3. current issue registers and wave reports;
4. architecture documents explicitly marked current/canonical;
5. current repository/context orientation documents;
6. generated snapshots such as `genome/`;
7. historical architecture/archaeology;
8. conversation-derived planning/context;
9. speculative ideas.

External Control Plane evidence is authoritative only for what the Control Plane requested, authenticated, executed, observed, or packaged. It never overrides AIpinho runtime truth.

## Mandatory naming distinction: Horizons vs Control tranches

The project currently has two unrelated naming families that both use H-numbers.

```text
AIpinho Horizon H1 / H2 / H3 / H4
    strategic maturity/planning horizons
    objectives and ideas grouped from near-term to long-range
    not patches, releases, wave IDs, or specific implementation updates

CONTROL-H1 / CONTROL-H2 / CONTROL-H3
    concrete external Control Plane implementation/validation tranches
    Lúcio Shell / account / delegated-agent / engineering-governance work
    separate authority and evidence namespace
```

Never abbreviate away the namespace when ambiguity is possible. Completing `CONTROL-H3` does not mean strategic `Horizon H3` is complete. See `07_H1_TO_H4_ROADMAP.md`.

## Repository roles and current observed heads — pre-documentation refresh, 2026-09-07

```text
AIpinho
  role: runtime/application truth
  observed main: a4253226d5af73ffa8eea6279943cce5915fb507

AIpinho-FireTest-Control
  role: external authentication/replay/governed engineering/execution authority
  observed main: dacd3e5afde981e077ef212b7c1072bfea80b8a7

AIpinho-Envelope-Requests
  role: unsigned request/intake transport to the local governed broker
  observed main: 8ff0632736a01b5faf27e53fcffd12ecbdc3cbca
```

These SHAs are a continuity snapshot. Reobserve live `main` before acting.

## Current Control Plane orientation

The old B1.0-D/E/F/G snapshots in earlier Context Pack versions are historical. Current external Control has progressed through:

```text
G3_BASELINE_VALIDATED
CONTROL-H1 through H1-E validated
CONTROL-H2 through H2-E validated
CONTROL-H3-A through H3-H accepted at their defined scopes
CONTROL-H3-I end-to-end authority compression live accepted and independently reproduced
CONTROL-H3-J progressive FireTest re-entry started
```

H3-J is deliberately progressive. It does not create unrestricted FireTest authority.

A fresh narrow J1 live smoke on 2026-09-05 successfully executed the admitted FireTest/CVL unit surface through `engineering.test.pytest`: 19 tests passed. Broad product FireTest remained a separate gate.

## Current FireTest checkpoint — 2026-09-07

The latest product-facing FireTest B attempt on 2026-09-06 did **not** produce success. The governed Control execution completed and returned truthful evidence, while the product path blocked before a TaskRun was created:

```text
Control run: 34059896495
operation: op_firetest5_b_clean_final_20260906T211500Z
product verdict: BLOCKED_PRE_TASK
reason: PUBLIC_RUNTIME_CREATE_RUN_NOT_REACHED
task_run_id: null
runtime terminal result: absent
SpeakerTruth safe_to_report_success: false
Phases 2-6: skipped_due_to_prior_block
```

That is a product/runtime block, not a reason to mark the green Control workflow as FireTest success.

The AIpinho `main` at `a4253226...` includes the live multi-endpoint FireTest observer that separates chat dispatch from TaskRun correlation/observation.

## Clean reset checkpoint — operator-supplied governed observation, 2026-09-07

After the 06/09 campaign, Codex reported a governed cleanup/reset:

```text
RESET_STATUS=CLEAN
TASK_RUNTIME active=0 pending=0 orphaned=0 leases=0
CHAT active=0 pending=0 orphaned=0
active locks/leases=0
hygiene preview candidates=0
AIpinho API/9088=OFFLINE / no listener
old Control runner=stopped/disabled
Envelope runner=kept running
unrelated processes killed=0
AIpinho HEAD=origin/main=a4253226...
worktree_clean=YES
corpus_ok=YES / corpus not modified
FFmpeg host presence=YES
FFprobe host presence=YES
new FireTest round started=NO
```

The historical long-running TaskRun and the 06/09 observer were terminalized as `cancelled`; their history/evidence was preserved. Expired stale approvals/grants remain audit residue, not active authority.

This reset means **operational hygiene is clean**, not that FireTest is ready.

## FFmpeg evidence boundary

Preserve this apparent contradiction instead of smoothing it away:

- the 06/09 governed FireTest execution observed `ffmpeg=false` and `ffprobe=false` in its execution context;
- the 07/09 reset observed FFmpeg and FFprobe present on the host.

Therefore:

```text
binary present on host
!= binary visible in exact governed execution environment
!= AIpinho capability admitted
!= semantic observation validated
```

The next campaign must reobserve executable visibility and capability admission in the exact execution/runtime context.

## Historical runtime frontier retained

B3.5 remains valid historical evidence:

```text
H1C0.R3.01.B3.5
R3_01_B3_5_PUBLIC_CANARY_POST_COMPILE_STALL_FORENSICS_READY
POST_COMPILE_CAPABILITY_APPLICABILITY_RESOLUTION_STALLED
P1: R3_01_B3_5_P1_CAPABILITY_APPLICABILITY_RESOLUTION_CAPACITY_FRONTIER
```

The B3.6 applicability/capacity question remains unresolved evidence debt. Progressive FireTest re-entry does not erase it; a new run may confirm, refine, or supersede that boundary with better evidence.

## Immediate operational posture

FireTest 5 remains `NOT_READY`. The next campaign should start from the clean baseline, acquire fresh coordination locks, start the required governed runner/runtime deliberately, verify exact source provenance, corpus and tool visibility, then run a fresh product request with new correlation identity. Phase 2 may proceed only if Phase 1 permits it.

## Context rules

Always separate:

- observed vs inferred;
- current vs historical;
- architecture vs aspiration;
- planning horizon vs implementation tranche;
- Control execution success vs AIpinho product success;
- host dependency presence vs governed capability availability;
- terminalization vs semantic fulfillment.

Memory is orientation. Evidence remains authority.
