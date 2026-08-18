# Sprint 25 — Model & Capability Router

## Veredito

`SPRINT25_MODEL_ROUTER_READY_WITH_WARNINGS`

## Resultado

Foi criada uma camada explícita de capability/model routing, com endpoints para listar capacidades, health, registry, regras de roteamento, teste leve por capability, route-preview e workspace search com fallback keyword.

O sistema não finge providers ausentes: capabilities desabilitadas aparecem como `disabled`; runtime não verificado aparece como `unverified`; capability sem provider/model real deve aparecer como `missing`.

## Endpoints adicionados/consolidados

- `GET /api/v1/capabilities`
- `GET /api/v1/capabilities/health`
- `POST /api/v1/capabilities/workspace-search`
- `GET /api/v1/models/registry`
- `GET /api/v1/models/router`
- `POST /api/v1/models/router/test`
- `GET /api/v1/models/route-preview`

## Configs

- `config/models/capability_router.yaml`
- `config/models/fallbacks.yaml`

## Capabilities core

- `text_chat`
- `code_assist`
- `planning`
- `intent_classification`
- `policy_reasoning`
- `embeddings`
- `reranker`
- `ocr`
- `vision`
- `workspace_search`
- `file_summarization`
- `patch_planning`
- `shell_planning`
- `artifact_summary`

## Workspace Search

O endpoint usa policy `list_files` via `WorkspacePermissionMatrixService`. Se permitido, faz busca keyword local e registra route decision com `embeddings_used=false`, `reranker_used=false`, `fallback=keyword_search`.

## Telemetria

Route decisions são gravadas em:

`data/runtime/model_route_decisions.jsonl`

Evento:

`model_route_decision`

## Testes

Comando:

`python -m pytest tests\integration\test_continue_openai_compat_api.py tests\integration\test_model_capability_router_api.py -q`

Resultado:

`40 passed in 11.66s`

## Warnings

- OCR e Vision permanecem disabled por config.
- Embeddings/reranker usam health do VectorRAG; o teste leve não executa inferência real, então pode retornar `unverified` quando runtime está configurado mas não testado diretamente.
- Debugger/Pipeline ainda consomem indiretamente via endpoints/metadata; uma visualização dedicada pode ser feita em sprint de UX.
