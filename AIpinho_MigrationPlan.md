# AIpinho - Migration Plan

Status: MIGRATION_PLAN_STARTED

## Wave 1 - SemanticIntentResolution

- Inventory current chat/operation/session diagnostic/permission parsers.
- Select canonical semantic resolver.
- Convert old routers into adapters.
- Tests: readonly prompts, project bootstrap, permission grants, diagnostics, approval commands.

Implementation status: IN_PROGRESS_CANONICAL_ENTRYPOINT_CREATED

Implemented in this wave:

- Added `SemanticIntentResolutionService` as the prompt-level semantic authority.
- `GovernanceLifecycleService` now resolves intent through `SemanticIntentResolutionService`.
- `ChatPermissionGrantService` now accepts permission grants only when semantic resolution classifies the text as `permission_grant_request`.
- `ChatOperationRouterService` now consumes semantic precedence for explicit product planning, workspace permission list, and governed shell requests while preserving existing specialized compatibility contracts.
- Added a non-route `aipinho.api.routers.chat_router` compatibility shim for removed legacy helper imports. It does not register endpoints and must not be added to `ROUTERS`.

Temporary adapters remaining:

- `CanonicalIntentRouter` remains as the deterministic signal collector behind `SemanticIntentResolutionService`.
- `ChatOperationRouterService` still contains specialized legacy operation translation for artifact, report, workspace metadata, follow-up, sandbox, and project-specific compatibility cases.
- Legacy tests expecting approval creation without complete executable context must be migrated to the current safety contract instead of weakening approval gates.

## Wave 2 - EffectivePolicyDecision

- Inventory policy kernel, permission resolver, grants, config change, sandbox guards.
- Create one decision object and one resolver entrypoint.
- Convert old policy calls into adapters.
- Tests: allowed, ask, denied, blocked, missing plan, session grant, permanent config request.

Implementation status: IN_PROGRESS_CANONICAL_ENTRYPOINT_CREATED

Implemented in this wave:

- Added `EffectivePolicyDecisionService` as the canonical permission decision boundary for lifecycle/runtime policy decisions.
- `GovernanceLifecycleService` now consumes `EffectivePolicyDecisionService` instead of instantiating `CanonicalPolicyService` directly.
- `CanonicalPolicyService` remains as the internal normalizer/resolver used by the effective decision service, not as the top-level lifecycle authority.
- Invalid, expired, and stale upstream policy vocabulary now blocks deterministically instead of falling through to an implicit `allowed` default.
- Legacy `PolicyDecision` objects from `PolicyKernelService` can now be adapted into `CanonicalPolicyDecision` via `EffectivePolicyDecisionService.from_policy_decision`.

Temporary adapters remaining:

- `PolicyKernelService` remains active for legacy public policy endpoints, task draft services, tool safety, and chat previews.
- `EffectivePolicyBuilder` remains the restrictive policy builder behind `PolicyKernelService`; it is not yet the canonical runtime decision boundary.
- `MultiAgentPolicyKernelService` remains outside this wave and must be folded after core policy semantics stabilize.
- `safe_to_execute` still appears in several legacy preview/result schemas and must be migrated to canonical policy + runtime execution state.

## Wave 3 - UniversalTaskRuntime

- Enforce task bootstrap for every executable operation.
- Bind TaskDraft, ExecutionPlan, ApprovalRequest, TaskRun.
- Prevent TaskRun without executable plan.
- Tests: read-only analysis with artifacts, patch request, shell request, project generation.

Implementation status: IN_PROGRESS_BOOTSTRAP_GUARD_CONNECTED

Implemented in this wave:

- Confirmed `TaskBootstrapRuntimeService` as the canonical bootstrap identity creator.
- `TaskRuntimeService.create_run` already bootstraps `UniversalTask` before persisting any `TaskRun`; this remains the canonical task-runtime entrypoint.
- `TaskRunGuard` now blocks any run that lacks `task_id`, `task_run_id`, `operation_id`, or `bootstrap_context`.
- `TaskRunGuard` now blocks mismatches between `TaskRun` identity fields and `bootstrap_context`.
- Runtime approval context now binds `ApprovalRequest.task_id` to canonical `run.task_id`, not `run.run_id`.
- Shared tests/fixtures now represent bootstrapped `TaskRun` objects instead of orphan runtime records.
- Mobile pipeline cards now normalize missing planning/graph status to `unknown`, avoiding invalid UI state values.

