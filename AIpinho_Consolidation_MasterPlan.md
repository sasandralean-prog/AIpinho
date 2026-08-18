# AIpinho - Consolidation Master Plan

Status: CONSOLIDATION_MASTERPLAN_STARTED

## Objective

Transform AIpinho from a set of overlapping operational paths into one governed runtime architecture.

The consolidation is not a new audit and not a feature sprint. It is a controlled rewire from duplicated/parallel flows into five canonical authorities:

1. `SemanticIntentResolution`
2. `EffectivePolicyDecision`
3. `UniversalTaskRuntime`
4. `RuntimeTimeline`
5. `SpeakerTruth`

## Source Of Truth

Input evidence:

- `AIpinho_Architecture_Audit.md`
- `AIpinho_Architecture_Audit_Consolidated_Report.md`
- Existing code under `src/aipinho`
- Existing configs under `config`
- Existing tests under `tests`

## Non Negotiables

- No big bang migration.
- No third implementation when a canonical implementation already exists.
- No deletion before consumer migration.
- No hardcoded fix for one prompt, provider, workspace, test, or Fire Test.
- Preserve public API compatibility during migration.
- Every temporary adapter must be documented and removable.
- Every removed file must be listed in `AIpinho_RemovedFiles.md`.
- Every behavior change must be listed in `AIpinho_BreakingChanges.md`, even when compatibility is preserved by adapter.

## Target Canonical Flow

Prompt -> Conversation Context -> SemanticIntentResolution -> RuntimeContractBundle -> EffectivePolicyDecision -> ExecutionPlan -> ApprovalRequest when needed -> UniversalTaskRuntime -> RuntimeTimeline -> ArtifactRuntime -> Validation -> Completion -> SpeakerTruth -> Chat/Mobile/API/Launcher

## Waves

| Wave | Domain | Canonical authority | Main goal | Success condition |
|---|---|---|---|---|
| 0 | Control docs | Consolidation control | Create master docs and migration ledger | All consolidation docs exist |
| 1 | Semantic | SemanticIntentResolution | One prompt/intention resolver | No router interprets prompt directly |
| 2 | Policy | EffectivePolicyDecision | One policy/permission/grant decision | No allowed/ask/denied path outside authority |
| 3 | Task Runtime | UniversalTaskRuntime | One task bootstrap/execution authority | No executable operation without task/task_run |
| 4 | Timeline | RuntimeTimeline | One state source | Completion/UI/SpeakerTruth derive from timeline |
| 5 | Artifacts | ArtifactRuntime | One artifact identity/lifecycle | No artifact without producer/task binding |
| 6 | Speaker Truth | SpeakerTruth | One final response authority | Routers/ViewModels do not invent final state |
| 7 | Repositories | Repository consolidation | One store per domain | No duplicate runtime store ownership |
| 8 | Mobile/API/Launcher | Client alignment | Clients consume canonical session | No client-specific state machine |
| 9 | Tests | Coverage matrix | Tests map to contracts/regressions | Started in `AIpinho_TestCoverageMatrix.md`; canonical runtime fixtures moved to `tests/support/runtime_fixtures.py` |
| 10 | Cleanup | Legacy quarantine/removal | Remove migrated shadows | Removed files documented and reversible |

## Current Highest Risk Areas

1. `policy`, `policy_kernel`, `security`, `sandbox`, `approvals`, `config_governance`
2. `chat`, operation routing, permission grant parsing, approval command parsing
3. `runtime`, `task_runs`, `tasks`, `task_drafts`, `orchestration`, `supervisor`, `session`
4. `validation`, `completion`, `speaker`, `mobile_view_models`
5. `artifacts`, `events`, `telemetry`, `runtime_doctor`, `regression`, `replay`
6. Provider-specific external paths: Codex, Gemini, Lucio, agents, connectors

## Canonical Selection Rules

For each domain:

- Canonical: implementation that becomes the only writer/decision maker.
- Adapter: compatibility layer that delegates to canonical implementation.
- Shadow: existing implementation that still has consumers.
- Legacy: implementation whose consumers were migrated.
- Archive: file or module eligible for quarantine/removal after validation.

## Done Criteria

The consolidation is complete only when:

- All five canonical authorities exist in code and are connected.
- All public routes enter through the canonical flow or documented adapter.
- All mutable operations pass through policy, task runtime, timeline, artifacts, validation, and SpeakerTruth.
- Duplicate equivalent classes/functions are migrated or retired.
- Critical hardcodes are replaced by config/contracts/registries/providers.
- Tests prove compatibility and no false success.

## Wave 7 Status

Status: WAVE_7_DATA_MIGRATION_EXECUTED_WITH_RECORDED_REGRESSION

Wave 7 moved only data whose owner and canonical target were clear:

- `data/runtime/context_plans/*.json` -> `data/runtime/context/plans/*.json`
- empty legacy roots -> `data/runtime/repository_legacy/empty_dirs`

No repository facade was retained. Active configured stores were intentionally not moved because their readers/writers remain live and require consumer migration first.

Evidence:

- Migration manifest: `reports/wave7_repository_migration/repository_data_migration_manifest.json`
- Migration report: `reports/wave7_repository_migration/repository_data_migration.md`
- Focused context/contract tests passed.
- One broader chat/context e2e still fails and is tracked as a regression candidate, not as a successful Wave 7 validation.

## Wave 7.5 Status

Status: WAVE_7_5_COMPAT_CLEANUP_IN_PROGRESS

Completed:

- Removed obsolete non-route `api.routers.chat_router` shim after migrating consumers.
- Replaced persistent chat helper usage with `CanonicalPublicChatService` and the canonical persistent chat route.
- Moved persistent chat workspace-context extraction to `PersistentChatWorkspaceContextService`.
- Added config-driven `ContextPromptPolicyService` for RAG/context prompt policy checks.
- Separated canonical `task_id` from TaskRun references in approval continuation, readonly artifact runtime, chat artifact fulfillment, task result publishing, and task block causes.

Evidence:

- 49 focused tests passed.
- Changed runtime services passed `py_compile`.
- `rg` found no source/test import of the removed chat shim.

Known risk:

- The broad mobile chat integration file still contains compatibility failures unrelated to the removed shim. Treat this as Wave 8 client-alignment debt, not as completed cleanup.

## Wave 8 Status

Status: WAVE_8_PUBLIC_CHAT_CLIENT_ALIGNMENT_PASSED_FOCUSED_TESTS

Completed:

- Persistent Mobile/API chat uses canonical public chat adapters for permission status, session diagnostic, artifact generation, filesystem archive, read-only analysis preview, and follow-up recall/review.
- Grounded final answers are indexed with `result_ref_id` before persistent metadata is stored.
- Mobile chat broad regression now passes.
- Artifact Store generation was separated from workspace mutation in public lifecycle evaluation.

Evidence:

- 13 mobile chat integration tests passed.
- 49 Wave 7.5 regression tests passed.
- 33 combined Wave 8 principal tests passed.
- Fake progress marker scan found no matches in `apps` or `src/aipinho`.

Remaining:

- Complete Launcher and External Gateway alignment with dedicated tests.
- Replace `ChatOperationRouterService` compatibility classification with semantic/runtime contract compilation.
