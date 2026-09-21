# AIpinho Current State — 2026-09-18

## Authority note

This file is an orientation snapshot. Current production code, canonical configuration/contracts and validated runtime evidence remain authoritative.

## Repository baseline

- Repository: `sasandralean-prog/AIpinho`
- Branch: `main`
- Runtime consolidation implementation commit: `6126a73a9ddfc054fe527174fe4df16740b9d1e0`
- Semantic Sprints 0–9: `COMPLETE` and integrated into the canonical runtime.
- Runtime + roles consolidation: `COMPLETE / VALIDATED`.
- Canonical post-consolidation focused regression: `174 passed / 0 failed` after reboot.
- Sprint 0–9 dedicated branches/worktrees: retired after merge; residual evidence remains quarantined outside the tracked repository.

## Five canonical authorities

1. **Human operator** — grants authority, approvals and scope.
2. **Trusted dispatcher** — validates identity/operation/arguments/scope and invokes fixed capabilities.
3. **Local execution broker** — routes already-authorized operations to Git/tests/build/FireTest/AIpinho.
4. **AIpinho runtime** — owns meaning, intent, contract, planning, governed execution, evidence binding, validation, RuntimeTruth and SpeakerTruth ceiling.
5. **Evidence/result layer** — provides auditable outputs, diagnostics and validation evidence without inventing success.

The dispatcher/broker may not become a second semantic planner or orchestration runtime.

## Canonical runtime

```text
public ingress
  → CanonicalPublicChatService
  → SemanticIntentResolution / GovernanceLifecycle
  → OperationContract / Policy / Approval
  → TaskBootstrap + durable TaskRun
  → TaskRunPlanner / ExecutionPlanPromotion
  → TaskSemanticVocabulary
  → SemanticExecutionGraph
  → EdgeSemanticDemand
  → SupervisedExecutionLoop
  → TaskRunExecutor / GovernedTaskStepRunner
  → domain executors + TaskRuntime-bound RolePipeline children
  → RuntimeTimeline / artifacts / validation / TaskRunResult
  → SemanticOffer / Offer-Demand compatibility
  → N-way semantics / governed graph revision
  → SemanticCompletionTruth / SemanticTruthFacet
  → RuntimeTruthEngine
  → CanonicalOperationState
  → CanonicalSpeakerTruth
  → client output
```

Roles/models are subordinate components inside this runtime. `RuntimeContractsV2`, `PlannerV2`, and `RuntimeDispatcherV2` are compatibility/introspection, not a second execution plane.

## Latest FireTest 5 revalidation

Canonical summary: `reports/runtime_consolidation/runtime_consolidation_final_validation_20260915.md`.

```text
phase_1 = completed_with_limitations / RuntimeTruth partial
          PhaseOutcome satisfied_with_limitations
          safe_to_report_success = false
phase_2 = completed / RuntimeTruth completed
phase_3 = completed / RuntimeTruth completed
phase_4 = completed / RuntimeTruth completed
phase_5 = completed / RuntimeTruth completed
phase_6 = completed / RuntimeTruth completed
```

Across all six phases:

- RuntimeTimeline sequence gaps: `0`
- duplicate sequences: `0`
- `run_role_pipeline` executed: `6/6 TaskRuns`
- persisted supervisor consistency pass: `completed`, deterministic, `real_inference=false`
- Runtime Doctor: completed all phases, including former Phase 4/6 problem cases
- workspace mutations: `0`
- corpus mutations: `0`
- final runtime queue: clean

Phase 1 is intentionally not a success claim. `CanonicalOperationState=BLOCKED` prevents success/UI claims while `RuntimeTruth=partial`; edge-local downstream use may still be admitted only as `satisfied_with_limitations` when explicit use-safety is compatible.

## Bugs closed by the consolidation

- RuntimeTimeline event sequence allocation race / duplicate-gap failure.
- blocked/contradictory RuntimeTruth failing to constrain `PhaseOutcome` and downstream admission.
- large-run Runtime Doctor evidence rehydration/timeout path.
- specialized readonly artifact service owning a duplicate lifecycle/result/Truth path.
- planned `run_role_pipeline` appearing in the plan without executing in specialized artifact flows.
- role pipeline binding/authority ambiguity and deterministic supervisor inconsistency.
- root-role provenance tokenization suffix issue.

## Deferred