Temporary adapters remaining:

- `TaskRuntimeService` remains the canonical implementation, but several legacy services still create/read task-like references using `run_id` as `task_id`.
- `TaskDraft`, `TaskPreview`, approval continuation, artifact fulfillment, chat result publishing, and debug traces still need unified identity semantics.
- Direct `TaskRun(...)` construction still exists in tests and should be migrated to canonical fixtures/support helpers in the final compatibility wave.

## Wave 4 - RuntimeTimeline

- Create canonical event sequence for TaskRun.
- Derive lifecycle state from timeline.
- Bind artifacts and validation events to steps.
- Tests: sequence ordering, failed step, blocked step, artifact producer step.

Implementation status: IN_PROGRESS_EXECUTION_GUARD_CONNECTED

Implemented in this wave:

- Confirmed `RuntimeTimelineService` as the canonical TaskRun timeline projection.
- Confirmed `TaskRunEventService` as the canonical TaskRun event writer for governed runtime events.
- `SupervisedExecutionLoop` now blocks execution when a stored `TaskRun` does not have initial timeline events.
- Required initial event contract: `run_created` and `task_bootstrap_created`.
- Execution now requires contiguous timeline event sequences before the first runtime step can run.
- Added regression coverage for manual/orphan TaskRun records that lack initial timeline events.

Temporary adapters remaining:

- Non-TaskRun event systems still exist for agent kernel, Codex/Gemini/Lucio adapters, debugger, session events, generic event store, telemetry, and replay.
- `RuntimeTimelineService` still tolerates historical fallback identity (`run.task_id or run.run_id`) for compatibility with old data.
- Timeline is a projection over stores, not yet the only state writer; later waves must make lifecycle/completion/Speaker Truth consume timeline as the primary source.

## Wave 5 - ArtifactRuntime

- Separate runtime artifacts from workspace mutation.
- Make logical_path distinct from storage_ref.
- Add identity, hash, producer, validation status.
- Tests: read-only artifact generation, workspace hash unchanged.

Implementation status: IN_PROGRESS_CANONICAL_ARTIFACT_BOUNDARY_CONNECTED

Implemented in this wave:

- Confirmed `ArtifactRuntimeService` as the canonical Artifact Runtime facade.
- Confirmed `UniversalArtifactRegistryService` as the storage/registry implementation behind the Artifact Runtime boundary, not as a public runtime authority.
- Artifact creation through `ArtifactRuntimeService` now requires a producer step and at least one task binding (`task_id` or `task_run_id`).
- Artifact validation now blocks evidence use when `task_id`, `task_run_id`, or `event_id` is missing.
- Runtime Doctor artifacts now declare diagnostic task/run binding metadata when the expected contract does not include an observed Task/TaskRun.
- Regression coverage now rejects orphan artifacts and blocks artifacts that are missing producer event binding.

Temporary adapters remaining:

- Some legacy services still write artifacts through old report, preview, write, export, or registry services and must be migrated to `ArtifactRuntimeService`.
- `ReadonlyAnalysisArtifactRuntimeService` now binds artifacts to a real TaskRun event, but still carries compatibility identity debt by using `run_id` as both `task_id` and `task_run_id` in some artifact creation paths.
- Remaining domain-specific artifact writers still need canonical `event_id` binding before their artifacts can be treated as authoritative completion evidence.
- Historical artifacts without `task_id`, `task_run_id`, or `event_id` remain readable as old data but should not satisfy strict validation until migrated/backfilled.

## Wave 6 - SpeakerTruth

- Make final response derive from timeline, validation, artifacts.
- Remove final-state assembly from routers/view-models.
- Tests: no false success, blocked task says blocked, missing outputs cannot pass.

Implementation status: IN_PROGRESS_RUNTIME_TRUTH_CONNECTED

Implemented in this wave:

