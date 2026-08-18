# Operation Contract Selection

## Objetivo

Explicar como o contrato operacional selecionado se relaciona com a intent e com os efeitos de estado.

## IRs

- `OperationContractCandidate`
- `OperationContractDecision`

Campos principais:

- selected_contract_type
- selected_operation_type
- candidates
- relation_to_intent
- relation_to_state_effects
- reason_codes
- evidence_refs

## Integracao

O contrato real continua sendo gerado pela cadeia existente:

```text
SemanticIntentResolution
  -> GovernanceLifecycleService
  -> CanonicalOperationContract
```

O Semantic Ingress Doctor nao substitui essa cadeia.

## Diagnosticos gerados

- `OPERATION_CONTRACT_STATE_EFFECT_MISMATCH`
- `READONLY_CONTRACT_PROMOTED_TO_MUTATION`

## Conclusao

A AIpinho agora consegue explicar por que um contrato operacional foi escolhido e detectar, como diagnostico, quando a escolha observada nao condiz com o efeito semantico declarado pelo prompt.