- Windows subprocess `cp1252` decoding failure observed in `.m4a`/media probing remains explicitly deferred.

## Genome / runtime map

- Genome: `genome/00_manifest.json` — version `2.0`, regenerated from the consolidated runtime.
- GitHub folder audit: `genome/reports/github_folder_audit_20260915.md`.
- Runtime map: `docs/architecture/CURRENT_RUNTIME_MAP_20260915.md`.
- Context map: `AIpinho_context_pack/docs/context/05_RUNTIME_ARCHITECTURE_MAP.md`.

## Active architecture wave — E2E New Runtime

Canonical execution plan: `e2enewruntimee.md`.

Wave status: `IN_PROGRESS`. `M1 - Canonical Mission Contract` through `M9 - Cross-Phase Truth and Mission Completion Contract` are CLOSED. Next sprint: `M10 - Fresh Manual E2E FireTest and Consolidation`.

The wave extends the single canonical TaskRuntime with frozen mission contracts, prompt-derived local resources, prompt-derived remote repository/branch resources, explicit human authority, unified capability/policy decisions, governed Git/network execution, mission staging, cross-TaskRun continuation and cross-phase completion truth.

Pre-wave diagnostic evidence was gathered on `fix/firetest5-mission-runtime-intentmap` at `cfba76ee094018f9680c0a63eda6378cb118a076`. That branch is evidence for the plan; it is not equivalent to code already canonized on `main`.

Sprint closure protocol: every sprint is complete only after validated merge to `main`, update of this file, update of `AIpinho_context_pack/docs/context/current_state.json`, and update of the sprint status board in `e2enewruntimee.md`.

M1 closure: implementation/main SHA `489ca3bd37eb8584b7b58d86526a203897965121`. The canonical TaskRuntime now freezes and persists a `MissionContract`/`MissionContractBinding` before planning, binds mission identity/hash through bootstrap and durable run indexes, and enforces monotonic child-contract narrowing. Validation: new mission-contract suite `10 passed`; broader runtime/semantic regression `92 passed / 1 failed`, with the single failure reproduced unchanged on baseline `630d454f` from an unregistered detached worktree. No project-specific resource, repository or FireTest rule was added.

M2 closure: implementation/main SHA `bb69739eb748472ebb36c359491bc4e7a895e24c`. Prompt-derived local workspaces/corpora are now frozen as permission-specific `MissionResourceScope` entries and enforced consistently by WorkspaceContext, TaskRunGuard, patch gates and the final Agent Tool Gateway. Static protected/forbidden/source_readonly policy remains stronger than prompt-derived mutable scope. Validation: dedicated M2 suite `10 passed`; semantic/resource/tool/patch regression `48 passed`; runtime/workspace regression `34 passed / 1 failed`, with the single failure reproduced on unchanged baseline `55e56a56` from an unregistered detached worktree. `compileall` and diff checks passed. No project-specific local resource registration or patch allowlist was added.

M3 closure: implementation/main SHA `3654d0e792f7fbe2c97aacd4f510f531c8e5b959`. Prompt-derived remote repositories are now frozen as credential-free, provider-aware `MissionResourceScope` entries with normalized repository identity, explicit allowed branches and operation permissions. The canonical remote gate enforces repository + branch + operation, negative repo scope, global host/scheme/secrets policy and destructive-operation denial; `git_push` additionally requires identity reobservation before later promotion execution. Validation: dedicated M3 suite `11 passed`; MissionContract/M2/M3 regression `31 passed`; semantic ingress `15 passed`; TaskRuntime `16 passed / 1 failed`, with the single failure matching the previously documented unregistered-worktree approval-test limitation. `compileall` and staged diff checks passed. No repository/host/project-specific production allowlist was added and no Git/network execution policy was relaxed.

M4 closure: implementation/main SHA `0fe414fb5196318e49eb660b5c5440b7dd135f11`. Semantic ingress now distinguishes requested capability from evidence-backed explicit human authority. `AuthorityGrantService` is the canonical grant evaluator and the legacy SessionGrant service is a compatibility facade over the same store/model. Mission grants are bound to source message/hash, mission, action/capability, local resources/paths and remote repository/branch scope; use-count, expiry and revocation are runtime behavior. TaskRunGuard and Agent Tool Gateway consume the same authority only to satisfy the human-consent facet and cannot override source_readonly/protected/global policy. Validation: dedicated M4 `11 passed`; grant/contract compatibility `28 passed`; gate/resource/remote/semantic regression `55 passed`; broader runtime/public regression `100 passed / 2 failed`, both reproduced unchanged on M3 baseline `77685f0b`. `compileall` and diff/hardcode checks passed.


