# FireTest 5 H1B5.2 - Relationship-Aware Artifact Contract Activation

## Veredito

FIRETEST5_H1B5_2_RELATIONSHIP_AWARE_ARTIFACT_CONTRACT_READY

## Objetivo

Permitir que artifact contracts declarem e materializem campos de relacionamento candidato sem transformar candidatos em relacoes finais.

## Escopo

- `ArtifactSemanticProfile` agora preserva `relationship_rendered_fields` e `relationship_rendering_summary`.
- `ArtifactSemanticContractService` deriva campos candidatos a partir de binding/profile.
- Runtime renderer materializa campos `relationship_*` consumindo somente `perception_payload` ja produzido pelo fluxo governado.
- Summary leve `relationship_cognition` inclui `rendered_field_count`, refs e `validation_status`.
- Validation continua blocked por `RELATIONSHIP_VALIDATION_REQUIRED`.

## Nao-goals

- Nao implementar H1B5.3.
- Nao validar relacao final.
- Nao declarar `lyrics_for`, `artwork_for`, `album_art_for` ou `sidecar_of`.
- Nao criar renderer observador.
- Nao deixar renderer chamar capability.
- Nao mexer em public chat boundary.
- Nao buscar FIRETEST5_READY.

## Arquivos alterados

- `src/aipinho/schemas/artifacts/artifact_semantic_profile.py`
- `src/aipinho/services/artifacts/artifact_semantic_contract_service.py`
- `src/aipinho/services/governance/runtime/readonly_analysis_artifact_runtime_service.py`
- `src/aipinho/services/runtime/universal_task_session_service.py`
- `tests/unit/test_relationship_aware_artifact_contract_activation.py`
- `tests/unit/test_media_relationship_foundation.py`

## Artifact Contract Antes/Depois

Antes, relationships podiam existir no profile/binding, mas contratos nao tinham caminho claro para campos candidatos materializaveis.

Depois, contratos podem declarar:

- `expected_relationships`
- `relationship_fields`
- `relationship_semantics`

Campos suportados:

- `relationship_candidate_summary`
- `relationship_candidate_count`
- `relationship_candidate_families`
- `relationship_top_family`
- `relationship_confidence_band`
- `relationship_validation_status`
- `relationship_evidence_ref_count`
- `relationship_provenance_ref_count`
- `relationship_conflict_count`
- `relationship_limitations_summary`

## Renderer Behavior

O renderer apenas materializa dados de:

```text
perception.relationship_summary
perception.relationship_candidates
perception.relationship_observations
perception.relationship_provenance_traces
```

Ele nao chama `media_relationship_candidate_detector`, nao cria EvidenceRecord, nao observa filesystem/backend e nao infere por extensao/nome.

## ArtifactSemanticProfile -> Output

`ArtifactSemanticContractService` deriva `relationship_rendered_fields` do binding/provenance:

- candidate count;
- top family;
- confidence band;
- validation status;
- evidence/provenance ref counts;
- conflict count;
- limitations summary.

## Validation Behavior

Campos candidatos renderizados nao passam final validation.

Quando candidates existem, o runtime/profile preserva:

```text
relationship_final_validation_missing
reason_code = RELATIONSHIP_VALIDATION_REQUIRED
truth_eligible = false
```

## Summary Behavior

`relationship_cognition` agora inclui:

- `rendered_field_count`
- `evidence_ref_count`
- `provenance_ref_count`
- `validation_status`
- `truth_eligible=false`

Sem payload gigante.

## Service-Equivalent Validation

Validado:

- artifact contract declarando relationship fields;
- profile derivando fields de binding;
- runtime renderer materializando campos candidatos;
- final validation permanecendo blocked;
- summary leve com rendered field counts.

## Testes Executados

```text
python -m pytest tests/unit/test_relationship_aware_artifact_contract_activation.py -q
3 passed in 2.62s
```

```text
python -m pytest tests/unit/test_relationship_aware_artifact_contract_activation.py tests/unit/test_relationship_evidence_provenance_maturity.py tests/unit/test_media_relationship_foundation.py tests/unit/test_contract_driven_perception_service.py tests/unit/test_artifact_semantic_contract_service.py tests/unit/test_cognitive_validation_laboratory_service.py tests/unit/test_universal_task_session_service.py -q
68 passed in 10.96s
```

```text
python -m py_compile ...
PASS
```

## Hardcode Audit

Busca por projeto/path/extensoes/relacoes finais nao encontrou regras novas. A unica ocorrencia relevante foi o nome do teste que afirma que o renderer nao chama detector.

## Gaps Restantes

- Relationship validation/readiness policy ainda nao existe.
- `relationship_validation_ready` ainda nao e calculado.
- Public path boundary permanece externo.

## Proxima Wave Recomendada

H1B5.3 - Relationship Validation Policy / Final Relation Readiness.

## Por Que Nao Houve Truth Prematuro

- Rendering de campos candidatos nao altera Validation/Completion/Speaker Truth.
- `relationship_validation_status` fica `validation_required`.
- `truth_eligible` permanece `false`.
- Confidence e candidate fields seguem como evidencias/materializacao, nao fatos finais.

