# Diagnosis Runtime Migration

## Migração aplicada

O `PatchPlanningService` deixou de construir `PatchCandidateArtifact` diretamente a partir de paths e evidências.

Agora ele segue duas etapas internas:

1. Construção ou adaptação para `CanonicalDiagnosisArtifact`.
2. Derivação determinística de `PatchCandidateArtifact` via `PatchCandidateBuilder`.

## Planner assistido por modelo

O `ModelAssistedPatchPlannerService` agora cria um diagnóstico canônico a partir do contexto read-only selecionado.

O candidate enviado ao Role LLM é derivado desse diagnóstico e contém `diagnosis_id`.

O modelo continua limitado a retornar replacement ou patch snippet, rationale e confidence. Ele não escolhe alvo, não gera diff, não decide rollback e não aprova execução.

## Validação preservada

O compilador bloqueia candidates sem diagnóstico, evidência, alvo técnico ou replacement concreto.

Reason codes mantidos ou adicionados:

- `PATCH_CANDIDATE_INSUFFICIENT`
- `PATCH_SYMBOL_NOT_FOUND`
- `PATCH_CONTEXT_TOO_SMALL`
- `PATCH_MODEL_EMPTY_OUTPUT`
- `PATCH_REPLACEMENT_INVALID`
- `PATCH_COMPILER_FAILED`
- `INSUFFICIENT_PATCH_EVIDENCE`
