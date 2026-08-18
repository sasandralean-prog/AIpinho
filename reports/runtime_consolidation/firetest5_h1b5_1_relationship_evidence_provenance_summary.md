# FireTest 5 H1B5.1 - Relationship Evidence & Provenance Binding Maturity

## Veredito

FIRETEST5_H1B5_1_RELATIONSHIP_EVIDENCE_PROVENANCE_READY

## Objetivo

Amadurecer candidatos de relacionamento para que cada candidatura carregue sinais auditaveis, provenance trace, modelo de confidence, negative evidence, conflitos, limitations e binding sem virar Truth.

## Escopo

- `RelationshipEvidenceSignal` fortalecido com `signal_id`, entity refs, confidence weight/method, negative evidence e conflicts.
- `RelationshipProvenanceTrace` criado para explicar produtor, inputs, sinais usados/rejeitados, policy checks, arbitration ref e evidence refs.
- `RelationshipConfidenceModel` criado com score bruto/normalizado, band, signal contributions, conflitos, negative evidence e calibration notes.
- `RelationshipNegativeEvidence` e `RelationshipConflict` criados.
- `EvidenceRecord` de `relationship_observation` amadurecido com `observation_id`, `provenance_trace_id`, negative evidence, conflicts e `validation_required=true`.
- `ArtifactSemanticProfile` fortalecido com provenance traces, conflict summary, negative evidence summary e binding quality.
- `SemanticSelfReview` distingue evidence, provenance, conflicts, validation required e truth-not-eligible.
- `relationship_cognition` no summary ganhou contagens leves de provenance/conflict/negative evidence.
- CVL reconhece novas fronteiras de relationship maturity.

## Nao-goals

- Nao implementar H1B5.2.
- Nao ativar rendering final em artifacts.
- Nao implementar H1B5.3.
- Nao validar relacao final.
- Nao declarar `lyrics_for`, `artwork_for`, `album_art_for` ou `sidecar_of`.
- Nao criar Knowledge Graph/H1D, parser novo ou public chat boundary.
- Nao buscar FIRETEST5_READY.

## Arquivos alterados

- `src/aipinho/schemas/artifacts/relationship.py`
- `src/aipinho/schemas/artifacts/artifact_semantic_profile.py`
- `src/aipinho/schemas/artifacts/contract_perception.py`
- `src/aipinho/schemas/artifacts/__init__.py`
- `src/aipinho/services/artifacts/media_relationship_candidate_service.py`
- `src/aipinho/services/artifacts/contract_driven_perception_service.py`
- `src/aipinho/services/artifacts/artifact_semantic_contract_service.py`
- `src/aipinho/services/governance/runtime/readonly_analysis_artifact_runtime_service.py`
- `src/aipinho/services/runtime/universal_task_session_service.py`
- `src/aipinho/services/cvl/cognitive_validation_laboratory_service.py`
- `tests/unit/test_relationship_evidence_provenance_maturity.py`
- `tests/unit/test_media_relationship_foundation.py`
- `tests/unit/test_cognitive_validation_laboratory_service.py`

## Evidence Signal Maturity

Cada signal agora preserva:

- `signal_id`
- `signal_type`
- `raw_value`
- `normalized_value`
- `normalization_trace`
- `source_entity_ref`
- `target_entity_ref`
- `confidence_contribution`
- `confidence_weight`
- `confidence_method`
- `negative_evidence`
- `conflicts`
- `is_sufficient_alone=false`

Nenhum signal isolado valida relacao final.

## Provenance Trace

`RelationshipProvenanceTrace` responde:

- por que o candidato existe;
- qual capability produziu;
- quais entidades/contrato entraram;
- quais sinais foram usados/rejeitados;
- quais normalizacoes e policy checks foram aplicados;
- qual ref de arbitration autorizou;
- quais EvidenceRecords resultaram.

## Confidence Model

`RelationshipConfidenceModel` explicita:

- `raw_score`
- `normalized_score`
- `confidence_band`
- `signal_contributions`
- `positive_signal_count`
- `negative_signal_count`
- `conflict_count`
- `missing_signal_count`
- `calibration_notes`
- `limitations`

Bands:

```text
insufficient
low
medium
high
conflicted
```

`high` nao significa Truth. `conflicted` impede readiness futura.

