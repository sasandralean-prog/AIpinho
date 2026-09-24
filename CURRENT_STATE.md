# AIpinho Current State — 2026-09-22

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

Immediate frontier: continue Sprint M10 from `e2enewruntimee.md`. M10-A.17 (`0a803b6d6b36c95065d11b2b70f96992439e089e`) closed governed semantic-reasoner truncation/contract failures; M10-A.18 (`a266b732`, `5833fccd`) made backend restart truth require a real `healthy -> down -> healthy` transition. M10-A.19 implementation/main SHA `57833beb7e54862956b67e91c0927c0f04d8f91f` bounds continuation semantic payloads, makes use-safety applicability action-registry-driven, and replays the real `project_analysis` dependency with only `safe_for_downstream_static_analysis=[true]`; expanded regression is `130/130`. M10-A.20 implementation SHA `93b2cf1360db785329217f697145d41cfaf64636` separates requested capability, explicit human authority, and resource permission envelopes. Resource permissions are no longer promoted into human-requested capabilities; negative/incidental mentions no longer fabricate artifact/write demand; `criacao/alteracao de testes` resolves to `create_file`; diagnostic/preflight authority resolves to governed `shell_readonly`; and remote scope recognizes clean-copy/fetch/safe-fast-forward as `git_clone`, `git_fetch`, `git_pull_ff` without auto-authorizing them. Focused A.20 regressions are `45/45`, `76/76`, and `72/72`. A.20 was promoted by fast-forward with zero overlap against the canonical dirty state; the two pre-existing tracked hashes and all 153 untracked files were preserved. Verified restart `backend_restart_1789986053376` stopped PID `23916`, observed `stop_health=down`, started PID `13916`, and ended `healthy` with no warnings; live `/api/v1/runtime/health` is `ok` and tracked canonical HEAD equals `origin/main`. The remaining future-side-effect authority gap is intentionally fail-closed and exactly `git_clone`, `git_fetch`, `git_pull_ff`, because those operations are requested and scoped but not named by the explicit human authorization clause. The next validation step is a fresh manual end-to-end mission through the normal interface on this restarted code. Mission-level completion truth remains evidence-bound across canonical TaskRuns and subordinate to RuntimeTruth/SpeakerTruth. The deferred Windows subprocess cp1252/.m4a reader issue remains separate unless a later mission explicitly scopes it.

M10-A.21 implementation/main SHA `ef8011e86e27e230355b168ec69126a27ba66c38` closes the intra-workflow partial-context semantic truth gap. `build_file_context` now emits an explicit governed `semantic_outcome`: complete context is fully safe for downstream static analysis, validated partial context is `true_with_limitations`, and blocked/failed context is unsafe. `WorkflowPhase` persists that producer-local semantic outcome and `WorkflowRuntimeService` binds it into the next `PhaseDependencySnapshot` instead of evaluating with an empty use-safety map. `project_analysis` declares through ActionRegistry that `safe_for_downstream_static_analysis` accepts `[true, true_with_limitations]`; the model may determine whether that dimension is required but cannot arbitrarily narrow the action-owned acceptable-state contract. Focused regression is `52/52`, expanded workflow/offer/demand/continuation regression is `118/118`, and the exact persisted FireTest run replay (deep copy only, no store mutation) changes the phase-4 -> phase-5 boundary from `PHASE_DEPENDENCY_REQUIRED_USE_SAFETY_UNKNOWN` to `ADMITTED_WITH_CONSTRAINTS`, preserving all four file-context limitations as mandatory disclosures. Verified restart `backend_restart_1789989093550` records `healthy -> down -> healthy`, transitions PID `13916 -> 19512`, and leaves live runtime health `ok`.

M10-A.22 implementation/main SHA `7811ebdf1d55ac6cbe5ed9cec49f364cd673ffb0` closes the next producer/consumer truth gap: `project_analysis` now emits governed `safe_for_user_report` semantics (`true`, `true_with_limitations`, or `false`) together with limitations, missing truth and mandatory disclosures. The normal-interface FireTest `task_run_51f7a878192d41e7bb1aa88b8baec2f3` proves the real phase-5 -> phase-6 boundary: partial analysis persisted `safe_for_user_report=true_with_limitations`, dependency evaluation returned `ADMITTED_WITH_CONSTRAINTS`, and `project_report` executed as partial instead of being blocked. Focused A.22/A.23 checks are `5/5`; the exact workflow/dependency/offer-demand/continuation regression is `127 passed / 1 deselected`, with the deselected legacy optional-failure assertion reproduced unchanged on the A.21 baseline. `compileall`, TaskRun event-policy load, diff check and production hardcode scan are clean.

M10-A.23 is implemented in the same main SHA `7811ebdf1d55ac6cbe5ed9cec49f364cd673ffb0` and hardens optional workflow semantics. When governed dependency evidence is unavailable for a non-required step, `SupervisedExecutionLoop` records `step_skipped`, preserves the dependency reasons as warnings, updates execution graph/workflow/execution context/audit and continues; required steps remain fail-closed and still block. `WorkflowRuntimeService` already treats `skipped` as a successful terminal phase state, so this does not create a bypass or second lifecycle. The focused skip test passes; the latest FireTest did not need this branch because its optional/runtime phases completed normally, so A.23 has contract/enforcement/regression proof but no fresh E2E activation of the skip condition.

