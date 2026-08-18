# PinhoForge Provider Discovery

A AIpinho registra o PinhoForgeStudio2 como provider externo em modo de descoberta.

Fluxo:

1. Lê `config/providers/pinhoforge_bridge.yaml`.
2. Resolve `PINHOFORGE_BRIDGE_MANIFEST_PATH` ou `runtime.manifest_path`.
3. Valida `PinhoForgeBridgeManifest`.
4. Expõe status sanitizado via `/api/v1/pinhoforge-bridge/status`.
5. Bloqueia execução com `pinhoforge_bridge_execution_disabled`.

Execução real permanece fora de escopo nesta fase.

