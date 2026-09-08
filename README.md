# AIpinho

AIpinho is a local, experimental, governed AI runtime whose central goal is to turn language into governed work without pretending to know, execute, validate, or complete more than the system actually has.

Core chain:

```text
language
→ meaning
→ intention
→ contract
→ plan / intermediate representation
→ governed execution
→ evidence
→ validation
→ completion
→ SpeakerTruth
→ user-facing operational truth
```

## Current status — 2026-09-07

FireTest 5 remains:

```text
NOT_READY
```

The latest product-facing FireTest attempt was **not** a success. On 2026-09-06, the governed Control operation completed and packaged evidence, while the AIpinho product path blocked before a TaskRun was created:

```text
Control run: 34059896495
operation: op_firetest5_b_clean_final_20260906T211500Z
product verdict: BLOCKED_PRE_TASK
reason: PUBLIC_RUNTIME_CREATE_RUN_NOT_REACHED
task_run_id: null
SpeakerTruth.safe_to_report_success: false
Phases 2-6: skipped_due_to_prior_block
```

A clean governed reset followed on 2026-09-07. The reported baseline is cold and hygienic: no active/pending/orphaned runtime/chat work, no active leases, zero hygiene candidates, the old long-running task and previous observer terminalized as `cancelled`, AIpinho API/port 9088 offline, the old Control runner stopped/disabled, Envelope intake retained, corpus present/unmodified, tracked AIpinho clean, and no new FireTest round started.

`RESET_STATUS=CLEAN` means **operational hygiene is clean**. It does not mean FireTest is ready.

## Repository snapshot before this documentation refresh

```text
AIpinho
  main a4253226d5af73ffa8eea6279943cce5915fb507

AIpinho-FireTest-Control
  main dacd3e5afde981e077ef212b7c1072bfea80b8a7

AIpinho-Envelope-Requests
  main 8ff0632736a01b5faf27e53fcffd12ecbdc3cbca
```

These SHAs are continuity anchors only. Reobserve live repositories before acting.

## Three repository roles

### AIpinho

Runtime/application source of truth. Current code, canonical contracts/config, validated runtime evidence, validation/completion, and SpeakerTruth own product truth.

### AIpinho-FireTest-Control

Separate external governed operations/engineering layer. It owns authentication/replay, local broker integration, semantic engineering authority, Script Catalog binding, launcher/bootstrap execution, evidence/lifecycle, provider/account context, delegated-agent authority, and CONTROL-H3 engineering governance.

Current Control progression:

```text
G3_BASELINE_VALIDATED
CONTROL-H1 through H1-E validated
CONTROL-H2 through H2-E validated
CONTROL-H3-A through H3-H accepted at defined scopes
CONTROL-H3-I end-to-end authority compression live accepted and independently reproduced
CONTROL-H3-J progressive FireTest re-entry started
```

H3-J1 has fresh narrow unit-level FireTest/CVL live proof: Control run `33933759448` executed `tests/unit/test_cognitive_validation_laboratory_service.py` through `engineering.test.pytest` and returned `19 passed in 0.51s`.

That narrow admission is not broad FireTest success.

### AIpinho-Envelope-Requests

Unsigned request/intake transport into the local governed broker. It is never signing authority. GitHub/request text does not become execution authority merely because a request exists.

## Important naming rule: Horizons are not Control H-tranches

AIpinho uses `H1`, `H2`, `H3`, and `H4` as **strategic maturity Horizons** in the roadmap. They categorize objectives and ideas from near-term to long-range:

```text
Horizon H1 -> near-term foundational reliability/evidence maturation
Horizon H2 -> medium-term tool intelligence/operations
Horizon H3 -> medium-to-long-term agentic collaboration/initiative
Horizon H4 -> long-range exploratory evolution
```

They are **not patches, releases, or specific implementation updates**.

Do not confuse them with:

```text
CONTROL-H1
CONTROL-H2
CONTROL-H3
```

Those names belong to concrete implementation/validation tranches in `AIpinho-FireTest-Control` / Lúcio Shell. Completing `CONTROL-H3` does not mean strategic `Horizon H3` is complete. See `AIpinho_context_pack/docs/context/07_H1_TO_H4_ROADMAP.md`.

## Current FireTest tooling

AIpinho `main` at `a4253226...` contains the live multi-endpoint observer merged through PR #8. Its important protocol correction is:

```text
chat dispatch
!= synchronous TaskRun identity

chat dispatch
→ correlation/session identity
→ independent TaskRun acquisition
→ multi-endpoint read-only observation
→ terminal/product verdict
```

This prevents the observer from assuming a `task_run_id` must be returned directly by chat.

## FFmpeg / FFprobe boundary