M5 closure: implementation/main SHA `75baa3551a1520ebc62ba985dbedbf3a1eae71f6`. `CanonicalPolicyDecision` is now the sole execution-authority verdict for TaskRunGuard, Agent Tool Gateway, WriteCapabilityEnvelope and GovernedToolExecution; specialized policies remain facet/evidence producers. Mission authority satisfies only matching ASK facets and cannot override hard resource/global denies. GovernedToolExecution resolves `task_run_id` back to the canonical MissionContract for dynamic resources, while legacy callers use the central workspace-role registry; its duplicated project allowlist was removed. Generic `git_write_shell` and `network_shell` remain fail-closed pending M6 granular classification, while structured HTTP web requests remain governed. Validation: C.1 `9/9` focused and `26/26` regression; C.2 `4/4` focused and `8/8` cross-gate; final policy/authority/Gateway/envelope/executor `55/55`; TaskRuntime/resources `55 passed / 1 failed`, the same known unregistered-worktree baseline failure. `compileall`, diff and hardcode checks passed.


M6 closure: implementation/main SHA `398f875e1485b878bf8bc7d242e53549c47c3659`. Git is now capability-classified into local read, network read, worktree write, commit, push, destructive and unknown classes; destructive/unknown paths remain fail-closed. GovernedToolExecution reobserves remote identity and branch JIT, composes remote scope plus human authority, executes with `shell=False`, and requires refreshed remote HEAD evidence after push. Public ingress, TaskRunGuard and Agent Tool Gateway propagate the same granular capability; the Gateway reclassifies actual argv/command and delegates non-read Git to GovernedToolExecution instead of trusting caller shell labels or creating a second Git runtime. Validation: controlled real-Git fixture `6/6`; Git/policy/authority/Gateway regression `86/86`; resources/public `44/44`; TaskRuntime/bootstrap `21 passed / 1 failed`, the same known unregistered-worktree baseline failure. `compileall`, diff and production hardcode checks passed. Generic `network_shell` remains fail-closed while structured HTTP and classified Git network operations remain governed.

M7 closure: implementation/main SHA `725f47b789c6c356aa63b2126461d4c59c45fb4c`. `mission_staging` is now a mission-scoped derived local resource created only from a frozen authorized remote repository under the global safe staging root. Materialization uses the canonical TaskRuntime identity and GovernedToolExecution for governed directory creation plus classified Git clone/fetch/`pull --ff-only`; origin, branch and remote HEAD are reobserved, and the staging workspace is exposed through the normal WorkspaceContext/resource gates without permanent registration. A controlled real-Git promotion proved clone/sync, intentional change, governed commit and governed push while a separate `source_readonly` corpus and `workspace_registry.yaml` remained hash-identical. Terminal parent/child lifecycle hard-denies further staging use without rewriting already-proven push truth; physical cleanup remains subordinate to the global `delete_files` deny and is therefore a cleanup limitation, not a success rollback. Validation: M7-A `51/51`; M7-B.1 `25/25`; M7-B.2 `60/60`; focused M7-C `8/8`; final cross-sprint regression `107/107`; `compileall`, diff and production hardcode checks passed.

M8 closure: implementation/main SHA `446d22349850`. Terminal `end_to_end_governed` TaskRuns can now cause the canonical `TaskRunPlanner` to propose the next bounded phase from frozen structured mission semantics and automatically materialize a canonical child TaskRun through the existing TaskRuntime. `MissionContract.semantic_context` freezes continuation semantics without retaining/reparsing `raw_prompt`; planner candidates remain descriptive and cannot supply policy or authority. Mission authority permissions are separated from internal runtime/profile capabilities so a child phase consumes only its required runtime subset without erasing mission-wide authority needed later. Child resources remain monotonic, policy is recomputed canonically, PhaseOutcome/dependency truth gates the handoff, and configurable depth/phase-lineage/history guards fail closed against loops. Validation: focused MissionContract/M8 `38/38`; cross-sprint M4-M8 `134/134`; broader runtime/public `65 passed / 1 failed`, with the sole failure reproduced identically on clean baseline `4b14e2f8`; `compileall`, diff and production hardcode/`raw_prompt` scans passed.

