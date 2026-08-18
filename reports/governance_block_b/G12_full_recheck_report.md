# G12 - Full Recheck

Status: G12_FULL_RECHECK_READY_WITH_RESIDUAL_LEGACY

## Escopo rechecado

- Rotas publicas criticas.
- Lifecycle canonico em chat direto, chat persistente e Continue/OpenAI-compatible.
- Trace canonico de intent, policy, plan, approval e completion.
- Import/bypass basico de rotas legadas.
- Configs duplicadas de runtime.

## Rotas criticas

As primeiras rotas registradas no FastAPI para estes endpoints pertencem a `governance_lifecycle_router`:

- `POST /api/v1/chat`
- `POST /api/v1/chat/sessions/{session_id}/send`
- `POST /v1/chat/completions`
- `POST /v1/integrations/continue/chat`

## Configs

`config/runtime/runtime_profiles.yaml` era um perfil legado com execucao desabilitada. Foi substituido por:

- `config/governance/runtime_profiles.yaml`

`src/aipinho/utils/diagnostics.py` agora aponta para a fonte canonica.

## Testes executados

```text
python -m py_compile C:\Dev\AIpinho\src\aipinho\utils\diagnostics.py C:\Dev\AIpinho\src\aipinho\services\governance\lifecycle\canonical_public_chat_service.py C:\Dev\AIpinho\src\aipinho\services\governance\intent\canonical_intent_router.py

python -m pytest tests\governance\test_lifecycle_core.py tests\governance\test_g11_canonical_public_routes.py tests\governance\test_g7_functional_route_rewire.py tests\governance\test_g12_full_recheck.py tests\governance\test_canonical_lifecycle_trace.py tests\governance\test_no_legacy_operational_bypass.py tests\governance\test_legacy_import_forbidden.py tests\integration\test_chat_api.py::test_post_chat_greeting_200 tests\integration\test_chat_api.py::test_chat_status_200 tests\integration\test_chat_runtime_parity_api.py::test_no_silent_message_after_persistent_chat_send -q
```

Resultado:

```text
25 passed in 71.14s
```

## Ponto residual

Os routers legados `chat_router.py` e `continue_integration_router.py` ainda estao montados para endpoints residuais. Eles nao sao os primeiros donos das rotas publicas criticas, mas ainda nao podem ser movidos para quarentena sem mapear/substituir todos os endpoints secundarios.