The first fresh mission on A.22/A.23-loaded code completed the full readonly discovery workflow through `project_report`, `role_pipeline_run` and `compose_result`, then blocked cross-TaskRun continuation at `SEMANTIC_REASONER_ROLE_BUDGET_EXCEEDED` without materializing a child TaskRun or expanding write authority.

M10-A.24 through M10-A.26 share implementation SHA `dabb0ed24a8c485f3a7074bafa85ad253b81e621` (`fix(runtime): consolidate semantic reasoning budgets`). A.24 separates phase-local operation identity from frozen mission-level semantics and projects only bounded cognitive fields to `SemanticDemandInterpreterService`; the exact failing nested prompt drops from 6,382 to 4,572 chars under the unchanged 6,000-char low-role budget, with `project_generation` consistent in canonical and model-facing identity. A real read-only `TaskRunPlanner.plan_continuation()` replay over `task_run_51f7a878192d41e7bb1aa88b8baec2f3` now returns `MISSION_CONTINUATION_CANDIDATE_PLANNED`.

A.25 makes registered action semantic scope explicit and removes model inference where deterministic action/capability semantics are sufficient. `write_files`, `run_command`, `run_tests`, `validate_runtime`, and `compose_result` are deterministic dependency modes with empty model-owned use-safety scope; project-generation continuation now compiles only `safe_for_destructive_action=[true]` from deterministic side-effect semantics and records zero semantic-reasoner requirement provenance. PromptAssembly no longer counts packed context twice after it is rendered into messages. A.26 additionally fits packed context against the actual final prompt envelope, preserving safety/role/output-contract/user messages; the adversarial case that previously produced 20,660/20,000 now fits exactly 20,000/20,000 by truncating the lowest-priority final context item instead of emitting `prompt_budget_exceeded`.

A.24-A.26 validation is green: focused semantic/action/prompt budget regression `52/52`; expanded continuation/runtime/semantic set `131 passed / 3 failed`, with all three failures reproduced unchanged on clean baseline `f96767b6` and therefore no new regression; `compileall`, `git diff --check`, ActionRegistry load and production/config hardcode scan are clean.

Verified post-A.26 restart `backend_restart_1790060436295` is accepted with no warnings. Supervisor trace `supervisor_trace_55b34fa9e39f4645946e992210671df2` records `pre_health=healthy`, stop of PID `17344`, `stop_health=down`, start of PID `17848`, and `post_health=healthy`; the PID file contains `17848` and live `/api/v1/runtime/health` returns `status=ok`.

M10-A.27 implementation SHA `2c916e90` (`fix(runtime): bound mission completion evidence binding`) closes the missing binder-role frontier without creating a second truth authority. `mission_completion_evidence_binder` is now a dedicated subordinate role with no tools, execution, write, patch, approval or truth authority; it binds to `qwen2_5_7b_instruct_q5_k_m` under the medium role budget and has explicit prompt/output contracts. Real-inference opt-in is exposed through a dedicated `semantic_reasoner_controlled_inference` gate allowlist rather than by adding the binder to generic chat or role-pipeline authority.

The binder now reasons over one frozen requirement at a time and a bounded evidence subset. Policy limits are 8 evidence items per batch, 9,000 model-prompt chars, 12 total reasoner calls, 4 candidate bindings per batch, and 900 output tokens. Mission/evidence authority hashes stay deterministic and are not sent to the model. If one evidence item cannot fit the batch budget, or the complete Cartesian coverage would require more than 12 calls, proposal generation fails closed before model invocation; evidence is never silently truncated. Batch outputs may reference only the exact current requirement, evidence refs and producer TaskRun ids, and the existing `MissionCompletionBindingCompiler` remains the sole component that validates identities, confidence, RuntimeTruth/dependency/use-safety and derives requirement satisfaction.

Real A.27 replay on a synthetic M9-shaped snapshot with `validated_change` and `tests_pass` now performs two governed Qwen2.5 7B calls, both with `real_inference=true` and `evaluation_status=accepted`. The proposal is `candidate / MISSION_COMPLETION_BINDING_CANDIDATE_PROPOSED`; deterministic compilation returns `compiled / MISSION_COMPLETION_BINDINGS_COMPILED`. The final replay binds `tests_pass` only to `evidence:tests`, while `validated_change` is supported by the patch plus validation evidence; both compile to `satisfied`. Provider provenance retained a non-blocking `invalid_json:Expecting value` warning even though the governed candidate was accepted and parsed successfully.

