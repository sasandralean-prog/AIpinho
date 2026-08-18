# AIpinho - Repair Intent Enrichment Wave

## Status

```text
READY
```

## Objetivo

Esta wave adicionou enriquecimento semantico deterministico ao `CanonicalDiagnosisArtifact` para produzir um `RepairIntent` antes da geracao de `PatchCandidateArtifact`.

O objetivo foi eliminar a lacuna estrutural identificada na wave anterior:

```text
PatchCandidate com alvo e evidencia, mas sem comportamento esperado especifico ao alvo tecnico.
```

## Fluxo Preservado

```text
ReadOnly Analysis
  -> CanonicalDiagnosisArtifact
  -> DiagnosisRuntimeService
  -> RepairIntentResolver
  -> CanonicalDiagnosisArtifact enriquecido
  -> PatchCandidateArtifact
  -> PatchPlanningService
  -> InferenceRuntimeService
```

`RepairIntentResolver` nao e uma autoridade nova. Ele e uma etapa interna do `DiagnosisRuntimeService`.

## Responsabilidade do Repair Intent

O `RepairIntent` representa:

- expected behavior especifico ao alvo;
- repair boundary;
- success condition;
- evidencias usadas;
- confidence;
- reason codes.

Ele nunca representa:

- patch;
- diff;
- replacement;
- hunk;
- rollback;
- approval;
- plano executavel.

## Determinismo

O resolver nao usa LLM, prompts ocultos, inferencia externa ou matching por FireTest.

Ele trabalha com:

- diagnosis type;
- observed behavior;
- expected behavior existente;
- evidence summaries;
- reason codes;
- repair hints;
- target file;
- target symbol.

Quando nao ha informacao tecnica suficiente, ele nao inventa comportamento esperado e registra:

```text
REPAIR_INTENT_MISSING
TARGET_SPECIFIC_EXPECTED_BEHAVIOR_MISSING
```

## Runtime Doctor

O Runtime Doctor passa a reconhecer o dominio:

```text
repair_intent
```

E os reason codes:

```text
REPAIR_INTENT_MISSING
REPAIR_BOUNDARY_MISSING
SUCCESS_CONDITION_MISSING
TARGET_SPECIFIC_EXPECTED_BEHAVIOR_MISSING
```

## Arquivos Alterados

- `src/aipinho/schemas/patching/canonical_diagnosis_artifact.py`
- `src/aipinho/schemas/patching/__init__.py`
- `src/aipinho/services/patching/repair_intent_resolver.py`
- `src/aipinho/services/patching/diagnosis_runtime_service.py`
- `src/aipinho/services/patching/patch_candidate_builder.py`
- `src/aipinho/services/patching/model_assisted_patch_planner_service.py`
- `src/aipinho/schemas/runtime/runtime_doctor.py`
- `src/aipinho/services/runtime/runtime_doctor_service.py`
- `tests/unit/test_repair_intent_resolver.py`
- `tests/unit/test_diagnosis_runtime_service.py`
- `tests/unit/test_runtime_doctor_service.py`

## Validacao

Testes executados:

```text
python -m pytest tests\unit\test_repair_intent_resolver.py tests\unit\test_diagnosis_runtime_service.py tests\unit\test_patch_candidate_actionability_analyzer.py tests\unit\test_model_assisted_patch_planner_service.py tests\unit\test_patch_planning_service.py tests\unit\test_runtime_doctor_service.py -q
```

Resultado:

```text
29 passed in 6.11s
```

## Garantias

- Nenhum Runtime paralelo criado.
- Nenhum Planner paralelo criado.
- Nenhum PatchPlan paralelo criado.
- Nenhuma Validation paralela criada.
- Nenhuma inferencia adicionada.
- Nenhuma regra especifica para FireTest.
- Nenhum bypass de Validation, Completion ou Speaker Truth.
- PatchPlanningService permanece a unica autoridade de PatchPlan.

## Conclusao

A AIpinho agora possui uma etapa deterministica para transformar diagnostico tecnico em intencao de reparo verificavel antes de promover um PatchCandidate. Quando a semantica ainda for insuficiente, o Runtime deve bloquear com reason codes estruturados em vez de delegar a descoberta da intencao ao modelo.
