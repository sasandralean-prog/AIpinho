# AIpinho PinhoForge Bridge Protocol

Endpoints adicionados:

- `GET /api/v1/pinhoforge-bridge/status`
- `POST /api/v1/pinhoforge-bridge/handshake`
- `GET /api/v1/pinhoforge-bridge/health`
- `GET /api/v1/pinhoforge-bridge/manifest`
- `GET /api/v1/pinhoforge-bridge/readiness`
- `POST /api/v1/pinhoforge-bridge/execute`

`execute` é intencionalmente bloqueado. Essa rota serve para provar que a AIpinho não tenta acionar o PinhoForge como ferramenta operacional antes de existir execução governada.

