# Sprint 25 — Model Registry Summary

O Sprint 25 não substituiu o registry existente. Ele adicionou uma camada de capability routing sobre:

- `config/models/model_registry.yaml`
- `config/models/provider_registry.yaml`
- `config/models/capability_router.yaml`
- `config/models/fallbacks.yaml`

Use:

- `GET /api/v1/models/registry` para modelos/providers.
- `GET /api/v1/models/router` para route matrix e roles.
- `GET /api/v1/capabilities/health` para estado por capability.
