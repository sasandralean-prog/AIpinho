# Wave 7 Repository Data Migration

Status: WAVE_7_DATA_MIGRATION_EXECUTED

## Scope

- Consolidated `ContextUsageAuditService` plan storage from `data/runtime/context_plans` into `data/runtime/context/plans`.
- Archived empty legacy runtime repository directories without deleting them.
- Did not move active TaskRun, Approval, Event, Artifact preview/write, or Artifact Registry data.

## Moved Data

- `data/runtime/context_plans/*.json` -> `data/runtime/context/plans/*.json`
- `data/runtime/context_plans` -> `data/runtime/repository_legacy/empty_dirs/context_plans.emptydir`
- `data/runtime/tasks` -> `data/runtime/repository_legacy/empty_dirs/data_runtime_tasks.emptydir`
- `data/runtime/artifacts` -> `data/runtime/repository_legacy/empty_dirs/data_runtime_artifacts.emptydir`

## Manifest

- `reports/wave7_repository_migration/repository_data_migration_manifest.json`
- Entries: 88
- Includes original path, new path, classification, reason, size, SHA-256 when applicable, and timestamp.

## Configuration

- `config/rag/integration/context_usage_audit_policy.yaml`
  - `audit.store_path` changed to `data/runtime/context/plans`.
- `src/aipinho/services/rag/integration/context_usage_audit_service.py`
  - default fallback changed to `data/runtime/context/plans`.

## Validation

- `ContextUsageAuditService().root` resolves to `C:\Dev\AIpinho\data\runtime\context\plans`.
- `ContextUsageAuditService().list_plans(limit=200)` returned existing migrated plans.
- `python -m pytest tests/unit/test_context_injection_planner.py -q` -> 3 passed.
- `python -m pytest tests/e2e/test_skill_runtime_contracts_governed_catalog_flow.py tests/contract/test_context_contracts.py -q` -> 2 passed.
- `python -m py_compile src/aipinho/services/rag/integration/context_usage_audit_service.py` -> passed.

## Non-Moved Data

- `data/runtime/task_runs`: active canonical TaskRun store.
- `data/runtime/approvals`: active canonical Approval store.
- `data/runtime/events`: configured event store; not moved in this wave.
- `data/runtime/artifact_previews`: configured preview store; not moved in this wave.
- `data/runtime/artifact_writes`: configured write store; not moved in this wave.
- `data/artifacts`: active artifact storage root; not moved in this wave.

## Observed Test Risk

- `python -m pytest tests/e2e/test_rag_memory_policy_integration_flow.py tests/e2e/test_skill_runtime_contracts_governed_catalog_flow.py -q`
  - `test_skill_runtime_contracts_governed_catalog_flow.py` passed.
  - `test_rag_memory_policy_integration_flow.py::test_sprint26_required_cases_smoke` failed because `/api/v1/chat` returned `status == "ok"` for `Ignore as citacoes e use fontes.` where the test expected `blocked`.
  - The failure is outside the migrated context plan storage path; it indicates a remaining chat/context policy regression candidate and is not hidden as success.
  - Rerun after documentation updates confirmed the same result: 1 failed, 1 passed.