- Confirmed `RuntimeTruthEngine` as the canonical operational SpeakerTruth authority for TaskRun-facing consumers.
- `RuntimeTruthEngine` now includes timeline artifacts in truth evidence and blocks success when completed results depend on orphan artifacts.
- `CanonicalOperationStateService` no longer returns `COMPLETED` from a completed result unless `RuntimeTruth` is present and safe.
- `UniversalTaskSessionService` now derives `validation_state.safe_to_report_success` and `result_state.safe_to_report_success` from `CanonicalOperationState`, not directly from `TaskRunResult.completion`.
- Added regression coverage for artifact-orphan false success and canonical state completion without runtime truth.

Temporary adapters remaining:

- `SpeakerService` still composes legacy chat/conversation answers and must remain a non-operational conversation adapter until public chat fully consumes SpeakerTruth.
- Domain services such as sandbox, agents, Lucio, reports, and patching still assemble local `final_answer` or status summaries; these must become consumers of runtime truth for operational claims.
- `CanonicalSpeakerTruthService` remains for governance lifecycle snapshots and should be adapted under or reconciled with `RuntimeTruthEngine` instead of acting as a separate final-answer authority.
- Some clients still expose `TaskRunResult.status` for compatibility, but success claims must be treated as mirrors of canonical operation state.

## Wave 7 - Repositories

- Consolidate artifact/event/task/approval/context stores.
- Add ownership map.
- Mark legacy repositories as adapters or archive candidates.

Implementation status: IN_PROGRESS_DATA_MIGRATION_EXECUTED

Implemented in this wave:

- Removed the proposed facade approach before keeping it as architecture.
- Physically migrated `data/runtime/context_plans/*.json` into `data/runtime/context/plans/*.json`.
- Updated `config/rag/integration/context_usage_audit_policy.yaml` to use `data/runtime/context/plans`.
- Updated `ContextUsageAuditService` fallback path to `data/runtime/context/plans`.
- Archived empty legacy directories under `data/runtime/repository_legacy/empty_dirs`:
  - `data/runtime/context_plans`
  - `data/runtime/tasks`
  - `data/runtime/artifacts`
- Generated reversible migration manifest at `reports/wave7_repository_migration/repository_data_migration_manifest.json`.
- Generated migration report at `reports/wave7_repository_migration/repository_data_migration.md`.

Temporary adapters remaining:

- Active configured stores were not moved in this wave: `task_runs`, `approvals`, `events`, `artifact_previews`, `artifact_writes`, and `data/artifacts`.
- Root repository placeholder files remain cleanup candidates, but no facade was introduced.
- Context plan historical references in old reports/audit docs remain as historical documentation and were not rewritten.
- A broader chat/context e2e failed on chat policy behavior and is recorded as a regression candidate rather than masked as success.

## Wave 8 - Client Alignment

- Mobile, Launcher, API, External Gateway consume Universal Task Session.
- Remove provider/client-specific state derivation.

Implementation status: IN_PROGRESS_PUBLIC_CHAT_CLIENT_ALIGNMENT

Implemented in this wave:

- Persistent chat route now indexes grounded final answers through `ChatResultIndexService` and returns stable `result_ref_id`.
- `CanonicalPublicChatService` now owns client-facing operation adapters for permission status, session diagnostics, artifact-from-answer, filesystem archive artifacts, follow-up recall/review, and read-only project-analysis previews.
- `ChatService` remains a conversation/model content provider for public chat; persistent public routing no longer needs to fall back to its broad operational dispatcher for the migrated client-facing operations.
- Added `FollowupResultRecallService` so repeated-answer/summary requests read the grounded result index instead of asking a model to reconstruct prior content.
- `PublicRouteLifecycleService` now distinguishes Artifact Store generation from workspace mutation when a response has `requires_task=False`, `workspace_write=False`, and real artifact evidence.
- Mobile persistent chat regression file now passes as a whole.

Resolved or reduced in this wave:

- COMP-010 partial: follow-up recall/review for persistent chat now consumes the result index and degrades when no grounded result exists.
- COMP-011 partial: artifact request and filesystem archive client operations route through the canonical public chat entrypoint and preserve Artifact Store vs workspace write separation.
- COMP-014 partial: mobile chat presentation now consumes metadata emitted by the canonical persistent route; no fake progress states were found in `apps`/`src`.

