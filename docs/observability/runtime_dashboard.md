# Runtime Dashboard

Sprint OB3 adds a read-only observability dashboard for the Runtime.

The dashboard consolidates Runtime Telemetry and Runtime Metrics into queryable views. It never modifies Runtime contracts, execution, approvals, semantic state, or cognitive decisions.

## Components

- `RuntimeDashboardService`
- `DashboardView`
- `DashboardSnapshot`
- `DashboardQuery`
- `DashboardExporter`

## Sections

- Runtime
- Semantic Runtime
- Governed Runtime
- Runtime Doctor
- Patch Intelligence
- Semantic Learning
- Cognitive Governance
- Fire Tests

## Exports

Supported export formats:

- JSON
- CSV
- Markdown

## Endpoints

- `GET /api/v1/runtime/dashboard`
- `GET /api/v1/runtime/dashboard/history`
- `GET /api/v1/runtime/dashboard/export?format=json|csv|markdown`

## Invariants

- Dashboard is read-only.
- Snapshots are derived from telemetry and metrics.
- Exports are deterministic.
- No execution, contract, approval, or runtime state can be modified by the dashboard.
