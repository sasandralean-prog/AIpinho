# G13 - Legacy Quarantine

Status: G13_LEGACY_QUARANTINE_READY_PARTIAL

## Movido para quarentena

- `config/runtime/runtime_profiles.yaml`
  - destino: `quarantine/legacy/governance/2026-06-26/config/runtime/runtime_profiles.yaml`
  - substituto canonico: `config/governance/runtime_profiles.yaml`
  - motivo: perfil legado mantinha execucao desabilitada e podia conflitar com a policy canonica de runtime.

## Ajuste de conexao

- `src/aipinho/utils/diagnostics.py` deixou de apontar para `config/runtime/runtime_profiles.yaml`.
- Agora aponta para `config/governance/runtime_profiles.yaml`.

## Arquivos nao movidos

Nao foram movidos:

- `src/aipinho/api/routers/chat_router.py`
- `src/aipinho/api/routers/continue_integration_router.py`
- `src/aipinho/services/chat/chat_service.py`
- `src/aipinho/services/chat/chat_operation_router_service.py`
- `src/aipinho/services/chat/chat_permission_grant_service.py`

Motivo: ainda ha imports/endpoints residuais. As rotas publicas criticas ja estao substituidas, mas mover estes arquivos agora quebraria superficie secundaria sem substituto completo.

## Testes depois da quarentena

```text
25 passed in 71.14s
```

## Veredito

A quarentena foi aplicada onde havia substituto seguro. A quarentena completa de routers/services legados fica como pendencia controlada para o proximo bloco.