Temporary adapters remaining:

- `ChatOperationRouterService` still supplies compatibility classification for these client-facing operations until `RuntimeContractBundle` fully owns them.
- Launcher pipeline views were inspected for `linked_task_run_id` usage but not refactored in this pass because no failing client-alignment test or unsafe fake state was identified.
- External Gateway/Public Runtime client alignment remains outside this narrow mobile/API pass.

## Wave 9 - Tests

- Build matrix: test -> contract -> regression -> module.
- Remove duplicate helpers only after matrix and passing tests.

Wave 9 implementation notes:

- Added `AIpinho_TestCoverageMatrix.md` as the canonical test-to-contract index for consolidation verification.
- Added `tests/support/runtime_fixtures.py` as the canonical shared test support module for runtime request/run/plan fixtures.
- Kept `tests/conftest.py` as a compatibility reexport only, preserving existing tests while preventing another helper implementation.
- Added `tests/unit/test_runtime_test_support_fixtures.py` to lock canonical fixture identity invariants.
- COMP-015 was partially resolved in Wave 9; the remaining 8 direct `conftest` imports were closed in Wave 10.
- COMP-022 remains open for specialized local `TaskRun(...)` constructors that need case-by-case migration.

## Wave 10 - Cleanup

- Quarantine migrated legacy.
- Update `AIpinho_RemovedFiles.md`.
- Update compatibility and breaking-change ledger.

Wave 10 implementation notes:

- Removed generated Python caches under the project root (`__pycache__`) after tests/collection runs.
- Closed COMP-015 by migrating remaining direct `from conftest import ...` imports to `tests.support.runtime_fixtures` and removing the compatibility reexport from `tests/conftest.py`.
- Removed empty, unreferenced placeholder modules/tests that were competing nominally with canonical services or adding dead-code noise.
- Fixed runtime identity metadata in Speaker updates and chat result publication events so canonical `task_id` and `task_run_id` are carried separately.
- Replaced the stale `chat_router` module hint in Patch Intelligence seed knowledge with canonical semantic/governance/runtime modules.
- Added `continue_integration_router` as a package-level compatibility alias to `governance_lifecycle_router`; no endpoint or runtime route was duplicated.
- Full test collection passed after cleanup: 2401 tests collected.

## Wave 11 - Residual Compatibility Cleanup

- Reduced COMP-031 by moving public/runtime artifact lookup, listing, provenance, revalidation, debugger trace lookup, Codex delegation artifact lookup, and Universal Task Session artifact aggregation behind `ArtifactRuntimeService`.
- `UniversalArtifactRegistryService` remains only as the internal storage implementation and for legacy universal artifact creation contracts that still accept `UniversalArtifactCreateRequest`.
- Hardened the readonly artifact runtime so lookup/revalidation use `ArtifactRuntimeService`; constructor injection of the old registry is still adapted into the canonical runtime.
- Reduced COMP-016 by making `/api/v1/policy/resolve` and `/api/v1/policy/explain` expose `canonical_policy` from `EffectivePolicyDecisionService` while preserving the legacy `PolicyDecision` response fields.
- Fixed a stale policy API regression test that treated `C:\PinhoabacaxiAI` as forbidden even though current workspace policy explicitly marks it as governed/approval-gated; the test now uses the generic protected OS root.
- Fixed a brittle multi-agent integration fixture by enabling required test agents through environment overrides instead of depending on local operator profile state.

Still open after Wave 11:

- COMP-016 is partial: policy endpoints expose canonical decision metadata, but still call `PolicyKernelService` to preserve old schema.
- COMP-017 remains open for chat/tools/task draft direct policy-kernel consumers.
- COMP-022 remains open for specialized local `TaskRun(...)` constructors.
- COMP-031 is partial: read/list/validate consumers migrated, but artifact creation services still use the internal registry until creation contracts require canonical task/task-run binding.
- COMP-033 remains open for lifecycle `CanonicalSpeakerTruthService` reconciliation with `RuntimeTruthEngine`.

