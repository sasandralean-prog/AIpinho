# AIpinho - Breaking Changes Ledger

Status: NO_BREAKING_CHANGES

No breaking changes have been introduced by this consolidation start.

## Compatibility Policy

- Preserve public routes.
- Preserve response contracts during migration.
- Use adapters only as temporary compatibility layers.
- Document behavior changes even when routes remain compatible.

## Required Entry Format

| Date | Change | Affected clients | Compatibility adapter | Tests | Rollback |
|---|---|---|---|---|---|

| 2026-07-31 | Wave 1 semantic intent entrypoint introduced | Internal lifecycle/chat services | `SemanticIntentResolutionService`; non-route `chat_router` shim | 96 focused passed; 18 governance regression passed | Revert Wave 1 files if semantic delegation causes regression |
| 2026-07-31 | Wave 2 effective policy decision boundary introduced | Internal lifecycle/governance policy services | `EffectivePolicyDecisionService`; `CanonicalPolicyService` retained internally; `PolicyKernelService` adaptation available | 25 policy/lifecycle passed; 16 policy kernel passed; 24 governance regression passed | Revert Wave 2 policy service/lifecycle import and canonical policy hardening |
| 2026-07-31 | Wave 3 runtime bootstrap guard enforced | Internal TaskRun execution/start paths | `TaskRuntimeService.create_run` continues to bootstrap; lookup still accepts task_id/run_id/task_run_id aliases | 40 Wave 3 passed; 40 expanded runtime passed; 43 lifecycle/policy regression passed | Revert TaskRunGuard identity checks and approval task_id binding if bootstrap identity causes regression |
| 2026-07-31 | Wave 4 runtime timeline execution guard introduced | Internal supervised execution loop | `TaskRuntimeService.create_run` already creates required initial events; historical records remain readable | 12 loop/timeline passed; 36 runtime/session passed; 19 event/result/contracts passed | Revert SupervisedExecutionLoop timeline bootstrap check if legacy execution migration is needed |
| 2026-07-31 | Wave 5 artifact runtime evidence binding enforced | Internal artifact creation/validation through `ArtifactRuntimeService` | Historical artifacts remain readable; strict validation blocks orphan evidence | 13 artifact/timeline passed; 23 vertical/doctor/operator passed; 10 artifact bridge/export passed; 43 lifecycle/policy passed | Revert ArtifactRuntime create/validate hardening and Runtime Doctor diagnostic binding if artifact producers regress |
| 2026-07-31 | Wave 6 runtime truth required for canonical completion | Internal canonical state and Universal Task Session views | Public schemas preserved; result status remains visible, safe success mirrors canonical state | 23 truth/session/consistency passed; 17 operator/timeline passed; 26 vertical/lifecycle passed; 26 public/operator/session passed; 23 policy/read-only passed | Revert RuntimeTruth artifact checks, canonical completion truth requirement, and session safe-success mirroring |
| 2026-07-31 | Wave 7 context plan store physically migrated | Context usage audit storage | Manifest-backed move; old empty directory archived under `data/runtime/repository_legacy/empty_dirs` | 3 context planner passed; 2 context/skill tests passed; py_compile passed; one broad chat/context e2e failed outside path migration | Restore files from `reports/wave7_repository_migration/repository_data_migration_manifest.json` and revert context usage policy path |
| 2026-07-31 | Wave 7.5 removed obsolete non-route chat shim and separated several task/run identities | Internal tests/imports and runtime metadata consumers | Public chat route and `CanonicalPublicChatService` preserved; `result_ref_id`/`task_run_id` remain execution references | 49 focused tests passed; full mobile chat file has unrelated compatibility failures recorded as risk | Restore shim only as a temporary non-route import adapter if a missed consumer is found, then migrate that consumer |
| 2026-07-31 | Wave 8 aligned persistent mobile/API chat with canonical public chat adapters | Persistent chat/mobile view-model consumers | Public route unchanged; metadata and `result_ref_id` are enriched, not removed | 13 mobile chat integration passed; 49 Wave 7.5 regressions passed; 33 combined Wave 8 principal passed | Revert Wave 8 service additions and public lifecycle artifact distinction if a client depends on old degraded behavior |

Notes:

- No public endpoint was intentionally removed or changed in this wave.
- No new legacy chat endpoint was registered.
- Existing stricter approval behavior remains: mutable approval creation requires executable context and may block old tests that expected approval without `context_ref`.
- Behavior hardening: invalid, stale, or expired policy vocabulary is now blocked instead of potentially resolving as `allowed`.
- Behavior hardening: executable TaskRuns without canonical bootstrap identity are now blocked by `TaskRunGuard`.
- Behavior hardening: executable TaskRuns without initial timeline events are now blocked by `SupervisedExecutionLoop`.
- Behavior hardening: governed artifacts without task, task-run, or producer event binding cannot be used as authoritative evidence.
- Behavior hardening: completed result records cannot produce canonical completion or public safe-success unless RuntimeTruth agrees.
- Data migration: `data/runtime/context_plans` moved to `data/runtime/context/plans` with reversible manifest.
- Internal cleanup: `api.routers.chat_router` was removed after import migration. No public route was removed.
- Client alignment: persistent chat artifact-store outputs no longer require workspace-write executable plans when `requires_task=False`, `workspace_write=False`, and validation evidence is present.
