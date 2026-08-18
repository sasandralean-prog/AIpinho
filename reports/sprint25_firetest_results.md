# Sprint 25 — Firetest Results

## Firetest A — route preview

Endpoint testado por suite: `/api/v1/models/route-preview?operation_type=continue_context_analysis`

Resultado esperado observado: `code_assist` selecionado.

## Firetest B — embeddings health

Endpoint testado: `POST /api/v1/models/router/test`.

Resultado aceito: `ok`, `missing`, `disabled`, `failed` ou `unverified` estruturado. Não há fake ready.

## Firetest D — workspace search

Endpoint testado: `POST /api/v1/capabilities/workspace-search`.

Resultado: busca keyword com policy e fallback explícito quando permitido.

## Firetests OCR/Vision

Status por config: disabled. Não foi enviado arquivo/imagem para provider externo.

## Continue context

Teste Continue com `@App.tsx` valida `model_route_decision.source_channel=vscode_continue`.