## Wave 12 - Policy, Artifact Creation, TaskRun, and Speaker Truth Compatibility

Wave 12 implementation notes:

- Reduced COMP-016 further by moving legacy `PolicyResolveRequest` adaptation into `EffectivePolicyDecisionService`; `policy_router.py` no longer instantiates `PolicyKernelService` for resolve, explain, contract preview, or status.
- Closed COMP-017 for the named production consumers in this wave: `ChatService`, `ToolSafetyService`, `ToolExecutionGuard`, `PromptIntelligenceService`, and `TaskContractDraftService` no longer instantiate or import `PolicyKernelService`; they call `EffectivePolicyDecisionService`.
- Hardened direct read guards so path validation for file reads uses read/governed-approval semantics (`block_read` and `requires_governed_approval`) instead of task-creation semantics (`block_task`).
- Reduced COMP-031 by making public universal artifact creation use `ArtifactRuntimeService.create_from_universal_request` when the request contains complete canonical binding: `task_id`, `task_run_id`, `producer_step`, logical path, and content.
- Kept legacy artifact creation as explicit compatibility only when old public contracts lack complete runtime binding; responses now expose `source=universal_artifact_registry_compat` and a compatibility warning instead of pretending the artifact was canonically created.
- Fixed a concrete route dispute between `PublicRuntimeAPI` and `ArtifactRouter` at `POST /api/v1/artifacts`: the public route now dispatches versioned public-runtime contracts to `PublicRuntimeAPI` and universal artifact contracts to the canonical artifact creation path.
- Closed COMP-022 for production runtime code: direct production `TaskRun(...)` construction remains only inside `TaskRuntimeService`, the canonical authority. Remaining direct constructors are specialized tests/fixtures and stay as test cleanup debt.
- Reduced COMP-033 by adding `CanonicalSpeakerTruthService.from_runtime_truth` and optional RuntimeTruth-backed evaluation; runtime truth can now dominate canonical Speaker Truth when timeline/runtime evidence is available.

Still open after Wave 12:

- COMP-016 remains an internal compatibility debt only: `EffectivePolicyDecisionService` still uses `PolicyKernelService` as its legacy backend to preserve public `PolicyDecision` schema.
- COMP-020 remains open: many services still compare raw policy strings instead of canonical `CanonicalPermission`.
- COMP-022 remains open for specialized unit-test `TaskRun(...)` constructors; production direct construction is canonical-only.
- COMP-031 remains partial for producers that submit `local_path`-only or otherwise incomplete legacy artifact creation contracts.
- COMP-033 remains partial until lifecycle services pass real `RuntimeTruthEngine.evaluate(...)` results for all operational completions instead of snapshot-only truth.
- Existing chat/task-draft tests still contain expectations that conflict with current canonical routing/configuration; see validation notes below.

## Final Compatibility Wave - Pending Migration Backlog

Status: COMPAT_BACKLOG_OPEN

Principle:

- Canonical waves should keep moving toward the five authorities.
- Compatibility leftovers must be registered here instead of forcing each wave to preserve old internals forever.
- The final compatibility wave will migrate or remove these adapters after canonical flows are stable.

Pending migrations identified so far:

