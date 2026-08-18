# Runtime Metrics

Sprint OB2 adds structured Runtime metrics derived from Runtime Telemetry.

The metrics layer does not alter Runtime decisions, contracts, semantic runtime, cognitive governance, executors, or task state. It aggregates observed telemetry events into reproducible snapshots.

## Components

- `RuntimeMetricsService`
- `MetricsCollector`
- `MetricsAggregator`
- `MetricsSnapshot`
- `MetricsHistory`
- `RuntimeHealth`
- `RuntimePerformance`
- `RuntimeEfficiency`

## Metrics

The service calculates:

- latency and total duration
- time by role
- time by model
- inference events
- contract events
- artifact events
- Fire Test events
- regression events
- patch plan events
- semantic recommendation events
- escalation events
- approval events

## Endpoints

- `GET /api/v1/runtime/metrics`
- `GET /api/v1/runtime/metrics/history`
- `GET /api/v1/runtime/health`

## Invariants

- Metrics are derived from telemetry only.
- Metrics do not mutate Runtime.
- Snapshots are stored historically.
- Health is computed from observed severity signals.
