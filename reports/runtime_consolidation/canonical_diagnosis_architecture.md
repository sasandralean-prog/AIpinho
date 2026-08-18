# Canonical Diagnosis Architecture

## Status

READY

## Autoridade canônica

`CanonicalDiagnosisArtifact` passa a ser a representação oficial de diagnóstico técnico para o pipeline de coding da AIpinho.

Ele representa apenas diagnóstico: comportamento observado, comportamento esperado, localização técnica, evidências, confiança, hints de reparo e reason codes.

Ele não representa patch, diff, rollback, approval ou execução.

## Fluxo consolidado

Read-only analysis

-> `CanonicalDiagnosisArtifact`

-> `PatchCandidateBuilder`

-> `PatchCandidateArtifact`

-> `PatchPlanningService`

-> Role LLM replacement/snippet only

-> Patch compiler interno

-> `CanonicalPatchPlan`

-> preview, approval, execution, validation, completion e Speaker Truth

## Arquivos alterados

- `src/aipinho/schemas/patching/canonical_diagnosis_artifact.py`
- `src/aipinho/schemas/patching/patch_candidate_artifact.py`
- `src/aipinho/schemas/patching/patch_plan_request.py`
- `src/aipinho/schemas/patching/patch_plan.py`
- `src/aipinho/services/patching/patch_candidate_builder.py`
- `src/aipinho/services/patching/patch_planning_service.py`
- `src/aipinho/services/patching/model_assisted_patch_planner_service.py`
- `src/aipinho/services/runtime/runtime_doctor_service.py`

## Compatibilidade

Objetos antigos de `PatchCandidateArtifact` ainda podem chegar sem `diagnosis_id`, mas são promovidos para `CanonicalDiagnosisArtifact` antes da compilação.

Essa compatibilidade não mantém uma autoridade paralela: ela é apenas uma adaptação para a autoridade canônica.