M9 closure: implementation SHA `19beb80d866018c5b0ee26547e2577c2ce775992`. Mission-wide completion now projects durable TaskRun/PhaseOutcome evidence, persists accepted model-assisted requirement/evidence bindings only after deterministic compilation, and applies the resulting MissionCompletionFacet as a ceiling inside the existing RuntimeTruth/SpeakerTruth chain. Missing mission evidence can no longer be upgraded by a locally completed phase; intermediate or blocked continuation cannot publish final mission success. Restart rehydrates the persisted proposal and recompiles it against canonical evidence without model reinvocation, reproducing the same RuntimeTruth. Validation: C.1 `29/29`; C.2 focused `76/76`; restart/ceiling `9/9`; cross-sprint M4-M9 `172/172`; broader runtime/public `69 passed / 1 failed`, with the sole failure the previously documented `test_service_waits_for_approval_when_policy_requires_apply_patch` unregistered-worktree fixture. `compileall`, diff and production hardcode/`raw_prompt` scans passed.

## Current engineering frontier

There is no open P0/P1 from the completed FireTest 5 consolidation wave. The E2E New Runtime wave is active and extends the same canonical TaskRuntime; no parallel planner, dispatcher, role runtime or truth authority is authorized.

Immediate frontier: continue Sprint M10 from `e2enewruntimee.md`. M10-A.17 implementation/main SHA `0a803b6d6b36c95065d11b2b70f96992439e089e` closes the governed semantic-reasoner truncation/contract frontier, but its first recorded backend restart was later proven to be a false-positive supervisor result: a stale PID file caused stop to return success without touching the real listener, start returned success because that same listener was still healthy, and `BackendControlService` accepted healthy-to-healthy without observing an actual stop. M10-A.18 implementation SHAs `a266b732fbf2cd8c8e98f31359c362919d4c8300` and `5833fccdbff9100a50076b6b0ade810b3855fe80` repair restart truth by falling back from stale PID metadata to the active listener, requiring an observed `down` state between stop and start, waiting for the port to close, and capturing canonical script output through temporary files so a spawned uvicorn cannot keep supervisor pipes open. Verified restart `backend_restart_1789957290698` transitioned PID `24636` to PID `21432`, recorded `healthy -> down -> healthy`, returned `accepted` with no warnings in 13.21 s, created the canonical PID file, and left the backend online on the current main. The manual FireTest submitted before A.18 completed was therefore executed by the old PID and is not valid post-A.17 evidence. A current read-only replay exposes the next fail-closed frontier: continuation selection now stops at `SEMANTIC_REASONER_ROLE_BUDGET_EXCEEDED`; its planner payload is 11,237 chars, of which `continuation_options` contributes 7,367, against the semantic-interpreter low-role budget of 6,000. This is the diagnostic entry point for the next M10 correction. Mission-level completion truth remains evidence-bound across canonical TaskRuns and subordinate to RuntimeTruth/SpeakerTruth. The deferred Windows subprocess cp1252/.m4a reader issue remains separate unless a later mission explicitly scopes it.

## Invariants

- `MODEL != AUTHORITY`.
- Unknown is fail-closed.
- Execution completion != semantic admission.
- Producer completion does not authorize consumer usage.
- Demand is edge-local; Offer/Demand compatibility is evaluated per edge.
- Historical graph truth cannot authorize a revised active graph.
- `run_completed != safe success`.
- Doctor diagnoses; RuntimeTruth governs safe operational claims.
- FireTest is regression evidence, not runtime configuration.
- Requested capability != explicit human authority.
- Explicit mission authority satisfies human consent only; stronger resource/global policy still wins.

- Remote scope is repository + branch + operation; missing branch scope is fail-closed.
- Remote promotion requires repository identity reobservation before promotion execution.
- Caller-provided shell category is not authority; command/argv is reclassified at the execution gate.
- Mission staging is derived only from an authorized frozen remote resource and never from prompt-declared local staging metadata.
- Staging local-resource metadata never inherits human authority; Git authority remains bound to the frozen mission remote scope.
- Terminal parent/child TaskRun lifecycle expires staging authority without rewriting previously proven promotion truth.
