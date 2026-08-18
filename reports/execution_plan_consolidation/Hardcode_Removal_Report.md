# Hardcode Removal Report

## Hardcodes Addressed

### Operation Identity

Previous behavior could leave `operation_type` unset while execution still proceeded under `contract_type`.

Change:

- `TaskRuntimeService` now derives an effective operation type from structured request fields:
  - `operation_type`
  - `intent_map.operation_type`
  - `intent_map.intent_type`
  - `contract_type`

This is not path-based and does not inspect prompt text.

### Event Catalog

New canonical event names are declared in:

- `config/runtime/task_run_event_policy.yaml`
- `config/runtime/task_speaker_update_policy.yaml`

The runtime does not bypass event validation.

### Public Status Shape

`/api/v1/tools/execution-status` now reuses `ReadOnlyExecutionService.status()` and exposes compatibility keys without duplicating service logic.

### Prompt/Intent Runtime Fallback

`GovernedTaskStepRunner` no longer falls back to:

- `intent_map.raw_prompt`
- session recent user messages

Execution objective now comes from `CanonicalExecutionPlan.semantic_goal`.

Structured shell plans and read-only report metadata are moved into the ExecutionPlan during promotion.

## Hardcodes Not Introduced

No new logic was added based on:

- prompt text;
- Fire Test names;
- workspace paths;
- file names;
- model names;
- provider names.

## Remaining Candidates

Later cleanup should continue reviewing:

- legacy executable-plan reference strings in approval previews;
- old runtime event names that remain for compatibility;
- historical tool execution IDs separate from TaskRun execution_id;
- patch/runtime schemas that still predate the canonical ExecutionPlan boundary.
