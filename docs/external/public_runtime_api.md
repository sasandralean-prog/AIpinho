# Public Runtime API

Sprint EX3 introduces the official public API for AIpinho automations and external integrations.

The public API is contract-based and routes all operational requests through:

Public Runtime API -> External Gateway -> Runtime Kernel

## Endpoints

- `POST /api/v1/chat`
- `POST /api/v1/execute`
- `POST /api/v1/analyze`
- `POST /api/v1/doctor`
- `POST /api/v1/validate`
- `POST /api/v1/artifacts`
- `GET /api/v1/runtime`
- `GET /api/v1/modules`
- `GET /api/v1/contracts`
- `GET /api/v1/health`
- `GET /api/v1/version`

## Public Contracts

Each operation uses a public contract version and a gateway-compatible request. Internal Runtime contracts remain isolated behind the Gateway and Kernel.

## Compatibility

Designed for Launcher, Mobile, Web, CLI, VSCode, Continue, MCP, external agents, and automation tools.

## Invariants

- Public requests pass through Gateway.
- Gateway dispatches through Runtime Kernel.
- Public API records audit and telemetry.
- Kernel remains isolated from external clients.
