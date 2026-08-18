# Runtime Telemetry

Sprint OB1 introduces the first Runtime observability layer.

Runtime Telemetry is read-only with respect to Runtime behavior. It records observations about governed execution without modifying contracts, semantic runtime, governed runtime, cognitive governance, executors, or task state.

## Components

- `TelemetryEvent`
- `TelemetrySession`
- `TelemetryRecordRequest`
- `TelemetryQuery`
- `TelemetryRepository`
- `TelemetryCollector`
- `TelemetrySerializer`
- `RuntimeTelemetryService`

## Event Fields

Each event contains:

- `event_id`
- `timestamp`
- `category`
- `origin`
- `module`
- `event_type`
- `severity`
- `correlation_id`
- `session_id`
- `task_run_id`
- `task_id`

## Categories

Telemetry supports task, task run, session, intent, ISR, contracts, roles, model selection, routing, escalation, Runtime Doctor, Fire Tests, artifacts, validation, completion, Speaker Truth, and governance.

## Endpoints

- `GET /api/v1/runtime/telemetry`
- `GET /api/v1/runtime/telemetry/session/{id}`
- `POST /api/v1/runtime/telemetry/query`
- `POST /api/v1/runtime/telemetry/events`

The legacy endpoint `GET /api/v1/telemetry/events` remains available as a read-only compatibility view.

## Invariants

- Telemetry never mutates Runtime.
- Events are correlation-friendly.
- Sessions aggregate by session id or correlation id.
- Serialization is structured and deterministic.
