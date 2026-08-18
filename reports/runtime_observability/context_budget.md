# Context Budget

## Status

READY

## Analyzer

`ContextBudgetAnalyzer`

## Objetivo

Registrar o orcamento real de contexto usado pela inferencia:

- limite do role;
- limite estimado do provider;
- chars reais;
- tokens estimados;
- chars descartados;
- itens descartados;
- itens truncados.

## Onde fica

- `canonical_inference_input_artifact.context_budget`
- `inference_input_doctor.context_budget`

## Observacao

O analyzer nao decide truncamento e nao altera prompt. Ele apenas explica o que chegou ao modelo.
