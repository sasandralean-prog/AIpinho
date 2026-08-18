# AIpinho - Compatibility Matrix

Status: COMPATIBILITY_MATRIX_STARTED

| Client/surface | Current risk | Required canonical path | Compatibility strategy |
|---|---|---|---|
| Chat | Routers and parsers can compete | SemanticIntentResolution -> RuntimeContractBundle | Keep routes, delegate internally |
| Mobile | View models may derive state | Universal Task Session + SpeakerTruth output | Mapper from canonical contracts |
| Launcher | Operational state duplication | Universal Task Session + RuntimeTimeline | Adapter until UI consumes session |
| API/Public Runtime | Multiple internal service entrypoints | External Gateway -> canonical runtime | Preserve endpoints |
| Codex/Gemini/Lucio | Provider-specific paths | Universal Connector/Participant | Adapter profiles |
| Tests | Helpers and scenarios duplicated | Test coverage matrix | Keep tests, refactor helpers later |

## Rule

Compatibility is preserved at public boundaries, not by preserving duplicate internals.

## Wave 1 - SemanticIntentResolution

| Surface | Compatibility Decision | Status | Notes |
|---|---|---|---|
| `GovernanceLifecycleService.evaluate` | Preserve public snapshot schema | Compatible | Intent source moved to `SemanticIntentResolutionService`; existing public `evidence` values preserved. |
| `ChatPermissionGrantService.handle` | Preserve response contracts | Compatible | Positive grant detection now passes through semantic classification before grant preview/session mutation. |
| `ChatOperationRouterService.route` | Preserve historical operation vocabulary | Compatible adapter | Semantic precedence is used for safe authoritative classes; specialized router aliases remain adapters. |
| `aipinho.api.routers.chat_router` imports | Restore helper imports without routes | Compatibility shim | No `APIRouter`; helpers delegate or return canonical preview-shaped responses. |
| Legacy approval bootstrap tests | Keep stronger safety behavior | Needs migration | Current approval service blocks approval without complete executable context (`PREVIEW_REJECTED_NO_CONTEXT_REF`). |

## Wave 2 - EffectivePolicyDecision

| Surface | Compatibility Decision | Status | Notes |
|---|---|---|---|
| `GovernanceLifecycleService.evaluate` | Preserve public snapshot schema | Compatible | Policy source moved to `EffectivePolicyDecisionService`; lifecycle still returns `CanonicalPolicyDecision`. |
| `CanonicalPolicyService` imports in tests | Preserve direct normalizer tests temporarily | Compatible internal | Service remains as internal normalizer; new consumers should use `EffectivePolicyDecisionService`. |
| `PolicyKernelService` public/API consumers | Preserve old `PolicyDecision` schema | Compatibility debt | Legacy decisions can be adapted via `from_policy_decision`; route migration remains pending. |
| Invalid/stale/expired policy vocabulary | Block instead of implicit allow | Behavior hardening | This prevents ambiguous or unknown policy states from becoming permission grants. |

## Wave 3 - UniversalTaskRuntime

| Surface | Compatibility Decision | Status | Notes |
|---|---|---|---|
| `TaskRuntimeService.create_run` | Preserve public request/return contract | Compatible | Existing service remains canonical and bootstraps Universal Task identity before persistence. |
| `TaskRunGuard.check_run` | Block orphan or mismatched TaskRun identity | Behavior hardening | Any executable run without `task_id`, `task_run_id`, `operation_id`, or bootstrap context is blocked. |
| Approval runtime context binding | Use canonical `task_id` while preserving `run_id` | Compatible hardening | `ApprovalRequest.run_id` remains task-run reference; `ApprovalRequest.task_id` now receives `run.task_id`. |
| Mobile pipeline status cards | Normalize missing plan/graph status to `unknown` | Compatible | Prevents invalid UI status values such as `none`. |

## Wave 4 - RuntimeTimeline