A.27 validation: focused binder/gate/restart checks `17/17`; full M8/M9/A.24-A.27 cross-regression `152/152`; generic role-policy/output/prompt regression `19 passed / 1 failed`, with the sole `patch_planner` runtime-limit assertion reproduced identically on baseline `f4cfcba8`. `compileall`, `git diff --check`, role/config loading, model routing and production/config hardcode scan are clean. The prior fresh FireTest still does not activate mission-completion binding because its frozen mission contains zero completion/validation requirements; fresh normal-interface evidence for the binder therefore remains a separate post-restart validation target.

Verified post-A.27 restart `backend_restart_1790070634718` returned `accepted` with no warnings. Supervisor trace `supervisor_trace_e67f31ed4de146b3b5094696859a0049` proves `healthy -> down -> healthy`, stopping PID `17848` with port 9088 closed and starting PID `380`; the PID file contains `380`, live `/api/v1/runtime/health` returns `status=ok`, and backend-control status is `online/healthy` with this restart as the latest restart id.


M10-A.28 through M10-A.30 establish the governed mission-repair/completion ingress chain. A.28 (`9468faeb`) adds a bounded read-only evidence-repair continuation lane without weakening write/destructive gates. A.29 (`a7e8e5c4`) preserves extensible `use_safety`, including `safe_for_downstream_static_analysis`, across PhaseOutcome projection. A.30 (`522efd50`) freezes explicit terminal mission completion/validation criteria from exact prompt evidence; the live FireTest mission freezes `codigo_mudado`, `melhoria_pipeline`, `regressao_validada`, and `push_confirmado`, so local phase completion cannot falsely terminate the mission. Follow-up continuation hardening `fd24f7f2` bounds evidence-repair cognition and `f39f5ddc` reuses already-governed producer safety for generic read-only evidence repair.

M10-A.30.a implementation/main SHA `4f0e9aea34b78f66e2d017ee8180274c4cac0cdd` (`fix(runtime): separate workflow order from semantic dependencies`) closes the workflow-order/semantic-authority conflation exposed by the evidence-repair child. `WorkflowRuntimeService` still materializes adjacent `implicit_sequence` edges for scheduling/status/validation, but only canonical `CanonicalExecutionStep.depends_on` edges become `explicit_plan_dependency` and invoke semantic demand compilation, PhaseDependencyEvaluation and admission. Explicit non-adjacent dependencies are materialized; explicit semantic dependencies remain fail-closed when required `use_safety` is absent. The exact previously blocked child replay changes `validate_workspace -> project_analysis` from `PHASE_DEPENDENCY_REQUIRED_USE_SAFETY_UNKNOWN` to an ordinary implicit sequence and admits `project_analysis` without fabricating safety truth. Focused final regression is `114/114`; the exploratory wider set is `88 passed / 2 failed`, and both failures reproduce identically on clean baseline `f39f5ddc`. `compileall` and `git diff --check` are clean.

Post-A.30.a restart `backend_restart_1790116962318` is accepted with no warnings and records `healthy -> down -> healthy`. Fresh normal-interface FireTest session `chat_4bf2354b600a4bad9b69e6779cd96fa0` creates parent `task_run_146a956f17e646ad9d3ddeddfe5f058c`, then evidence-repair children `task_run_4434a6126fd2439ca111c28d17576fcd` and `task_run_7fe4d294878448d091e6b78577c0d663`. The first child executes `phase_003_execute_readonly_artifact_analysis` as `completed/passed` and completes its workflow, proving the A.30.a boundary removed. The second child also completes its readonly workflow and then deterministically blocks mission continuation at `MISSION_CONTINUATION_PREMATURE_COMPLETE`: the model proposed `action=complete` while frozen mission effects `build_execution`, `runtime_execution`, and `workspace_mutation` remain unsatisfied. This is the next genuine M10 frontier; the guard correctly prevents false completion and no write authority was invented.

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


## M10-B.1 — Governed context handoff closure (2026-09-24)

M10-B.1 is implemented and promoted on canonical `main` at `8fa566c8db9566688fd6dd018da6810c55f739b0` (`fix(runtime): deduplicate admitted context evidence`). The checkpoint closes the M10-A.31 diagnosis that admitted evidence could be valid at dependency admission yet disappear before patch planning / role cognition.

The runtime now materializes admitted phase evidence into a canonical context plan, binds that plan to child TaskRuns, resolves it through a single context-plan runtime facade, and feeds the same governed evidence into patch planning and role prompt assembly. Canonical artifact logical paths and runtime provenance survive the handoff. Required context that cannot be resolved or admitted fails closed rather than silently degrading.

The repair also removes competing context-plan storage paths, validates canonical storage identifiers without overfitting their representation, and deduplicates admitted evidence before prompt assembly. No model gains authority from the context handoff; context is evidence transport, while policy, mission authority, use-safety and RuntimeTruth remain separate authorities.

Branch `agent/lucio/m10-b-context-handoff` and `main` are aligned at the same SHA. The implementation wave from diagnostic `4e8d3614` to `8fa566c8` changes 14 files (+1496/-99), including a dedicated `test_m10b_context_handoff.py` regression surface. Fresh normal-interface E2E validation remains the next evidence target; this checkpoint does not claim that proof before it is observed.