Two pieces of evidence currently coexist:

```text
2026-09-06 FireTest execution context:
  ffmpeg=false
  ffprobe=false

2026-09-07 host reset:
  ffmpeg_present=YES
  ffprobe_present=YES
```

The binaries were reported as already installed; reset did not install or modify them.

Correct interpretation:

```text
host installed
!= visible in exact governed execution context
!= AIpinho capability admitted
!= governed observation executed
!= semantic media Truth
```

The next campaign must reprove executable visibility and normal capability admission/applicability in its exact environment. Do not hard-code an executable path just to make the scenario pass.

## Corpus

The current host orientation remains approximately:

```text
D:\Rafa\músicas
```

The 2026-09-07 reset reported corpus paths present, `corpus_ok=YES`, and no corpus mutation by cleanup.

The corpus deliberately contains fake `.m4a` files. Extension, filename, and path are locator/routing context, not semantic media authority.

## Historical B3.5/B3.6 evidence

The reviewed B3.5 forensic slice remains valid history:

```text
H1C0.R3.01.B3.5
R3_01_B3_5_PUBLIC_CANARY_POST_COMPILE_STALL_FORENSICS_READY
POST_COMPILE_CAPABILITY_APPLICABILITY_RESOLUTION_STALLED
```

Key evidence included two execute-observer tasks expanding to 10,000 target entity refs, 9,144 completed applicability decisions, 9,143 inapplicable outcomes, zero groups, zero physical probes, and roughly 120 seconds elapsed.

The associated structural P1 remains evidence debt until newer runtime evidence closes or supersedes it:

```text
R3_01_B3_5_P1_CAPABILITY_APPLICABILITY_RESOLUTION_CAPACITY_FRONTIER
```

Progressive FireTest re-entry does not erase this history.

## Readiness-latency corrective

A separate B0.4.1 investigation proved that public readiness endpoints were slow because `PublicRuntimeAPI()` eagerly constructed heavyweight runtime dependencies per request. The corrective commit `d41a7bae664f718fd615c222864db7eeeecb67cf` introduced lazy dependency construction and was live-validated without increasing readiness timeout.

Current `main` descends from that corrective. Therefore the API being `OFFLINE` in the reset checkpoint means the runtime is deliberately stopped, not that the old readiness-latency defect is automatically back.

## Next FireTest campaign

The next campaign should start fresh from the clean baseline:

```text
reobserve repository heads
→ acquire fresh firetest/runtime coordination locks
→ restore required governed Control runner/runtime
→ prove exact source + healthy 9088 state
→ confirm clean queue/chat state
→ bind current corpus observation
→ prove FFmpeg/FFprobe visibility in exact execution context
→ prove normal AIpinho capability admission/applicability
→ submit fresh product request with fresh correlation identity
→ independently acquire TaskRun
→ observe Phase 1 truth
→ Phase 2 only if Phase 1 permits
→ classify the next architecture boundary honestly
```

The goal is diagnostic evidence, not a ceremonial `READY` verdict.

## Governing principles

- Do not invent.
- Do not hide failures.
- No execution without contract.
- No validation without evidence.
- No success without SpeakerTruth.
- Candidate is not Truth.
- Derived is not observed.
- Unknown is not false.
- Artifact existence is not semantic success.
- Result existence is not completion.
- Path/filename/extension are not semantic Truth.
- Specific reason beats generic timeout.
- Accepted work must terminalize explicitly.
- A green external Control workflow is not automatically AIpinho product success.
- Block honestly rather than manufacture success.

> Bloqueio honesto é melhor que sucesso falso.

## Repository map

- `src/` — production Python package.
- `tests/` — unit/integration/workflow/security/regression tests.
- `config/` — runtime, model, policy, validation and governance configuration.
- `apps/` — launcher/mobile/client surfaces.
- `scripts/` — operational helpers.
- `reports/` — bounded engineering/runtime evidence.
- `AIpinho_context_pack/` — continuity/context layer.
- `AGENTS.md`, `.agents/skills/`, `docs/engineering_agents/`, `replit.md`, `.github/agents/` — engineering-agent infrastructure working **on** AIpinho.
- `config/agents/`, `src/aipinho/services/agents/` — governed runtime-agent namespaces **in** AIpinho.
- `archaeology/` — historical rationale/evidence orientation.
- `genome/` — generated architecture/design-DNA snapshots.

## Context and handoff

Canonical continuity entrypoint:

```text
AIpinho_context_pack/docs/context/00_START_HERE.md
```

Current pack version:

```text
v0.4.2 — 2026-09-07 cross-repository / pre-FireTest reset reconciliation
```

Context is not runtime authority. Current code/config/evidence win.