| Surface | Compatibility Decision | Status | Notes |
|---|---|---|---|
| `TaskRuntimeService.get_timeline` | Preserve public timeline access | Compatible | Timeline remains a projection from TaskRun store/events/artifacts. |
| `SupervisedExecutionLoop.run` | Block execution without initial timeline events | Behavior hardening | Manual stored TaskRuns must carry `run_created` and `task_bootstrap_created` before execution. |
| Historical TaskRun records | Keep readable via timeline fallback | Compatibility debt | Timeline still tolerates `run_id` fallback for old data; execution guard does not tolerate missing initial events. |
| External/agent/debugger events | Preserve separate views temporarily | Compatibility debt | Must become timeline adapters before cleanup. |

## Wave 5 - ArtifactRuntime

| Surface | Compatibility Decision | Status | Notes |
|---|---|---|---|
| `ArtifactRuntimeService.create` | Preserve canonical create API while requiring identity | Behavior hardening | New governed artifacts must include producer step and task/task-run binding. |
| `ArtifactRuntimeService.validate` | Preserve validation return schema | Behavior hardening | Artifacts missing task, task-run, or producer event binding are blocked from evidence use. |
| `UniversalArtifactRegistryService` | Keep as internal registry/store | Compatible internal | It remains the storage implementation behind `ArtifactRuntimeService`, not a second artifact runtime. |
| Runtime Doctor reports | Preserve artifact generation for read-only diagnostics | Compatible hardening | If expected contract lacks Task/TaskRun, Doctor artifacts use declared diagnostic report binding metadata instead of bypassing ArtifactRuntime. |
| Historical/legacy artifact records | Keep readable, not authoritative | Compatibility debt | Old artifacts without event/task binding require backfill before strict Completion/SpeakerTruth reliance. |

## Wave 6 - SpeakerTruth

| Surface | Compatibility Decision | Status | Notes |
|---|---|---|---|
| `RuntimeTruthEngine.evaluate` | Preserve return schema while expanding evidence checks | Behavior hardening | Completed results with orphan artifact evidence are blocked. |
| `CanonicalOperationStateService.derive` | Preserve canonical state schema | Behavior hardening | `COMPLETED` now requires RuntimeTruth safe success, not only `TaskRunResult.status`. |
| `UniversalTaskSessionService` | Preserve public session schema | Compatible hardening | `validation_state` and `result_state` safe-success fields now mirror canonical state. |
| Legacy `SpeakerService` | Keep conversation/preview/block text | Compatibility debt | Must not become operational final-answer authority. |
| Domain-local final answers | Preserve local summaries temporarily | Compatibility debt | Must pass through RuntimeTruth/SpeakerTruth before claiming execution success. |

## Wave 7 - Repositories

| Surface | Compatibility Decision | Status | Notes |
|---|---|---|---|
| `ContextUsageAuditService` | Move physical plan store into canonical context root | Data migrated | `data/runtime/context_plans` moved to `data/runtime/context/plans`; policy and fallback updated. |
| Empty legacy runtime dirs | Archive, do not delete | Compatible cleanup | `tasks`, `artifacts`, and emptied `context_plans` moved under `data/runtime/repository_legacy/empty_dirs`. |
| TaskRun store | Preserve active path | Compatible | `data/runtime/task_runs` remains canonical and active. |
| Approval store | Preserve active path | Compatible | `data/runtime/approvals` remains canonical and active. |
| Event store | Preserve active path | Compatibility debt | `data/runtime/events` remains configured; future wave must adapt to RuntimeTimeline ownership before any move. |
| Artifact preview/write stores | Preserve active paths | Compatibility debt | Configured stores remain until ArtifactRuntime migration covers preview/write lifecycle. |

## Final Compatibility Wave Backlog

Compatibility debt that must not block canonical waves, but must be closed before final architecture:

