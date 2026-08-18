# External Gateway

Sprint EX1 introduces the canonical entry point for external integrations.

External clients must use the Gateway instead of calling internal Runtime modules directly. The Gateway validates client identity, version, contract shape, and module access before forwarding eligible requests to the Runtime Kernel.

## Components

- `ExternalGateway`
- `GatewaySession`
- `GatewayRequest`
- `GatewayResponse`
- `GatewayContext`
- `GatewayPolicy`

## Supported Clients

- Launcher
- CLI
- VSCode
- Continue
- MCP
- REST
- Web
- Mobile
- Future clients

## Endpoints

- `POST /api/v1/external/gateway`
- `POST /api/v1/external/session`
- `GET /api/v1/external/health`
- `GET /api/v1/external/version`

## Invariants

- No external client receives direct access to internal Runtime modules.
- Contracts are required before Kernel dispatch.
- Forbidden internal targets are blocked before dispatch.
- Responses are governed and auditable.
