# Multi-Agent Event Bus

Sprint 2 adds a shared event bus and incremental timeline on top of the Sprint 1 Agent Session Kernel.

## Purpose

Every agent run can now publish audit-safe incremental events. Mobile, Launcher and future Workbench surfaces can poll a session or run and render progress without waiting for one final message.

The implementation does not add Tool Gateway, full delegation, Lucio runtime, Codex executor or Gemini executor behavior. It is a timeline contract and persistence layer.

## Event Model

`AgentEvent` includes:

- `event_id`;
- `run_id`;
- `session_id`;
- `agent_id`;
- `sequence` monotonic per run;
- `session_sequence` monotonic per session;
- `event_type`;
- `status`;
- `severity`;
- `human_message`;
- `technical_summary_sanitized`;
- `payload_sanitized`;
- `created_at`;
- `visible_in_timeline`;
- `evidence_refs`;
- optional correlation/tool/delegation/approval/validation/artifact/progress/raw references.

Raw references are not exposed in normal cards.

## Event Bus

`MultiAgentEventBus` provides:

- `append_event`;
- `append_status_event`;
- `append_error_event`;
- `list_events_by_run`;
- `list_events_by_session`;
- `get_latest_event`;
- `get_last_sequence`.

The bus stores events through `AgentSessionStore`.

## Ordering

- `sequence` is monotonic inside each run.
- `session_sequence` is monotonic across all runs in one agent session.
- Duplicate `event_id` append returns the already persisted event.

## Incremental Polling

Supported cursors:

- `after_event_id`;
- `after_sequence`;
- `limit`.

Polling contract:

```json
{
  "enabled": true,
  "recommended_interval_seconds": 5,
  "reason": "active_run",
  "stop_when_status_in": ["completed", "completed_with_warnings", "failed", "blocked", "cancelled"]
}
```

## Endpoints

- `POST /api/v1/agents/runs/{run_id}/events`
- `GET /api/v1/agents/runs/{run_id}/events?after_event_id=&after_sequence=&limit=&mode=`
- `GET /api/v1/agents/{agent_id}/sessions/{session_id}/timeline?after_event_id=&after_sequence=&limit=&mode=`
- `GET /api/v1/mobile/agents/{agent_id}/view-model?session_id=&after_event_id=&mode=`

## Timeline Mapper

`AgentEventTimelineMapper` converts events into safe cards:

- title;
- body;
- severity;
- status;
- copy_text;
- raw_available;
- details only when `mode=details` or `mode=raw`.

Normal mode hides raw references and technical metadata.

## State Aggregation

Session state now considers run status and event-derived status.

Precedence:

`blocked > failed > validation_failed > pending_approval > pending_validation > applying > running > preview_created > cancelled > completed_with_warnings > completed > idle`

This prevents simple chat completion from hiding pending approval, validation failures or blocked policy events.

## Sanitization

Human message, technical summary and payload pass through the existing `redact_payload` path.

The tests verify redaction for bearer-like secrets and hidden raw behavior.

## Compatibility

Existing AIpinho chat, mobile view-model, Codex mobile executor and Gemini executor tests were rerun and remain green.

## Sprint 3 Next Step

Sprint 3 can connect real runtimes more deeply:

- publish live events from chat/task/Codex/Gemini paths;
- connect mobile/launcher polling to these endpoints;
- keep governed autorun as a productive path instead of approval bureaucracy.

## Sprint 3 - Tool Gateway Events

O Tool Gateway multi-agent emite eventos no Event Bus usando `tool_invocation_id`, `artifact_ids`, `validation_id` e payload sanitizado. Eventos de shell stdout/stderr ficam disponiveis em details/raw, mas nao precisam aparecer no modo normal.

Eventos principais: `tool_invocation_created`, `tool_policy_check_started`, `tool_policy_check_completed`, `tool_auto_approved`, `tool_approval_required`, `tool_blocked`, `tool_started`, `tool_succeeded`, `tool_failed`, `shell_started`, `shell_stdout`, `shell_stderr`, `shell_finished`, `artifact_created`.