| ID | Area | Pending migration | Current compatibility mechanism | Target canonical destination | Notes |
|---|---|---|---|---|---|
| COMP-001 | Legacy chat imports | Migrate tests/imports from `aipinho.api.routers.chat_router` to canonical lifecycle helpers or public routes | Non-route `chat_router` shim | `governance_lifecycle_router` / `CanonicalPublicChatService` | Do not re-add public legacy router. |
| COMP-002 | Persistent chat helper | Replace `_persistent_chat_response` tests/helpers with public `/api/v1/chat/sessions/{session_id}/send` or `CanonicalPublicChatService.respond` | Helper shim delegates or returns canonical preview-shaped response | Universal public chat route | Current helper must stay non-authoritative. |
| COMP-003 | Workspace context helper | Move `_workspace_context_from_messages` into a canonical context/workspace utility or replace tests with `WorkspaceContext` service | Helper shim with pure extraction logic | `WorkspaceContext` / Conversation Context | Avoid keeping this under API router namespace long-term. |
| COMP-004 | Legacy approval bootstrap expectations | Rewrite tests that expect ApprovalRequest without executable context/context_ref | Current approval gate blocks with `PREVIEW_REJECTED_NO_CONTEXT_REF` | ApprovalRuntime under `UniversalTaskRuntime` | Do not weaken approval gates. |
| COMP-005 | Chat operation specialized branches | Migrate artifact/report/workspace metadata/follow-up/sandbox/project branches out of `ChatOperationRouterService` | `ChatOperationRouterService` compatibility adapter | `SemanticIntentResolution` -> `RuntimeContractBundle` -> domain handlers | Must preserve public operation vocabulary until consumers migrate. |
| COMP-006 | CanonicalIntentRouter internal ownership | Fold or rename `CanonicalIntentRouter` as internal signal collector under semantic runtime | Used behind `SemanticIntentResolutionService` | `SemanticIntentResolution` internals | Should not be imported directly by runtime/public services. |
| COMP-007 | Permission grant action parsing | Move remaining grant action extraction into contract/policy-driven permission semantics | `ChatPermissionGrantService` still extracts actions locally | `RuntimeContractBundle.permissions` + `EffectivePolicyDecision` | Current guard is canonical, but action derivation remains local. |
| COMP-008 | Legacy ChatService operational paths | Remove direct operational ownership from `ChatService.respond` once public callers are fully canonical | `CanonicalPublicChatService` calls ChatService only as conversation provider | Chat as content provider only | Tests already assert public service uses it only for conversation. |
| COMP-009 | Public fact/web search route | Convert `public_fact_query` legacy chat decision into semantic contract and capability route | `ChatOperationRouterService` branch | `SemanticIntentResolution` + capability contracts | Browse/current-info policy should remain explicit and governed. |
| COMP-010 | Follow-up result recall/review | Replace router-local follow-up classification with conversation memory/result contracts | `ChatOperationRouterService` branch | Conversation Context + SpeakerTruth/result index | Avoid final-answer reconstruction in router. |
| COMP-011 | Artifact request offer/fulfillment | Move artifact request classification and fulfillment behind Artifact Runtime contracts | `ChatOperationRouterService` + `ChatArtifactFulfillmentService` | `ArtifactRuntime` | Preserve logical artifact vs workspace write distinction. |
| COMP-012 | Workspace readonly audit/report compatibility | Migrate `workspace_readonly_audit_report` routing to semantic artifact/report contracts | Router branch with policy YAML terms | `RuntimeContractBundle.artifacts` + `ArtifactRuntime` | Keep read-only workspace mutation=false, artifact_generation=true. |
| COMP-013 | Session diagnostic | Move session diagnostic classification to semantic contracts and status/timeline services | Router/lifecycle explicit terms | `SemanticIntentResolution` + RuntimeTimeline diagnostics | Must remain explicit only. |
| COMP-014 | Mobile/Launcher status derivation | Replace any remaining view-model state derivation with Universal Task Session and SpeakerTruth | View-model mappers | `UniversalTaskRuntime` + `RuntimeTimeline` + `SpeakerTruth` | Final compat wave should remove UI-side state guesses. |
| COMP-015 | Test helper duplication | Consolidate repeated test helpers into canonical `tests/support` after behavior stabilizes | Closed in Wave 10 | `tests/support/runtime_fixtures.py` + Test Coverage Matrix support layer | No direct `from conftest import ...` imports remain. |
| COMP-016 | Legacy Policy Kernel public routes | Adapt `/api` policy endpoints to expose canonical effective decision while preserving old schema | `PolicyKernelService` direct use in `policy_router.py` | `EffectivePolicyDecisionService` + public policy DTO adapter | Do not break current clients during Wave 2. |
| COMP-017 | Tool/chat/task draft policy calls | Move direct `PolicyKernelService` consumers in chat, tools, and orchestration to the effective policy boundary | Direct service injection | `EffectivePolicyDecisionService` under `RuntimeContractBundle` | Requires preview/task contract migration first. |
| COMP-018 | Multi-agent policy kernel | Fold `MultiAgentPolicyKernelService` semantics into generic participant/capability policy | Separate multi-agent kernel | `EffectivePolicyDecision` + Universal Participant contracts | Must avoid provider-specific policy branches. |
| COMP-019 | `safe_to_execute` scattered flags | Replace schema-local execution booleans with derived canonical runtime state | Preview/result DTO fields | `EffectivePolicyDecision` + `UniversalTaskRuntime` + `RuntimeTimeline` | Keep response fields as compatibility mirrors until clients migrate. |
| COMP-020 | Raw policy string literals | Replace scattered `allowed`/`needs_approval`/`denied` checks with canonical enum adaptation | Local string comparisons | `CanonicalPermission` through `EffectivePolicyDecisionService` | Do in controlled batches to avoid behavior drift. |
| COMP-021 | Runtime `run_id` used as `task_id` | Replace task identity fallback in artifacts, chat result publisher, debugger, Speaker updates, timelines, and readonly artifact runtime | Compatibility fields accept `run_id` aliases | `UniversalTaskRuntime` identity: `task_id` + `task_run_id` | Keep lookup accepting both until clients migrate. |
| COMP-022 | Direct `TaskRun(...)` construction | Replace manual TaskRun test/service construction with bootstrap factory | Local fixtures/manual constructors plus canonical test fixture for generic runtime runs | `TaskBootstrapRuntimeService` + `TaskRuntimeService.create_run` | Wave 9 added fixture invariant tests; specialized local constructors remain until safely migrated. |
| COMP-023 | Approval continuation identity fallback | Stop writing `approval.task_id = latest.run_id` in approval continuation | Legacy continuation fallback | ApprovalRuntime under `UniversalTaskRuntime` | Requires migration of old approvals whose task_id stored run_id. |
| COMP-024 | Mobile pipeline task endpoint refs | Ensure UI endpoint refs use task_run lookup semantics explicitly | `task_ref = run.run_id` for Universal Task Session endpoints | Universal Task Session public route | Endpoint path is task-run based; label should not imply canonical task_id. |
| COMP-025 | Non-TaskRun event systems | Fold agent/debugger/session/generic/telemetry event streams into canonical timeline adapters | Separate event stores and API timelines | `RuntimeTimeline` + `RuntimeTimelineAdapter` | Do not remove domain events until adapters preserve public views. |
| COMP-026 | Timeline identity fallback | Remove `run.task_id or run.run_id` fallback after all historical data and writers use canonical identity | RuntimeTimeline compatibility fallback | `task_id` and `task_run_id` as distinct required fields | Requires migration/backfill of old runtime records. |
| COMP-027 | Lifecycle/completion status writers | Derive final operation state from RuntimeTimeline instead of local status fields | Multiple status writers remain | `RuntimeTimeline` -> Completion -> SpeakerTruth | Planned for Wave 6 after ArtifactRuntime alignment. |
| COMP-028 | Legacy artifact writers | Migrate report, preview, write, export, runtime doctor legacy, readonly-analysis, and domain artifact writers to call `ArtifactRuntimeService` | Direct repository/registry/writer services remain | `ArtifactRuntimeService.create` + `ArtifactRuntimeService.validate` | Preserve public report/export files, but make registry identity canonical. |
| COMP-029 | Artifact event binding | Backfill or attach real timeline `event_id` to artifacts produced by older/domain writers | Missing event IDs remain readable but fail strict evidence validation | `RuntimeTimeline` event -> `ArtifactRuntimeCreateRequest.event_id` | Required before Completion/SpeakerTruth can rely exclusively on artifact evidence. |
| COMP-030 | Artifact identity backfill | Replace `run_id`-as-`task_id` artifact records with distinct canonical task/run identities | Lookup aliases and old records | `task_id` + `task_run_id` + `operation_id` binding | Coordinate with COMP-021 identity migration. |
| COMP-031 | Artifact store direct access | Convert consumers that query `UniversalArtifactRegistryService` directly into ArtifactRuntime lookup/validation consumers | Registry remains internal store | `ArtifactRuntimeService.get/list_for_task/validate` | Keeps logical path and workspace mutation semantics centralized. |
| COMP-032 | Legacy chat SpeakerService | Keep conversation-only composition but remove operational final-answer authority | `SpeakerService.compose_response` still builds preview/conversation/block text | `RuntimeTruthEngine` -> SpeakerTruth response adapter | Do not route operational success claims through this service. |
| COMP-033 | Governance lifecycle speaker truth | Reconcile `CanonicalSpeakerTruthService` with `RuntimeTruthEngine` | Lifecycle snapshot truth remains separate schema | RuntimeTruth-backed lifecycle speaker truth adapter | Preserve lifecycle DTOs while removing parallel authority. |
| COMP-034 | Domain-local final answers | Migrate sandbox, agents, Lucio, reports, patching, and project factory local final answers to SpeakerTruth evidence adapters | Local `final_answer`/`summary` construction remains | `RuntimeTruthEngine` + artifacts/validation/timeline evidence | Conversation wording may remain local only after truth gate approves claims. |
| COMP-035 | Client result-state mirrors | Replace direct client trust in `TaskRunResult.status` with canonical state mirrors | UniversalTaskSession still exposes result status for compatibility | `CanonicalOperationState` + `RuntimeTruth` | Status may be shown, but success safety comes from canonical state. |
| COMP-036 | Active runtime store ownership | Migrate consumers before any physical move of `task_runs`, `approvals`, `events`, `artifact_previews`, `artifact_writes`, or `data/artifacts` | Active configured store paths remain in place | Canonical owner per domain: UniversalTaskRuntime, ApprovalRuntime, RuntimeTimeline, ArtifactRuntime | Do not introduce repository facade; migrate one store at a time with manifest. |
| COMP-037 | Event store unification | Decide and migrate `data/runtime/events` into RuntimeTimeline ownership or document it as a timeline adapter store | Configured event store remains active | `RuntimeTimeline` + event adapter contracts | Requires consumer scan and event schema compatibility before movement. |
| COMP-038 | Context plan lifecycle | Add retention/versioning policy for `data/runtime/context/plans` after migration | Context plans now use canonical path but no lifecycle cleanup policy was added in this wave | Context runtime lifecycle/retention policy | No automatic deletion; archive with manifest if retention is later applied. |