## Negative Evidence e Conflicts

Foram adicionados modelos para:

- `source_root_role_incompatible`
- `entity_role_incompatible`
- `insufficient_signal_diversity`

Conflitos sao preservados no candidate, observation, EvidenceRecord, profile e summary leve por contagem.

## EvidenceRecord Antes/Depois

Antes, relationship evidence tinha candidate/source/target basicos.

Depois, `EvidenceRecord` pode preservar:

- `candidate_id`
- `observation_id`
- `provenance_trace_id`
- `source_entity_ref`
- `target_entity_ref`
- `relation_family`
- `relation_kind_candidate`
- `signals`
- `negative_evidence`
- `conflicts`
- `truth_eligible=false`
- `validation_required=true`

## ArtifactSemanticProfile Binding

O profile agora preserva:

- `relationship_provenance_traces`
- `relationship_conflict_summary`
- `relationship_negative_evidence_summary`
- `relationship_binding_quality`

Validation continua blocked por `relationship_final_validation_missing`, e agora tambem pode distinguir `relationship_provenance_missing` e `relationship_conflict_present`.

## Validation e Speaker Truth

`SemanticSelfReview` agora distingue:

- `RELATIONSHIP_CANDIDATE_OBSERVED`
- `RELATIONSHIP_EVIDENCE_PRESENT`
- `RELATIONSHIP_PROVENANCE_PRESENT`
- `RELATIONSHIP_CONFLICT_PRESENT`
- `RELATIONSHIP_EVIDENCE_INSUFFICIENT`
- `RELATIONSHIP_VALIDATION_REQUIRED`
- `RELATIONSHIP_TRUTH_NOT_ELIGIBLE`

Candidato maduro ainda nao passa final validation. Speaker Truth nao pode declarar relacao final.

## CVL Awareness

CVL reconhece:

- `RELATIONSHIP_PROVENANCE_MISSING`
- `RELATIONSHIP_CONFLICT_UNRESOLVED`
- `RELATIONSHIP_CONFIDENCE_INSUFFICIENT`
- `RELATIONSHIP_VALIDATION_REQUIRED`

As previsoes partem de profile metadata/coverage/capability, nao de projeto, arquivo ou path.

## Service-Equivalent Validation

Validado:

- candidate com multiplos sinais positivos;
- candidate com sinal isolado;
- candidate com conflito;
- candidate com negative evidence;
- profile com provenance/conflict/negative summaries;
- CVL com fronteira de provenance.

## Testes Executados

```text
python -m pytest tests/unit/test_relationship_evidence_provenance_maturity.py tests/unit/test_media_relationship_foundation.py tests/unit/test_cognitive_validation_laboratory_service.py -q
26 passed in 0.89s
```

```text
python -m pytest tests/unit/test_relationship_evidence_provenance_maturity.py tests/unit/test_media_relationship_foundation.py tests/unit/test_contract_driven_perception_service.py tests/unit/test_artifact_semantic_contract_service.py tests/unit/test_cognitive_validation_laboratory_service.py tests/unit/test_universal_task_session_service.py -q
65 passed in 8.61s
```

```text
python -m py_compile ...
PASS
```

## Hardcode Audit

Busca por projeto/path/extensoes/relacoes finais encontrou apenas o extractor generico de path existente para atributos (`extension`, `basename`, `stem`, `parent_path`, `file_name`).

Nao houve regra nova para FireTest, Pinhoabacaxi, `music_inventory.csv`, caminhos locais, `.lrc`, `.jpg`, `.mp4`, `.m4a`, `lyrics_for`, `artwork_for`, `album_art_for` ou `sidecar_of`.

## Gaps Restantes

- Artifact contract activation/rendering de relationship fields ainda nao foi implementado.
- Relationship final validation/readiness policy ainda nao existe.
- Public path boundary segue externo a H1B5.x.

## Proxima Wave Recomendada

H1B5.2 - Relationship-Aware Artifact Contract Activation.

## Por Que Nao Houve Bypass

- Detector continua governado por `ContractDrivenPerceptionService` e `CapabilityRegistry`.
- Renderer nao chama detector.
- Backend nao escreve artifact.
- Evidence/provenance nao viram Truth.
- Confidence alta nao vira Validation PASS.
- Extensao/stem/diretorio continuam sinais, nao autoridade.

