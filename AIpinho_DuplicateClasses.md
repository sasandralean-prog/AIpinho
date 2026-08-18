# AIpinho - Duplicate Classes and Equivalent Implementations

Status: DUPLICATE_CLASS_LEDGER_STARTED

## Known Duplicate Domains

| Domain | Duplicated/equivalent forms | Canonical target |
|---|---|---|
| Status/state fields | status, state, phase, result, validation_status | CanonicalOperationState |
| Runtime identity | task_id, task_run_id, operation_id, preview_id, approval_id | Strong ID types |
| Policy decisions | policy kernel, permission resolver, session grants, config grants | EffectivePolicyDecision |
| Approval flows | approval command, UI approval, runtime approval, task approval | ApprovalRuntime under UniversalTaskRuntime |
| Artifacts | artifact repository, artifact runtime, reports, previews, writes | ArtifactRuntime |
| Events/timeline | events, telemetry, replay, regression, runtime doctor evidence | RuntimeTimeline |
| External agents | codex, gemini, lucio, agents, connectors | Universal Participant/Connector |
| Registries | action/capability/model/provider/role/route/skill/tool registries | Registry base + capability marketplace |
| Tests helpers | root helpers, fixtures, sandbox/workflow/unit duplicated helpers | tests/support |

## Process

For every duplicate:

1. Choose canonical implementation.
2. List consumers.
3. Add adapter if compatibility is required.
4. Migrate consumers.
5. Mark shadow as legacy.
6. Remove/quarantine only after tests.

## Wave 9 - Test Support Duplication

- Consolidated generic runtime test helpers from `tests/conftest.py` into `tests/support/runtime_fixtures.py`.
- Wave 10 migrated the remaining direct helper imports to `tests.support.runtime_fixtures`.
- `tests/conftest.py` no longer reexports `runtime_run`, `runtime_request`, `one_step_plan`, `runtime_context`, or `allowed_policy`.
- Remaining duplicated local constructors are not deleted in bulk because some encode domain-specific states such as approvals, project generation, blocked task explainability, and Universal Task Session progress.
- Pending migration: replace local constructors only when their state can be expressed by the canonical support fixture without weakening the regression being tested.

## Wave 10 - Empty Placeholder Cleanup

- Removed empty, unreferenced placeholder modules from core/repositories/schemas/services and empty test files with no collected tests.
- These files had zero bytes and no internal references in `src`, `tests`, `apps`, or `config`.
- Canonical implementations remain in the domain services already selected by the consolidation waves.

## Wave 1 Findings

- `CanonicalIntentRouter` and chat-level parsing logic represented overlapping intent authority. Wave 1 introduced `SemanticIntentResolutionService` as the canonical entrypoint and moved consumers toward delegation.
- `ChatPermissionGrantService` previously owned independent positive/negative grant classification. It now uses semantic resolution as the guard and keeps only grant materialization/preview responsibilities.
- `ChatOperationRouterService` still contains broad compatibility translation logic. It is classified as `KEEP_WITH_REFACTOR` until specialized operation contracts migrate behind `RuntimeContractBundle`.
- Removed `chat_router` imports still existed in tests. A non-endpoint compatibility shim was added to prevent import breakage without restoring a public legacy router.

## Wave 2 Findings

- `CanonicalPolicyService` and `PolicyKernelService` were overlapping policy decision entrypoints. Wave 2 introduced `EffectivePolicyDecisionService` as the lifecycle-facing authority.
- `CanonicalPolicyService` is now classified as an internal normalizer/resolver, not the top-level policy authority.
- `PolicyKernelService` remains `KEEP_WITH_REFACTOR` as a legacy kernel for existing API/task/tool/chat consumers until they can consume `RuntimeContractBundle` and canonical policy decisions.
- `safe_to_execute` appears across previews, tool results, task drafts, chat DTOs, and contracts. It is a compatibility mirror for now and must be derived from canonical policy + runtime state in later waves.

## Wave 3 Findings

- `TaskBootstrapRuntimeService` and `TaskRuntimeService` are the canonical bootstrap/runtime pair; no new Universal Task implementation was created.
- The previous duplicate identity pattern used `run_id` interchangeably as `task_id`. Wave 3 begins separating canonical `task_id` from `task_run_id`.
- `TaskRunGuard` is now the runtime boundary that rejects orphan `TaskRun` records before execution.
- Several non-canonical identity fallbacks remain in chat artifact fulfillment, chat result publishing, debugger traces, timeline fallback, Speaker task updates, and readonly artifact runtime. These are tracked as final compatibility migrations.

