# Chat Task Materialization and Speaker Polling Hotfix

## Verdict

`approved`

## Root Cause

Operational chat requests could reach a valid `TaskPreview`, but the normal chat path returned the preview without creating the canonical `TaskRun` and linked approval. Canonicalized filesystem operations could also miss the governed write adapter because it only recognized the legacy router operation name.

## Corrections

- Chat draft, preview, approval and runtime services now share the same stores and lifecycle services.
- Canonical filesystem create/modify operations can reach the existing governed Tool Gateway.
- Normal-mode operational previews are materialized into a TaskRun. `approval_required` becomes a real `waiting_input` run with `approval_id`; executable previews enter the governed queue according to runtime policy.
- Preview mode remains side-effect free and does not create a TaskRun.
- Public operation aliases are preserved for compatibility while canonical names remain internal.
- Citation bypass detection now requires explicit governed-context semantics and no longer blocks ordinary operational reports that merely say they do not need sources.
- A read-only `TaskSpeakerUpdateService` interprets significant sanitized TaskRun events and exposes incremental messages.
- `GET /api/v1/task-runs/{run_id}/speaker/updates` supports `after_event_id`, cursor continuation, no raw payload, and a 5-second polling contract.
- Launcher Chat and Mobile Chat consume the incremental Speaker feed every five seconds, deduplicated by source event id.

## Files Changed

- `src/aipinho/services/chat/chat_service.py`
- `src/aipinho/services/chat/governed_write_chat_service.py`
- `src/aipinho/services/interpreter/interpreter_service.py`
- `src/aipinho/services/speaker/task_speaker_update_service.py`
- `src/aipinho/services/runtime/supervised_execution_loop.py`
- `src/aipinho/api/routers/task_runtime_router.py`
- `config/runtime/task_speaker_update_policy.yaml`
- `apps/launcher/ui/api/chat_client.py`
- `apps/launcher/ui/tabs/chat_tab.py`
- `apps/mobile/android/app/src/main/java/br/com/aipinho/mobile/network/TaskRuntimeClient.kt`
- `apps/mobile/android/app/src/main/java/br/com/aipinho/mobile/ui/screens/ChatScreen.kt`
- focused Python and Android contract tests.

## Validation

- Python `py_compile`: passed.
- Focused backend/Launcher tests: `22 passed`.
- Android `TaskSpeakerPollingContractTest`: passed; Gradle build successful.
- The CompletionResolver integration initially exposed a real evidence-ordering bug: completed step outputs were only reconstructed after contract evaluation. `SupervisedExecutionLoop` now records sanitized completed/partial outputs in `context.outputs` before completion evaluation.

## Safety

- No prompt, task id, workspace, project name or filename specific rule was introduced.
- Preview mode does not materialize execution.
- Speaker reads sanitized runtime events only and never includes raw metadata.
- Approval remains required where policy requires it.
- Existing Tool Gateway, queue, policy and validation ownership remain canonical.

## Remaining Backlog

No blocking backlog was found in the focused scope. Full-suite sharding remains outside this localized hotfix.
