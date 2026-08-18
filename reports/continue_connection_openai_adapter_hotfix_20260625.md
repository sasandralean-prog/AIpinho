# HOTFIX — Continue 2.0.0 OpenAI-compatible Adapter

Data: 2026-06-25

## Objetivo

Fazer o Continue VS Code 2.0.0 conversar com a AIpinho via provider `openai`, usando:

- `apiBase: http://127.0.0.1:9088/v1`
- `model: aipinho-local`
- sem OpenAI pago;
- sem chamada a OpenAI;
- sem escrita/shell/patch via rota Continue nesta fase;
- com suporte a `stream=true` em SSE.

## Causa Raiz

Havia dois problemas:

1. O processo vivo retornava `404` para `/v1/models` e `/v1/chat/completions` antes do hotfix anterior/restart.
2. O Continue 2.0.0 chama `chatCompletionStream`, portanto `stream=true` precisa responder `text/event-stream`. O adapter anterior aceitava `stream=true`, mas devolvia JSON non-stream.

Tambem havia documentacao antiga apontando `http://127.0.0.1:8088/v1`, enquanto o backend real da AIpinho usa `9088`.

## Porta Escolhida

Porta oficial do adapter:

- `http://127.0.0.1:9088/v1`

Nao foi criado proxy separado em `8088`.

## Endpoints Implementados

- `GET /v1/models`
- `GET /v1/models/{model_id}`
- `POST /v1/chat/completions`

`POST /v1/chat/completions` agora suporta:

- `stream=false`: JSON OpenAI-compatible.
- `stream=true`: SSE com `chat.completion.chunk` e `data: [DONE]`.

## Arquivos Alterados

- `src/aipinho/api/routers/continue_integration_router.py`
- `tests/integration/test_continue_openai_compat_api.py`
- `docs/integrations/continue_vscode_aipinho.md`

## Comportamento de Seguranca

- Nao usa OpenAI.
- Nao exige chave OpenAI.
- Se `CONTINUE_API_TOKEN` estiver configurado, aceita `Authorization: Bearer <token>`.
- Em desenvolvimento local, `aipinho-local-token` pode ser aceito quando permitido por env.
- Nao executa escrita, shell, patch, delete, commit/push ou artifact pela rota Continue.
- Pedidos operacionais retornam mensagem humana dizendo que a acao exige o fluxo governado da AIpinho.

## Testes Executados

Comandos:

- `python -m py_compile C:\Dev\AIpinho\src\aipinho\api\routers\continue_integration_router.py`
- `python -m pytest C:\Dev\AIpinho\tests\integration\test_continue_openai_compat_api.py -q`

Resultado:

- `py_compile`: passou.
- `pytest`: `14 passed in 6.09s`.

Cobertura:

- models retorna 200.
- models contem `aipinho-local`.
- chat non-stream retorna OpenAI-compatible.
- chat stream retorna SSE chunks.
- stream termina com `data: [DONE]`.
- prompt simples `Ola` responde.
- modelo desconhecido retorna erro claro.
- payload malformado retorna 422/erro estruturado.
- nao chama OpenAI.
- funciona com `OPENAI_ENABLED=false`.
- nao escreve arquivos.
- nao roda shell.
- documentacao aponta para `9088`, nao `8088`.

## Smoke Curl

Backend reiniciado:

- PID: `49528`
- Local: `http://127.0.0.1:9088/api/v1/health`
- Tailscale: `http://100.107.124.8:9088/api/v1/health`

`GET /v1/models`:

```json
{"object":"list","data":[{"id":"aipinho-local","object":"model","owned_by":"aipinho"},{"id":"aipinho-agent","object":"model","owned_by":"aipinho"}]}
```

`POST /v1/chat/completions` com `stream=false`:

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
  ]
}
```

`POST /v1/chat/completions` com `stream=true`:

```text
data: {"object":"chat.completion.chunk", ... "delta":{"role":"assistant"}}

data: {"object":"chat.completion.chunk", ... "delta":{"content":"Ola."}}

data: {"object":"chat.completion.chunk", ... "delta":{},"finish_reason":"stop"}

data: [DONE]
```

## Smoke Continue Real

Nao foi executado clique real dentro do VS Code nesta rodada. O contrato que o Continue 2.0.0 usa (`provider: openai`, `useOpenAIAdapter: true`, `streamEnabled: true`, `llm/streamChat`) foi validado por HTTP com `curl -N`.

## Config Continue Final

Use:

```yaml
models:
  - name: AIpinho Local
    provider: openai
    model: aipinho-local
    apiBase: http://127.0.0.1:9088/v1
    apiKey: aipinho-local-token
```

## Limitacoes

- O streaming atual e fallback chunked a partir da resposta completa quando o runtime interno nao produz stream nativo.
- A UI real do Continue ainda precisa ser testada manualmente apos recarregar a extensao/config.
- Execucao de acoes pelo Continue continua bloqueada ate existir bridge governada completa.

## Veredito

`CONTINUE_OPENAI_ADAPTER_READY_WITH_WARNINGS`

