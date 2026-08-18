# Sprint 24 — Continue Smoke Results

## Automated Smoke

- `oi` / conversa simples: coberto por suite Continue.
- `quanto e 2+2?`: passou.
- pergunta sobre personalidade/configuração: passou sem refusal operacional.
- pergunta sobre leitura de arquivos: passou com resposta capability-aware.
- `@App.tsx`: contexto detectado e analisado sem leitura externa.
- `@Terminal`: contexto detectado.
- `@Git Diff`: contexto detectado.
- pedido de escrita: ApprovalRequest criado; nenhum arquivo escrito.
- pedido de shell: ApprovalRequest criado; nenhum comando executado.
- streaming: chunks SSE com content e `[DONE]`.

## Manual VSCode

Não executado nesta rodada. Recomendado testar no VSCode com Continue apontando para `http://127.0.0.1:9088/v1`.
