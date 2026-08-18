# PinhoForge Bridge Policy

Política atual:

- `handshake`, `health`, `manifest` e `readiness`: permitidos como operações read-only.
- `execute`: bloqueado.
- Raw fica escondido por padrão.
- Segredos não são expostos.
- Manifest inválido gera status estruturado.

A política é configurável em `config/providers/pinhoforge_bridge.yaml`.

