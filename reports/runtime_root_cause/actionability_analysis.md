# AIpinho - Actionability Analysis

## Objetivo

Foi adicionada a dimensao canonica `Actionability` para responder uma pergunta especifica:

```text
Um programador humano conseguiria editar este codigo apenas com as informacoes presentes?
```

Ela nao substitui:

- Completeness;
- Diagnosis Quality;
- PatchCandidate Quality;
- Validation;
- Runtime Doctor.

Ela complementa essas analises com foco exclusivo na editabilidade tecnica.

## Local de Integracao

`Actionability` foi integrada sob a autoridade existente de diagnostico:

```text
DiagnosisRuntimeService
  -> PatchCandidateActionabilityAnalyzer
  -> PatchCandidateArtifact.technical_context.actionability
  -> PatchPlanningService
```

Nenhuma nova autoridade de PatchPlan foi criada.

## Criterios Deterministicos

A analise verifica:

- alvo tecnico real;
- simbolo ou unidade de edicao resolvida;
- trecho de codigo presente;
- contexto suficiente para edicao de arquivo quando a unidade for ampla;
- comportamento observado;
- comportamento esperado especifico ao alvo;
- evidencias;
- estrategia de reparo;
- confianca.

Todos os limites e termos genericos sao configuraveis por policy em:

```text
config/patching/model_patch_planner_policy.yaml
```

## Reason Codes

Reason codes adicionados:

```text
REPAIR_TASK_NOT_ACTIONABLE
REPAIR_TASK_TARGET_MISSING
REPAIR_TASK_TARGET_TOO_BROAD
REPAIR_TASK_SYMBOL_UNRESOLVED
REPAIR_TASK_SNIPPET_MISSING
REPAIR_TASK_SNIPPET_INSUFFICIENT
REPAIR_TASK_EXPECTED_BEHAVIOR_MISSING
REPAIR_TASK_OBSERVED_BEHAVIOR_MISSING
REPAIR_TASK_EVIDENCE_MISSING
REPAIR_TASK_STRATEGY_MISSING
REPAIR_TASK_CONFIDENCE_MISSING
```

## Resultado da Execucao

Na reexecucao da Fase 4:

- `DiagnosisQuality`: alto;
- `PatchCandidateQuality`: alto;
- `Actionability`: bloqueado;
- causa: `REPAIR_TASK_EXPECTED_BEHAVIOR_MISSING`;
- chamada ao modelo: nao realizada;
- `model_run_id`: `null`.

Isso prova que a nova dimensao detecta um caso que as metricas anteriores nao capturavam.

## Impacto Arquitetural

Antes:

```text
Candidate estruturalmente completo
  -> chamada ao modelo
  -> output vazio
  -> PATCH_MODEL_EMPTY_OUTPUT
```

Depois:

```text
Candidate estruturalmente completo
  -> Actionability
  -> REPAIR_TASK_EXPECTED_BEHAVIOR_MISSING
  -> bloqueio antes do modelo
```

## Conclusao

`Actionability` reduz incerteza sem criar bypass. O Runtime passa a distinguir diagnostico completo de tarefa editavel.
