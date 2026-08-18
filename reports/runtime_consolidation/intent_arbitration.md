# Intent Arbitration

## Objetivo

Registrar quais intents foram consideradas e por que uma decisao venceu, sem criar outro router.

## IRs

- `IntentCandidate`
- `IntentDecision`

Cada candidato inclui:

- intent_id
- operation_type
- confidence
- supporting_propositions
- rejected_reason
- arbitration_score

## Fonte da decisao

A decisao vencedora continua vindo do `CanonicalIntentRouter` via `SemanticIntentResolutionService`.

O Semantic Ingress Doctor apenas compara:

```text
SemanticIntentGraph
  -> candidatos diagnosticos
  -> intent canonica vencedora
```

## Beneficio

Na regressao observada anteriormente, em que uma entrada readonly degradou para `filesystem_write`, o Doctor passa a indicar se houve:

- degradacao de encoding;
- ambiguidade de intent;
- conflito de state effect;
- selecao de contrato incompativel.

## Resultado

Nenhuma autoridade paralela foi criada.
