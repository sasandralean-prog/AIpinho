# AIpinho - Root Cause Wave Final Verdict

## Status

```text
ROOT_CAUSE_IDENTIFIED
```

Nao declarar `READY`.

## Motivo

A causa estrutural de `PATCH_MODEL_EMPTY_OUTPUT` foi identificada:

```text
O Runtime estava enviando ao modelo PatchCandidates que tinham alvo, evidencia e snippet, mas nao tinham comportamento esperado especifico ao alvo tecnico.
```

Sem essa informacao, o modelo pequeno recebe uma tarefa abstrata demais para produzir replacement seguro. Antes desta wave, isso aparecia como output vazio. Agora aparece como bloqueio deterministico:

```text
REPAIR_TASK_NOT_ACTIONABLE
REPAIR_TASK_EXPECTED_BEHAVIOR_MISSING
```

## Evidencia Principal

Na reexecucao da Fase 4:

- TaskRun: `task_run_97016ddc1eab4187aca73888115ab8e6`
- PatchCandidate: `patch_candidate_9d3dedcb9506400da32df0b0da9de110`
- Diagnosis: `diagnosis_bed3ae2161e74976bd2f101efc044db8`
- Target file: `src/main/kotlin/com/pinhoabacaxi/musicasdesktop/audio/AdaptivePcmDecoder.kt`
- Snippet: completo para a unidade de arquivo
- Model run: `null`
- Bloqueio: antes da inferencia

## O Que Foi Corrigido

- O Runtime nao chama mais o modelo quando a tarefa de reparo nao e editavel.
- `PATCH_MODEL_EMPTY_OUTPUT` deixa de ser um bloqueio opaco quando a causa real e candidate nao acionavel.
- `Actionability` foi integrada ao fluxo canonico existente.
- Runtime Doctor reconhece o novo dominio e os reason codes.
- Validation, Completion e Speaker Truth permaneceram intactos.

## O Que Ainda Falta

Para a Fase 4 produzir um PatchPlan concreto, a cadeia anterior ao PatchCandidate precisa fornecer:

```text
target-specific expected behavior
```

Em termos genericos:

```text
O diagnostico precisa declarar o que o arquivo ou simbolo selecionado deve passar a fazer, de forma concreta, verificavel e vinculada ao alvo tecnico.
```

Enquanto essa informacao nao existir, o Runtime deve continuar bloqueando.

## Proxima Correcao Recomendada

Fortalecer a producao de `CanonicalDiagnosisArtifact` para transformar evidencias de analise readonly em comportamento esperado especifico ao alvo.

Essa melhoria deve ocorrer antes do PatchCandidate, sem mover autoridade de PatchPlan para diagnostico e sem permitir que o modelo escolha alvo tecnico.

Fluxo recomendado:

```text
ReadOnly Analysis
  -> CanonicalDiagnosisArtifact com expected_behavior especifico ao alvo
  -> DiagnosisRuntimeService
  -> PatchCandidateArtifact acionavel
  -> PatchPlanningService
```

## Garantias Mantidas

- Nenhum fluxo paralelo criado.
- Nenhum runtime paralelo criado.
- Nenhum planner paralelo criado.
- Nenhum PatchCompiler paralelo criado.
- Nenhuma Validation paralela criada.
- Nenhum Diagnosis paralelo criado.
- Nenhum bypass criado.
- Nenhuma regra especifica para FireTest adicionada.
- Nenhum hardcode de projeto, caminho ou fase foi introduzido.
- Nenhuma validacao foi relaxada.

## Veredito

O Runtime agora consegue explicar, de forma deterministica, por que um candidate e ou nao editavel.

O FireTest continua bloqueado na Fase 4, mas agora o bloqueio e arquiteturalmente correto e possui causa precisa:

```text
faltou comportamento esperado especifico ao alvo tecnico.
```