| ID | Compatibility debt | Closure target |
|---|---|---|
| COMP-001 | Legacy `aipinho.api.routers.chat_router` imports | Migrate imports to canonical lifecycle/public route helpers. |
| COMP-002 | `_persistent_chat_response` helper | Replace with `CanonicalPublicChatService.respond` or public session send route. |
| COMP-003 | `_workspace_context_from_messages` helper under API namespace | Move to canonical conversation/workspace context utility. |
| COMP-004 | Tests expecting approval without executable context | Rewrite around current approval safety contract. |
| COMP-005 | Specialized `ChatOperationRouterService` branches | Compile to `RuntimeContractBundle` and domain handlers. |
| COMP-006 | Direct use of `CanonicalIntentRouter` outside semantic internals | Restrict to `SemanticIntentResolutionService` internals. |
| COMP-007 | Grant action parsing local to chat service | Move to permissions contract/effective policy. |
| COMP-008 | Operational behavior in legacy `ChatService` | Retain only conversation/content-provider behavior. |
| COMP-009 | UI/mobile/launcher state derivation | Consume Universal Task Session + SpeakerTruth only. |
| COMP-016 | Direct `PolicyKernelService` public route use | Adapt through `EffectivePolicyDecisionService` while preserving response schema. |
| COMP-017 | Direct `PolicyKernelService` use in chat/tools/task drafts | Migrate after `RuntimeContractBundle` and preview contract alignment. |
| COMP-018 | Separate multi-agent policy kernel | Fold into participant/capability policy. |
| COMP-019 | Scattered `safe_to_execute` fields | Convert to compatibility mirrors of canonical state. |
| COMP-020 | Raw policy status string checks | Replace with canonical enum adapters. |
| COMP-021 | `run_id` used as `task_id` in runtime/chat/artifact/debug services | Replace with canonical `task_id`; preserve `run_id` lookup aliases. |
| COMP-022 | Manual `TaskRun(...)` construction in tests/services | Replace with bootstrap fixture/factory. Wave 9 introduced canonical test support and fixture identity regression; specialized local constructors remain pending. |
| COMP-023 | Approval continuation task identity fallback | Migrate stored approvals and continuation code to canonical identity. |
| COMP-024 | Mobile endpoint refs using task-run IDs under task labels | Clarify/migrate labels after Universal Task Session alignment. |
| COMP-025 | Separate domain event/timeline systems | Fold into RuntimeTimeline adapters. |
| COMP-026 | Timeline `run_id` fallback as task identity | Backfill/migrate old records and remove fallback. |
| COMP-027 | Local lifecycle/completion state writers | Derive final state from RuntimeTimeline. |
| COMP-028 | Legacy artifact writers using repository/registry/report/export services directly | Migrate to `ArtifactRuntimeService`. |
| COMP-029 | Artifacts missing real producer event binding | Attach/backfill `event_id` from RuntimeTimeline. |
| COMP-030 | Artifact records using `run_id` as `task_id` | Backfill distinct canonical `task_id` and `task_run_id`. |
| COMP-031 | Direct `UniversalArtifactRegistryService` consumers | Convert to ArtifactRuntime lookup/validation adapters. |
| COMP-032 | Legacy `SpeakerService` operational composition | Restrict to conversation/preview adapter and route operational claims through RuntimeTruth. |
| COMP-033 | Separate `CanonicalSpeakerTruthService` lifecycle truth | Adapt lifecycle schema to RuntimeTruth-backed authority. |
| COMP-034 | Domain services with local final answers | Gate execution claims through SpeakerTruth evidence adapters. |
| COMP-035 | Clients reading `TaskRunResult.status` as success | Treat as display mirror; use canonical state for safe success. |

## Wave 7.5 Compatibility Updates

