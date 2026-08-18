# Diagnosis Runtime Boundary Update

## Status

READY

## Mudanca aplicada

`PatchCandidateBuilder` foi rebaixado para utilitario interno.

A fronteira operacional para transformar diagnostico tecnico em `PatchCandidateArtifact` agora e `DiagnosisRuntimeService`.

## Consumidores migrados

- `PatchPlanningService`
- `ModelAssistedPatchPlannerService`

## Autoridade preservada

`PatchPlanningService` continua sendo a unica autoridade de PatchPlan.

`DiagnosisRuntimeService` nao cria diff, rollback, hunk, approval ou execucao. Ele apenas traduz `CanonicalDiagnosisArtifact` para `PatchCandidateArtifact` de forma deterministica.

## Resultado arquitetural

Remove-se a disputa entre "planner cria candidate" e "diagnostico cria candidate".

O fluxo correto e:

CanonicalDiagnosisArtifact
-> DiagnosisRuntimeService
-> PatchCandidateArtifact
-> PatchPlanningService
-> PatchCompiler interno
-> CanonicalPatchPlan
