# AIpinho - Repair Task Root Cause

## Escopo

Esta analise investigou a causa estrutural de `PATCH_MODEL_EMPTY_OUTPUT` sem alterar Validation, Completion, Speaker Truth, Approval, ExecutionPlan ou o fluxo canonico de PatchPlan.

O fluxo preservado foi:

```text
CanonicalDiagnosisArtifact
  -> DiagnosisRuntimeService
  -> PatchCandidateArtifact
  -> PatchPlanningService
  -> InferenceRuntimeService
  -> Role LLM
  -> replacement/snippet
  -> PatchCompiler
  -> CanonicalPatchPlan
```

## Evidencias Observadas

### Candidates que conseguem gerar replacement

Os testes unitarios com candidates pequenos e localizados continuam gerando replacement quando possuem:

- arquivo real;
- simbolo ou unidade de edicao resolvida;
- trecho de codigo suficiente;
- comportamento observado;
- comportamento esperado especifico ao alvo;
- evidencia;
- estrategia de reparo;
- confianca minima.

Esse grupo demonstra que o mecanismo de compilacao nao precisa ser relaxado. Quando a unidade editavel existe, o fluxo pode seguir para inferencia e compilacao.

### Candidates que bloqueiam

Na execucao mais recente da Fase 4, o Runtime produziu:

- `task_run_id`: `task_run_97016ddc1eab4187aca73888115ab8e6`
- `patch_candidate_id`: `patch_candidate_9d3dedcb9506400da32df0b0da9de110`
- `diagnosis_id`: `diagnosis_bed3ae2161e74976bd2f101efc044db8`
- alvo tecnico: `src/main/kotlin/com/pinhoabacaxi/musicasdesktop/audio/AdaptivePcmDecoder.kt`
- unidade de edicao: `file`
- trecho atual completo: `1533` caracteres
- `model_run_id`: `null`

O bloqueio ocorreu antes da chamada ao modelo:

```text
REPAIR_TASK_NOT_ACTIONABLE
REPAIR_TASK_EXPECTED_BEHAVIOR_MISSING
```

Isso confirma que o erro deixou de ser tratado como uma saida vazia opaca do modelo. O Runtime agora explica que a tarefa de reparo ainda nao e editavel.

## Causa Raiz

A causa estrutural identificada e:

```text
PatchCandidate possuia completude estrutural, mas nao possuia objetivo de edicao especifico ao alvo tecnico.
```

Antes desta wave, `PatchCandidateQuality` e `DiagnosisQuality` podiam pontuar alto porque avaliavam presenca de campos e evidencias. Isso nao respondia a pergunta operacional:

```text
Um programador humano conseguiria editar este codigo apenas com estas informacoes?
```

Na Fase 4, o `expected_behavior` efetivo ainda estava proximo de uma solicitacao de planejamento e artifact, nao de uma mudanca concreta esperada no arquivo ou simbolo selecionado.

## Diferencas Entre Grupos

Candidates acionaveis possuem:

- comportamento esperado que menciona ou se conecta ao alvo tecnico;
- objetivo de edicao claro;
- unidade de edicao delimitada;
- trecho de codigo suficiente para executar a alteracao;
- estrategia de reparo aplicavel ao alvo.

Candidates bloqueados possuem:

- alvo e trecho, mas objetivo generico;
- evidencias suficientes para diagnosticar, mas insuficientes para editar;
- expected behavior sem vinculo tecnico verificavel com o arquivo/simbolo;
- risco de gerar diff especulativo.

## Campos Pouco Influentes Para Replacement

Os campos abaixo ajudam auditoria, mas nao bastam para produzir replacement:

- nomes de artifacts esperados;
- texto de fase ou instrucao operacional;
- riscos gerais;
- rollback generico;
- lista ampla de arquivos candidatos;
- objetivo semantico sem traducao para comportamento esperado no alvo.

## Campo Ausente em Casos Bloqueados

O campo determinante ausente e:

```text
target-specific expected behavior
```

Ou seja, o diagnostico precisa dizer o que o alvo tecnico deve passar a fazer de forma concreta e editavel, sem depender do modelo para inferir a intencao de reparo.

## Conclusao

`PATCH_MODEL_EMPTY_OUTPUT` era sintoma. A causa estrutural era a promocao de candidates que pareciam completos, mas nao eram tarefas de reparo editaveis.

O Runtime agora bloqueia deterministicamente antes da inferencia quando essa condicao ocorre.
