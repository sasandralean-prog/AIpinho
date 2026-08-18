# AIpinho - Runtime Integration

## Fluxo Integrado

O fluxo canonico apos a wave ficou:

```text
CanonicalDiagnosisArtifact
  -> DiagnosisRuntimeService
  -> ActionabilityAnalysis
  -> PatchCandidateArtifact
  -> PatchPlanningService
  -> InferenceRuntimeService
  -> Role LLM
  -> PatchCompiler
  -> CanonicalPatchPlan
```

Quando `ActionabilityAnalysis.editable = false`, o `PatchPlanningService` bloqueia antes da inferencia.

## Arquivos Alterados

- `src/aipinho/schemas/patching/patch_observability.py`
- `src/aipinho/services/patching/patch_candidate_actionability_analyzer.py`
- `src/aipinho/services/patching/diagnosis_runtime_service.py`
- `src/aipinho/services/patching/model_assisted_patch_planner_service.py`
- `src/aipinho/services/patching/patch_planning_service.py`
- `src/aipinho/schemas/runtime/runtime_doctor.py`
- `src/aipinho/services/runtime/runtime_doctor_service.py`
- `config/patching/model_patch_planner_policy.yaml`
- `tests/unit/test_patch_candidate_actionability_analyzer.py`
- `tests/unit/test_diagnosis_runtime_service.py`
- `tests/unit/test_model_assisted_patch_planner_service.py`

## Responsabilidades Preservadas

`DiagnosisRuntimeService` continua sendo a fronteira que transforma diagnostico em candidate.

`PatchPlanningService` continua sendo a unica autoridade de PatchPlan.

`InferenceRuntimeService` continua sendo a unica fronteira de inferencia.

`PatchCompiler` continua sendo a autoridade de diff, hunks e rollback.

`Validation`, `Completion` e `Speaker Truth` nao foram relaxados.

## Runtime Doctor

O Runtime Doctor passou a reconhecer o dominio:

```text
Actionability
```

E os reason codes `REPAIR_TASK_*`.

Isso permite classificar bloqueios de reparo como falhas de editabilidade, em vez de falhas genericas de modelo.

## Politica

Os parametros de actionability foram colocados em policy configuravel:

```text
model_patch_planner.actionability
```

Nao foram adicionados caminhos absolutos, regras por FireTest, nomes de projeto ou excecoes por fase.

## Validacao Tecnica

Testes focados executados:

```text
python -m pytest tests\unit\test_patch_candidate_actionability_analyzer.py tests\unit\test_diagnosis_runtime_service.py tests\unit\test_model_assisted_patch_planner_service.py tests\unit\test_patch_planning_service.py tests\unit\test_runtime_doctor_service.py -q
```

Resultado:

```text
25 passed in 5.98s
```

Suite ampla tentada:

```text
python -m pytest tests\unit tests\governance\test_runtime_vertical_slice.py -q
```

A execucao ficou presa proximo de 99% apos aproximadamente 12 minutos e foi interrompida. A saida parcial indicava falhas fora do escopo desta wave, portanto nao foi usada como evidencia conclusiva.

## FireTest Fase 4

Reexecucao via endpoint publico:

```text
POST /api/v1/chat
```

Resultado:

```text
TaskRun: task_run_97016ddc1eab4187aca73888115ab8e6
Status: blocked
Validation: blocked
PatchPlanning: blocked
Model run: null
Reasons:
  - REPAIR_TASK_NOT_ACTIONABLE
  - REPAIR_TASK_EXPECTED_BEHAVIOR_MISSING
```

O bloqueio e esperado e correto: nao houve bypass, nem chamada desnecessaria ao modelo.

## Conclusao

A integracao fortalece o fluxo existente. Nenhuma autoridade paralela foi criada.
