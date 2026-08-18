# Authority Migration

## Antes

Diagnóstico técnico e alvo de patch estavam misturados em `PatchCandidateArtifact`.

Alguns caminhos podiam construir candidates diretamente a partir de paths, evidências ou contexto de modelo.

## Depois

Diagnóstico técnico:

`CanonicalDiagnosisArtifact`

Alvo técnico para patch:

`PatchCandidateArtifact`, sempre derivado do diagnóstico.

Plano de patch:

`PatchPlanningService`

Compilação de hunks, diff e rollback:

compilador interno do `PatchPlanningService`.

## Autoridades preservadas

Nenhuma autoridade paralela foi criada.

`PatchPlanningService` permanece como única autoridade de PatchPlan.

Runtime Doctor permanece read-only.

Speaker Truth, Validation, Completion e Timeline não foram alterados como autoridades.
