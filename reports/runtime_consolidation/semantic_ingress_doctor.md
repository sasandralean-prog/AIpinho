# Semantic Ingress Doctor

## Objetivo

Esta wave adicionou uma camada read-only para explicar a fronteira entre texto recebido e selecao de contrato operacional.

O Semantic Ingress Doctor nao decide intent, nao escolhe policy, nao cria Task, nao cria TaskRun e nao altera Validation, Completion ou Speaker Truth. Ele apenas observa as decisoes canonicas ja existentes e materializa a trilha cognitiva inicial.

## Pipeline observado

```text
Raw Prompt
  -> PromptNormalization
  -> SemanticProposition
  -> StateEffect
  -> IntentCandidate
  -> IntentDecision
  -> OperationContractCandidate
  -> OperationContractDecision
```

## Implementacao

- Schemas adicionados: `src/aipinho/schemas/semantic_runtime/semantic_ingress.py`
- Servico adicionado: `src/aipinho/services/semantic_runtime/semantic_ingress_doctor_service.py`
- Integracao de observabilidade: `src/aipinho/services/governance/lifecycle/public_route_lifecycle_service.py`
- Integracao Runtime Doctor: `src/aipinho/services/runtime/runtime_doctor_service.py`
- Integracao Runtime Doctor endpoint/root-cause: `src/aipinho/services/runtime_doctor/runtime_doctor_service.py`
- Integracao CVL: `src/aipinho/services/cvl/cognitive_validation_laboratory_service.py`

## Garantias arquiteturais

- A decisao operacional continua nas autoridades existentes.
- O Doctor nao reclassifica prompt.
- O Doctor nao promove readonly para mutacao nem bloqueia execucao.
- O payload gerado fica em `governance_lifecycle.semantic_ingress_doctor`.
- O Runtime Doctor pode classificar falhas dessa fronteira sem depender de logs soltos.

## Reason codes adicionados/propagados

- `ENCODING_MOJIBAKE_SUSPECTED`
- `STATE_EFFECT_UNRESOLVED`
- `STATE_EFFECT_CONTRACT_MISMATCH`
- `OPERATION_CONTRACT_STATE_EFFECT_MISMATCH`
- `READONLY_CONTRACT_PROMOTED_TO_MUTATION`
- `SEMANTIC_PROPOSITIONS_MISSING`
- `STATE_EFFECTS_MISSING`
- `INTENT_CANDIDATES_MISSING`

## Resultado

READY: a camada foi implementada como diagnostico, nao como novo Runtime ou novo router.
