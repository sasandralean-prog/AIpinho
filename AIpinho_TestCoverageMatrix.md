# AIpinho Test Coverage Matrix

Status: WAVE_9_CANONICAL_TEST_MATRIX_STARTED

This matrix maps regression tests to canonical contracts, runtime authorities, and known compatibility debts. It is not a parallel source of behavior. It is the test-side index used to verify that the consolidation waves keep moving toward the canonical flow.

## Canonical Authorities Covered

| Authority | Primary contract covered by tests | Representative suites |
|---|---|---|
| SemanticIntentResolution | Prompt classification must compile to contract-compatible intent without direct execution | `tests/governance/test_runtime_vertical_slice.py`, `tests/unit/test_intelligent_planner_service.py` |
| EffectivePolicyDecision | Dangerous actions require canonical policy/approval state; read-only stays non-mutating | `tests/unit/test_task_run_guard.py`, `tests/unit/test_workspace_permission_matrix_service.py`, `tests/unit/test_governed_approval_continuation.py` |
| UniversalTaskRuntime | Executable operations require task/run identity, plan, queue, lifecycle, and context | `tests/unit/test_task_runtime_service.py`, `tests/unit/test_universal_task_session_service.py`, `tests/unit/test_runtime_operator_ro.py` |
| RuntimeTimeline | Events and lifecycle state must be observable and ordered | `tests/unit/test_runtime_timeline_service.py`, `tests/unit/test_task_run_event_service.py`, `tests/unit/test_runtime_consistency_bindings.py` |
| SpeakerTruth | Final answer and client-visible success must derive from runtime evidence | `tests/unit/test_task_run_chat_result_publisher_service.py`, `tests/unit/test_workflow_truth_runtime.py`, `tests/integration/test_mobile_chat_persistent_humanized_flow.py` |

## Contract Coverage Matrix

| Test file | Contract/regression guarded | Canonical owner | Modules under test | Status |
|---|---|---|---|---|
| `tests/governance/test_runtime_vertical_slice.py` | Read-only analysis may generate Artifact Runtime outputs without workspace mutation | SemanticIntentResolution, ArtifactRuntime, UniversalTaskRuntime | governance lifecycle, artifact runtime, public route lifecycle | KEEP |
| `tests/unit/test_runtime_test_support_fixtures.py` | Shared test fixtures must preserve distinct `task_id`, `task_run_id`, `operation_id`, and bootstrap context | UniversalTaskRuntime | `tests/support/runtime_fixtures.py` | ADDED_WAVE_9 |
| `tests/unit/test_task_run_store.py` | TaskRun persistence and lookup remain compatible with canonical identity | UniversalTaskRuntime | task run store | KEEP |
| `tests/unit/test_task_runtime_service.py` | TaskRun creation, policy snapshot, preview execution, and runtime request handling | UniversalTaskRuntime, EffectivePolicyDecision | task runtime service | KEEP |
| `tests/unit/test_task_queue_service.py` | Queue progression respects lifecycle and blocked/approval state | UniversalTaskRuntime, RuntimeTimeline | task queue service | KEEP |
| `tests/unit/test_task_run_guard.py` | Guard blocks unsafe execution and requires approved policy state | EffectivePolicyDecision, UniversalTaskRuntime | task run guard | KEEP |
| `tests/unit/test_workspace_permission_matrix_service.py` | Workspace permission matrix denies/asks deterministically by role and operation | EffectivePolicyDecision | workspace permission matrix, workspace roles, runtime profiles | KEEP_WITH_REFACTOR |
| `tests/unit/test_governed_approval_continuation.py` | Approval continuation preserves task identity and does not create orphan continuation runs | EffectivePolicyDecision, UniversalTaskRuntime | approval continuation, task preview/runtime stores | KEEP_WITH_REFACTOR |
| `tests/unit/test_hotfix_executable_approval_resume.py` | Executable approval resume requires real plan/context and cannot bypass gates | EffectivePolicyDecision, UniversalTaskRuntime | approval command/continuation services | KEEP |
| `tests/unit/test_universal_task_session_service.py` | Universal Task Session progress derives from real plan/result state | UniversalTaskRuntime, RuntimeTimeline | universal task session service | KEEP_WITH_REFACTOR |
| `tests/unit/test_runtime_operator_ro.py` | Runtime Operator consumes governed task context and does not invent runtime state | UniversalTaskRuntime | runtime operator services | KEEP |
| `tests/unit/test_runtime_timeline_service.py` | Runtime events provide ordered task execution history | RuntimeTimeline | timeline/event services | KEEP |
| `tests/unit/test_task_run_event_service.py` | Task events persist through canonical run identity | RuntimeTimeline | event service | KEEP |
| `tests/unit/test_runtime_consistency_bindings.py` | Lifecycle/completion/validation bindings remain aligned | RuntimeTimeline, SpeakerTruth | lifecycle, completion, validation state adapters | KEEP |
| `tests/unit/test_task_run_chat_result_publisher_service.py` | Chat result publication uses grounded runtime evidence and distinct task/run identity | SpeakerTruth, UniversalTaskRuntime | chat result publisher | KEEP |
| `tests/unit/test_workflow_truth_runtime.py` | Workflow truth cannot report success without required outputs | SpeakerTruth, Validation | truth runtime, workflow execution | KEEP |
| `tests/integration/test_mobile_chat_persistent_humanized_flow.py` | Mobile/API chat persistence, recall, artifacts, and client metadata consume canonical public chat flow | SpeakerTruth, UniversalTaskRuntime, ArtifactRuntime | canonical public chat service, lifecycle router, chat persistence | KEEP |
| `tests/e2e/test_rag_memory_policy_integration_flow.py` | Context prompt policy and memory/RAG enrichment remain governed and non-bypassable | SemanticIntentResolution, EffectivePolicyDecision | context prompt policy, RAG/memory services | KEEP |