## Wave 4 Findings

- `RuntimeTimelineService` is selected as the canonical TaskRun timeline projection.
- `TaskRunEventService` is selected as the canonical TaskRun event writer.
- Separate event/timeline domains still exist for generic events, agent kernel, Codex/Gemini/Lucio adapters, debugger, session events, telemetry, and replay. These are adapters/shadows until migrated.
- `SupervisedExecutionLoop` now rejects execution when the initial timeline is missing, preventing stored/manual TaskRun records from bypassing observability.

## Wave 5 Findings

- `ArtifactRuntimeService` is selected as the canonical Artifact Runtime facade.
- `UniversalArtifactRegistryService` is retained as the internal registry/store implementation behind ArtifactRuntime.
- Report writers, artifact preview/write services, export services, Runtime Doctor report generation, and readonly-analysis artifact generation remain equivalent artifact producers and must converge on `ArtifactRuntimeService`.
- Artifact validation is now centralized at the ArtifactRuntime boundary; artifacts without task, task-run, or producer event binding are not authoritative evidence.
- Readonly-analysis now binds generated artifacts to the canonical TaskRun event stream; other domain producers still need the same treatment.
- Direct registry consumers are classified as `KEEP_WITH_REFACTOR` until compatibility adapters migrate lookups to ArtifactRuntime.

## Wave 6 Findings

- `RuntimeTruthEngine` is selected as the canonical operational SpeakerTruth authority for TaskRun-facing runtime consumers.
- `CanonicalOperationStateService` is the status mirror derived from RuntimeTruth, not an independent completion authority.
- `UniversalTaskSessionService` now mirrors canonical state for safe-success fields, reducing client-side state divergence.
- `CanonicalSpeakerTruthService` remains a governance lifecycle adapter/shadow until it is backed by RuntimeTruth.
- Legacy `SpeakerService` and domain-local final answer builders remain compatibility adapters and must not assert operational success without RuntimeTruth evidence.

## Wave 7 Findings

- `data/runtime/context_plans` duplicated the context runtime data domain outside `data/runtime/context`.
- Existing context plan files were physically migrated to `data/runtime/context/plans`.
- Empty runtime roots `data/runtime/tasks` and `data/runtime/artifacts` were archived as legacy empty directories, not deleted.
- A repository facade proposal was removed before becoming part of the architecture; Wave 7 uses data migration and config ownership instead.
- Active configured stores remain in place until their consumers can be migrated without compatibility loss.

## Wave 7.5 Findings

- The non-route `api.routers.chat_router` shim duplicated persistent chat behavior after the canonical public chat route was restored. It was removed after consumers migrated.
- `_persistent_chat_response` and `_workspace_context_from_messages` no longer exist as API-router helper authorities.
- `PersistentChatWorkspaceContextService` is now the reusable context extraction utility for persistent chat tests and future callers.
- `ContextPromptPolicyService` centralizes context/RAG prompt policy checks that previously competed between `ChatService`, `ChatOperationRouterService`, and RAG memory policy expectations.
- Runtime identity duplication was reduced: approval continuation, readonly artifact runtime, artifact fulfillment, task-result publishing, and task block causes now prefer canonical `task_id` while preserving `run_id`/`task_run_id` as execution references.
- Remaining duplicate identity patterns are domain-specific external/agent/manual-run cases and should be migrated only when their contracts are promoted into Universal Task Runtime.

## Wave 8 Findings

- Persistent public chat previously depended on client-facing operation behavior that still lived inside the broad legacy `ChatService` dispatcher.
- `CanonicalPublicChatService` now owns the migrated client-facing operation adapters, reducing public-route dependence on `ChatService` for operational classification.
- `FollowupResultRecallService` complements `FollowupResultReviewService` and makes result recall an index lookup, not a model-generated reconstruction.
- Artifact request/archive responses now carry lifecycle evidence sufficient for `PublicRouteLifecycleService` and no longer get degraded by missing validation output when the artifact was actually created and validated.
- The broader `ChatOperationRouterService` remains a compatibility classifier and is still a consolidation target for future semantic contract waves.
