# Sprint 24 — Continue Governed Dev Mode

## Veredito

`SPRINT24_CONTINUE_GOVERNED_DEV_READY_WITH_WARNINGS`

## Resultado

A rota OpenAI-compatible do Continue está em modo `governed_dev` e foi validada por testes automatizados. Ela responde conversa, matemática simples, perguntas de capacidade/configuração, contexto anexado, streaming SSE e cria ApprovalRequest para escrita/shell sem executar efeitos colaterais.

## Evidência automatizada

Comando executado:

`python -m pytest tests\integration\test_continue_openai_compat_api.py tests\integration\test_model_capability_router_api.py -q`

Resultado:

`40 passed in 11.66s`

Também foi executado:

`python -m py_compile` nos arquivos alterados.

## O que foi consolidado

- Continue responde `quanto e 2+2?` com conteúdo não vazio e streaming `[DONE]`.
- Perguntas como “Você consegue ler arquivos?” retornam resposta capability-aware.
- Perguntas sobre configurar recursos/persona não viram refusal operacional.
- Contexto anexado como `@App.tsx`, `@Terminal`, `@Git Diff` e `@rules` é detectado e analisado como contexto já recebido.
- Pedidos de escrita e shell criam preview/ApprovalRequest, sem escrever/rodar comandos diretamente.
- Approval textual via Continue continua funcionando por `APROVAR approval_xxx` / `NEGAR approval_xxx`.
- Foi adicionada telemetria `model_route_decision` na metadata da resposta Continue.

## Arquivos alterados

- `src/aipinho/api/routers/continue_integration_router.py`
- `src/aipinho/services/models/capability_router_service.py`
- `src/aipinho/api/routers/capability_router.py`
- `src/aipinho/api/routers/model_router.py`
- `src/aipinho/api/routers/__init__.py`
- `config/models/capability_router.yaml`
- `config/models/fallbacks.yaml`
- `tests/integration/test_model_capability_router_api.py`

## Warning honesto

O smoke visual real dentro do VSCode/Continue não foi executado nesta rodada. O contrato HTTP OpenAI-compatible, streaming e approval por chat foram validados por TestClient.

## Segurança

- OpenAI pago não foi chamado.
- Escrita/shell continuam em preview/approval.
- Direct write/shell pelo Continue permanece bloqueado.
- Nenhum segredo foi registrado.
