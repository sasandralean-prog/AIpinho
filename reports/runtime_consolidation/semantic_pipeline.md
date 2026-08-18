# Semantic Pipeline

## Cadeia cognitiva inicial

```text
Raw Prompt
  -> Prompt Normalization
  -> Semantic Proposition Extraction
  -> State Effect Resolution
  -> Intent Candidates
  -> Intent Arbitration
  -> Operation Contract Candidates
  -> Operation Contract Selection
```

## Responsabilidades

| Etapa | Responsabilidade | Autoridade preservada |
| --- | --- | --- |
| Prompt Normalization | Registrar normalizacao, encoding e transformacoes | Observabilidade |
| Semantic Proposition | Representar objetivos, restricoes, efeitos e sinais | SemanticPropositionNormalizationService |
| State Effect | Explicar efeito sobre workspace, filesystem, runtime e conhecimento | SemanticIntentGraph |
| Intent Candidates | Materializar hipoteses consideradas | CanonicalIntentRouter |
| Intent Decision | Registrar intent vencedor e criterio | SemanticIntentResolutionService/CanonicalIntentRouter |
| Operation Contract Decision | Explicar contrato selecionado e alinhamento com state effect | GovernanceLifecycleService |

## Fluxo de dados

O Public Chat passa a anexar o relatorio em:

```text
governance_lifecycle.semantic_ingress_doctor
```

Isso permite auditoria posterior sem mudar o payload operacional canônico.

## Nao alterado

- Policy
- Approval
- TaskRuntime
- ExecutionRuntime
- Validation
- Completion
- SpeakerTruth
- Capability Matching
- Artifact Rendering

## Conclusao

A AIpinho agora consegue explicar como compreendeu o texto antes da selecao do contrato, incluindo encoding, proposicoes, efeitos de estado e divergencias entre readonly e mutacao.
