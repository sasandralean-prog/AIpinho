# AIpinho - Canonical Directories

Status: CANONICAL_DIRECTORIES_DRAFTED

## Target Ownership

| Domain | Canonical location | Notes |
|---|---|---|
| Semantic intent | `src/aipinho/services/semantic_runtime` | One prompt interpretation authority |
| Runtime contracts | `src/aipinho/schemas/runtime` plus common IDs/states | Versioned bundle |
| Policy decision | `src/aipinho/services/policy` or `policy_kernel` after selection | Only one is canonical |
| Task runtime | `src/aipinho/services/runtime` | Bootstrap, plans, task runs |
| Timeline/events | `src/aipinho/services/telemetry` or runtime timeline module after selection | State source |
| Artifacts | `src/aipinho/services/artifacts` | `ArtifactRuntimeService` owns runtime artifact semantics; registry/store services remain internal |
| Validation/completion | `src/aipinho/services/validation` | Completion derived from timeline |
| Speaker truth | `src/aipinho/services/speaker` | Final answer authority |
| External gateway/connectors | `src/aipinho/services/external_*` after unification | No provider-specific runtime authority |
| Tests support | `tests/support` planned | Shared helpers and fixtures |
| Generated cache | lifecycle/ignored | Not architecture source |

## Directory Rule

A directory may expose adapters, but only one directory owns decisions for its domain.

## Wave 7 Data Directory Decisions

| Data domain | Canonical data location | Decision |
|---|---|---|
| TaskRun runtime data | `data/runtime/task_runs` | Active canonical store, not moved. |
| Approvals | `data/runtime/approvals` | Active canonical store, not moved. |
| Context bundles/traces/plans | `data/runtime/context` | `context_plans` migrated into `data/runtime/context/plans`. |
| Artifact storage | `data/artifacts` | Active artifact storage root, not moved. |
| Empty legacy runtime dirs | `data/runtime/repository_legacy/empty_dirs` | Archived for restoration instead of deletion. |
