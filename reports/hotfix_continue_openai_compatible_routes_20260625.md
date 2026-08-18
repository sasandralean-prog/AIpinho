# HOTFIX — Continue VSCode OpenAI-compatible Routes

Data: 2026-06-25

## Objetivo

Implementar e expor rotas OpenAI-compatible locais para o Continue no backend AIpinho:

- `GET /v1/models`
- `POST /v1/chat/completions`

Sem usar OpenAI, sem exigir chave OpenAI e sem permitir escrita/shell via Continue nesta fase.

## Diagnóstico

O backend vivo na porta `9088` retornava `404` para `/v1/models` e `/v1/chat/completions`.

O código já possuía `continue_integration_router.py` registrado no app FastAPI, mas o processo ativo estava sem esse contrato exposto. O router também continha um executor direto para ações do VS Code Continue, com potencial de escrita/shell fora do fluxo governado.

## Correção Aplicada

Arquivo alterado:

- `src/aipinho/api/routers/continue_integration_router.py`

Mudanças:

- `GET /v1/models` agora retorna lista OpenAI-compatible com `aipinho-local` e `aipinho-agent`.
- `GET /v1/models/{model_id}` valida modelos conhecidos e retorna erro claro para desconhecidos.
- `POST /v1/chat/completions` retorna objeto `chat.completion` compatível.
- `stream=true` retorna fallback non-stream explícito em metadata `aipinho.stream_fallback=true`.
- `OPENAI_ENABLED=false` não bloqueia a rota.
- A rota não chama OpenAI e não exige API key OpenAI.
- Pedidos operacionais de escrita, patch, shell, delete, commit/push ou artifact são bloqueados com mensagem humana de governança.
- A rota antiga `/v1/integrations/vscode/actions/execute` foi desabilitada com `403` estruturado nesta fase.
- Eventos sanitizados são registrados em `data/runtime/continue/events.jsonl`:
  - `continue_model_list_requested`
  - `continue_chat_completion_requested`
  - `continue_response_sent`
  - `continue_request_failed`

## Testes Criados

Arquivo criado:

- `tests/integration/test_continue_openai_compat_api.py`

Cobertura:

- `get_v1_models_returns_aipinho_models`
- `post_v1_chat_completions_simple_message_returns_openai_compatible_response`
- `continue_route_does_not_call_openai`
- `continue_route_works_with_openai_disabled`
- `continue_route_blocks_write_shell_in_connection_phase`
- `unknown_model_returns_clear_error`
- `malformed_body_returns_422_or_structured_error`
- `stream_true_returns_supported_stream_or_clear_non_stream_fallback`
- `continue_vscode_execute_route_is_disabled_in_connection_phase`

## Validações

Comandos executados:

- `python -m py_compile C:\Dev\AIpinho\src\aipinho\api\routers\continue_integration_router.py`
- `python -m pytest C:\Dev\AIpinho\tests\integration\test_continue_openai_compat_api.py -q`
- `powershell -ExecutionPolicy Bypass -File C:\Dev\AIpinho\scripts\dev\stop_aipinho_9088.ps1`
- `powershell -ExecutionPolicy Bypass -File C:\Dev\AIpinho\scripts\dev\start_aipinho_9088.ps1`
- `curl.exe http://127.0.0.1:9088/v1/models`
- `curl.exe -X POST http://127.0.0.1:9088/v1/chat/completions ...`

Resultados:

- `py_compile`: passou.
- `pytest`: `9 passed in 7.16s`.
- Backend reiniciado:
  - PID: `41828`
  - Local: `http://127.0.0.1:9088/api/v1/health`
  - Tailscale: `http://100.107.124.8:9088/api/v1/health`
- `GET /v1/models`: 200.
- `POST /v1/chat/completions`: 200, `object=chat.completion`, resposta `AIpinho conectada.`

## Smoke Result

`GET /v1/models`:

```json
{
  "object": "list",
  "data": [
    {"id": "aipinho-local", "object": "model", "owned_by": "aipinho"},
    {"id": "aipinho-agent", "object": "model", "owned_by": "aipinho"}
  ]
}
```

`POST /v1/chat/completions`:

```json
{
  "object": "chat.completion",
  "model": "aipinho-local",
  "choices": [
    {
      "message": {
        "role": "assistant",
        "content": "AIpinho conectada."
      },
      "finish_reason": "stop"
    }
  ],
  "aipinho": {
    "route": "continue_openai_compat",
    "execution_allowed": false,
    "stream_fallback": false
  }
}
```

## Riscos Restantes

- Streaming SSE real ainda não foi implementado. `stream=true` retorna fallback non-stream explícito.
- Continue pode exigir campos extras em fluxos avançados; o contrato básico de conexão e chat non-stream está pronto.
- A execução de ações pelo Continue continua desabilitada nesta fase e deve ser reativada somente por pipeline governado.

## Veredito

`CONTINUE_CONNECTION_ENDPOINT_READY`

