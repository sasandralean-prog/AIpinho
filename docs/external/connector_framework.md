# External Connector Framework

Sprint EX2 introduces a standard framework for external connectors.

Connectors isolate external clients from the Runtime. They normalize client capabilities and contracts, then communicate through the External Gateway. They do not interpret prompts, execute Runtime modules, or modify contracts.

## Components

- `ConnectorFramework`
- `ConnectorRegistry`
- `ConnectorContract`
- `ConnectorCapabilities`
- `ConnectorLifecycle`
- `ConnectorContext`

## Official Connectors

- LauncherConnector
- CLIConnector
- VSCodeConnector
- ContinueConnector
- RESTConnector
- WebConnector
- MobileConnector
- MCPConnector

## Endpoints

- `GET /api/v1/external/connectors`
- `POST /api/v1/external/connectors/register`
- `GET /api/v1/external/connectors/{id}`

## Invariants

- Connectors never execute Runtime.
- Connectors never modify contracts.
- Connectors never interpret prompts.
- All connector communication flows through the External Gateway.