## Test Support Consolidation

| Debt | Before Wave 9 | Wave 9 result | Remaining action |
|---|---|---|---|
| COMP-015 | Generic runtime helpers lived directly in `tests/conftest.py` and encouraged copy/paste | Wave 10 migrated the remaining direct imports and removed the `conftest.py` reexport | CLOSED |
| COMP-022 | Several tests still construct `TaskRun(...)` directly with local defaults | Added regression asserting canonical test fixture identity and bootstrap invariants | Replace local `_run()` constructors when their behavior matches the canonical fixture; keep specialized constructors only when they model domain-specific state |

## Known Gaps

| Gap | Risk | Planned handling |
|---|---|---|
| Local `_run()` helpers in approval, project generation, universal session, workspace matrix, and blocked-task tests | Medium: repeated identity defaults can drift from UniversalTaskRuntime | Migrate case by case after confirming each helper is not modeling unique domain state |
| Direct `from conftest import ...` imports | Closed: no direct imports remain | Keep `tests/support/runtime_fixtures.py` as canonical helper owner |
| Historical runtime fixtures with `run_id`-as-`task_id` aliases | Medium: can mask identity regressions | Keep explicit COMP-021/COMP-022 backlog until data and tests are fully migrated |
| Broad test inventory has 1024 files | Medium: full matrix cannot be completed safely in a single edit pass | Expand this matrix by canonical domain in future waves, not by bulk/generated documentation |

## Validation Commands

| Command | Result |
|---|---|
| `python -m py_compile tests\support\runtime_fixtures.py tests\unit\test_runtime_test_support_fixtures.py tests\conftest.py` | PASSED |
| `python -m pytest tests\unit\test_runtime_test_support_fixtures.py -q` | 2 passed |
| `python -m pytest tests\unit\test_task_run_store.py tests\unit\test_task_run_guard.py tests\unit\test_task_run_result_service.py -q` | 17 passed |
| `python -m pytest tests\unit\test_runtime_test_support_fixtures.py tests\unit\test_task_run_store.py tests\unit\test_task_run_guard.py tests\unit\test_task_run_result_service.py tests\unit\test_task_queue_service.py tests\unit\test_task_run_lifecycle_service.py tests\unit\test_task_run_event_service.py -q` | 31 passed |
| `python -m pytest tests\unit\test_task_runtime_service.py tests\unit\test_runtime_operator_ro.py tests\unit\test_universal_task_session_service.py tests\unit\test_task_run_chat_result_publisher_service.py -q` | 32 passed |
| `python -m pytest tests\governance\test_runtime_vertical_slice.py tests\unit\test_runtime_operator_ro.py tests\unit\test_governed_approval_continuation.py tests\unit\test_hotfix_executable_approval_resume.py tests\unit\test_task_run_chat_result_publisher_service.py tests\unit\test_sprint45_2_blocked_task_explainability.py tests\e2e\test_rag_memory_policy_integration_flow.py tests\unit\test_context_prompt_policy_service.py tests\unit\test_persistent_chat_workspace_context.py tests\unit\test_hotfix_approval_bootstrap_phase_resume.py::test_phase_resume_persistent_chat_uses_canonical_preview_approval_flow -q` | 49 passed |
| `python -m pytest tests\unit\test_continuous_collaboration_runtime.py tests\unit\test_continuous_runtime_service.py tests\unit\test_task_run_store.py tests\unit\test_task_run_guard.py tests\unit\test_task_run_result_service.py tests\unit\test_task_run_chat_result_publisher_service.py tests\unit\test_task_runtime_service.py -q` | 43 passed |