| ID | Status | Notes |
|---|---|---|
| COMP-001 | CLOSED | `aipinho.api.routers.chat_router` imports were migrated and the shim file was removed. |
| COMP-002 | CLOSED | Persistent chat preview/approval test now uses `CanonicalPublicChatService`; persistent route uses canonical public chat service. |
| COMP-003 | CLOSED | Workspace context extraction moved to `PersistentChatWorkspaceContextService`. |
| COMP-021 | PARTIAL | Core runtime/chat artifact/approval publisher paths now separate `task_id` and `task_run_id`; external/manual/debugger domains remain pending. |
| COMP-023 | CLOSED | Approval continuation preserves canonical task identity and resolves linked runs without writing `task_id=run_id`. |
| COMP-015 | CLOSED | Generic runtime test helpers live in `tests/support/runtime_fixtures.py`; `conftest.py` no longer owns or reexports helper logic. |
| COMP-CONTINUE-ALIAS | CLOSED | Legacy package import `continue_integration_router` now aliases `governance_lifecycle_router` without registering a parallel router. |
| Mobile chat broad suite | CLOSED_IN_WAVE_8 | `tests/integration/test_mobile_chat_persistent_humanized_flow.py` now passes as a whole. |

## Wave 8 Compatibility Updates

| ID | Status | Notes |
|---|---|---|
| COMP-010 | PARTIAL | Persistent chat follow-up recall/review now uses `ChatResultIndexService`; semantic contract migration remains pending. |
| COMP-011 | PARTIAL | Persistent chat artifact request/archive operations now go through `CanonicalPublicChatService`; direct ArtifactRuntime migration for all artifact producers remains pending. |
| COMP-014 | PARTIAL | Mobile chat consumes canonical persistent route metadata and passes regression coverage; launcher/client pipeline alignment remains to be proven by dedicated tests. |
| Public lifecycle artifact handling | HARDENED | Artifact Store generation with `requires_task=False` and `workspace_write=False` no longer becomes `write_files` by default. Workspace mutation still requires plan/policy/approval gates. |

## Wave 11 Compatibility Updates

| ID | Status | Notes |
|---|---|---|
| COMP-016 | PARTIAL | Policy resolve/explain endpoints now include `canonical_policy` from `EffectivePolicyDecisionService` while preserving legacy `PolicyDecision` fields. |
| COMP-031 | PARTIAL | Runtime/API artifact reads, lists, provenance, revalidation, task-session aggregation, debugger trace lookup, and Codex delegation lookup now go through `ArtifactRuntimeService`. Creation contracts still use `UniversalArtifactRegistryService` where public requests lack canonical task/run binding. |
| COMP-021 | HARDENED | Universal Task Session artifact state now reports `source=artifact_runtime`; previous registry source string removed from this path. |
| Test profile isolation | HARDENED | Multi-agent artifact/debugger integration test now sets required agent enablement explicitly, avoiding dependence on local operator profile state. |

## Wave 12 Compatibility Updates

| ID | Status | Notes |
|---|---|---|
| COMP-016 | PARTIAL_INTERNAL_ONLY | Public policy router no longer calls `PolicyKernelService` directly. Legacy kernel remains behind `EffectivePolicyDecisionService` as schema-preserving backend. |
| COMP-017 | CLOSED_FOR_NAMED_CONSUMERS | Chat, tools, prompt intelligence, and task draft production consumers now depend on `EffectivePolicyDecisionService` instead of direct `PolicyKernelService`. |
| COMP-022 | CLOSED_FOR_PRODUCTION | Production `TaskRun(...)` construction remains only inside `TaskRuntimeService`; specialized tests still use local constructors as fixture debt. |
| COMP-031 | PARTIAL_HARDENED | Public artifact creation uses `ArtifactRuntimeService` when full task/task-run/producer binding exists; incomplete legacy requests are marked `universal_artifact_registry_compat`. |
| COMP-033 | PARTIAL_HARDENED | `CanonicalSpeakerTruthService` can map `RuntimeTruth` into canonical lifecycle truth; full lifecycle wiring remains pending. |
| Artifact/Public API route dispute | CLOSED | Duplicate `POST /api/v1/artifacts` route now dispatches public-runtime contracts and universal artifact contracts without competing schemas. |
| Path read policy | HARDENED | Direct read validation now treats `requires_governed_approval` roots as protected for direct read access even when `block_task=false`. |