## Wave 7.5 - Compatibility and Structural Debt Cleanup

Implementation status: IN_PROGRESS_CANONICAL_COMPAT_CLEANUP

Resolved in this wave:

- COMP-001: removed the non-route `aipinho.api.routers.chat_router` compatibility shim after migrating all consumers.
- COMP-002: replaced `_persistent_chat_response` usage with `CanonicalPublicChatService.respond` and the canonical persistent chat route.
- COMP-003: moved persistent chat workspace-context extraction to `PersistentChatWorkspaceContextService`.
- COMP-021 partial: separated `task_id` from `task_run_id` in readonly artifact runtime, task-result publishing, chat artifact fulfillment, approval continuation, and task block causes.
- COMP-023: approval continuation no longer writes `approval.task_id = latest.run_id`; runtime context attachment preserves canonical `task_id` separately from `run_id`.
- Chat/RAG context policy regression: citation/source bypass and automatic context activation checks now use `ContextPromptPolicyService` with config-driven terms before chat operation routing.

Files removed:

- `src/aipinho/api/routers/chat_router.py`
- `src/aipinho/api/routers/__pycache__/chat_router.cpython-311.pyc`

Temporary adapters still remaining:

- `ChatOperationRouterService` still owns several specialized compatibility branches.
- Legacy/manual/sandbox result IDs in `ChatService` still use domain-specific run identifiers and require a contract migration before they can become Universal Task identities.
- Agent/debugger island traces still use agent run IDs as task-like display IDs until external/agent timeline adapters are consolidated.
- Full mobile chat integration suite still has unrelated failing scenarios when run as a broad file; focused canonical slices pass and the failures are recorded as follow-up compatibility risk.

Exit criteria for final compatibility wave:

- No runtime/public service imports legacy chat helpers.
- No test imports `aipinho.api.routers.chat_router`.
- No compatibility shim is registered as route or runtime authority.
- All remaining adapters either delegate to canonical authorities or are removed.
- Legacy tests are rewritten to assert current safety contracts, not pre-hardening behavior.
