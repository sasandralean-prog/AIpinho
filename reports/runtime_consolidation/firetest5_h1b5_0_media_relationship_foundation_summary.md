# FireTest 5 H1B5.0 - Media Relationship Capability Foundation

## Veredito

FIRETEST5_H1B5_0_MEDIA_RELATIONSHIP_FOUNDATION_READY

## Objetivo

Criar fundacao semantica e contratual para candidatos de relacionamento entre entidades de midia, sem resolver sidecars como verdade final e sem depender do caminho publico `/api/v1/chat`.

## Escopo

- IRs canonicos para RelationshipGoal, RelationshipCandidate, RelationshipEvidence, RelationshipObservation e binding.
- Capability governada `media_relationship_candidate_detector` no registry de percepcao existente.
- Detector service-equivalent que produz candidatos a partir de sinais genericos combinados.
- EvidenceRecord canonico com `evidence_type = relationship_observation`.
- ArtifactSemanticProfile com binding/resumo de relationship observations.
- Validation/SemanticSelfReview bloqueando promocao de candidatos para relacao final.
- Summary leve `relationship_cognition`.
- Awareness de CVL/Fase 0 para fronteiras de relationship capability/evidence/validation.

## Nao-goals

- Nao implementar H1B5 completo.
- Nao declarar `lyrics_for`, `artwork_for`, `album_art_for` ou `sidecar_of` como verdade operacional.
- Nao resolver sidecars, observations, Knowledge Graph/H1D, parsers ou public chat boundary.
- Nao tentar FIRETEST5_READY.

## Arquivos alterados

- `src/aipinho/schemas/artifacts/relationship.py`
- `src/aipinho/schemas/artifacts/observed_entity.py`
- `src/aipinho/schemas/artifacts/artifact_semantic_profile.py`
- `src/aipinho/schemas/artifacts/contract_perception.py`
- `src/aipinho/schemas/artifacts/__init__.py`
- `src/aipinho/services/artifacts/media_relationship_candidate_service.py`
- `src/aipinho/services/artifacts/contract_driven_perception_service.py`
- `src/aipinho/services/artifacts/artifact_semantic_contract_service.py`
- `src/aipinho/services/governance/runtime/readonly_analysis_artifact_runtime_service.py`
- `src/aipinho/services/runtime/universal_task_session_service.py`
- `src/aipinho/services/cvl/cognitive_validation_laboratory_service.py`
- `tests/unit/test_media_relationship_foundation.py`
- `tests/unit/test_cognitive_validation_laboratory_service.py`

## Arquitetura antes/depois

Antes, `ArtifactSemanticProfile` ja tinha `expected_relationships`, mas nao havia IR canonico, capability governada, evidence record nem binding para relationship observations.

Depois:

```text
ObservedEntity
-> RelationshipGoal
-> CapabilityRegistry
-> media_relationship_candidate_detector
-> RelationshipCandidate
-> RelationshipEvidence
-> RelationshipObservation
-> EvidenceRecord
-> ArtifactSemanticProfile
-> Validation/SemanticSelfReview
-> Summary leve
```

## IRs criados

- `RelationshipGoal`
- `RelationshipCandidate`
- `RelationshipEvidence`
- `RelationshipEvidenceSignal`
- `RelationshipObservation`
- `RelationshipConfidence`
- `RelationshipProvenance`
- `RelationshipLimitation`
- `RelationshipValidationHint`
- `RelationshipBinding`

Todo `RelationshipCandidate` nasce com:

```text
truth_eligible = false
validation_required = true
status = candidate
```

## Taxonomia e evidence signals

Familias candidatas suportadas incluem `descriptive_sidecar_candidate`, `visual_sidecar_candidate`, `textual_sidecar_candidate`, `metadata_sidecar_candidate`, `collection_member_candidate`, `variant_candidate`, `derived_asset_candidate`, `same_work_candidate` e `unknown_related_asset_candidate`.

Signals implementados nesta foundation:

- `normalized_stem_similarity`
- `same_directory_context`
- `near_directory_context`
- `source_root_role_compatibility`
- `entity_role_compatibility`
- `artifact_contract_relevance`
- `filename_token_overlap`

Nenhum signal isolado valida relacao final. Extensao nao foi implementada como signal de autoridade nem como regra especifica.

## Capability contract

A capability `media_relationship_candidate_detector` foi registrada no `CapabilityRegistry` existente de `ContractDrivenPerceptionService`, com:

- input via `ObservedEntity`, roles, root roles, artifact contract e `RelationshipGoal`;
- output como candidates/evidence/observations/EvidenceRecord;
- `safe_to_run_readonly = true` por desenho de service-equivalent;
- limitations explicitas de candidate-only;
- preconditions para observed entities, relationship goal, entity role, source root role e registry ativo.

Se a capability nao estiver no registry, o resultado bloqueia com:

```text
NO_MATCHING_RELATIONSHIP_CAPABILITY
```

## Registry/matching/arbitration

H1B5.0 nao criou registry paralelo. O detector so roda dentro de `ContractDrivenPerceptionService` quando existe `RelationshipGoal` derivado de contrato/semantica declarada. Renderer e backend nao chamam o detector.

## EvidenceRecord integration

`EvidenceRecord` agora pode representar `relationship_observation` com:

- `candidate_id`
- `source_entity_ref`
- `target_entity_ref`
- `relation_family`
- `relation_kind_candidate`
- `signals`
- `truth_eligible = false`

Esses records entram no `EvidenceSet`, mas nao viram attribute knowledge nem Speaker Truth.

## ArtifactSemanticProfile binding

O profile agora preserva:

- `bound_relationship_observations`
- `relationship_evidence_summary`
- `relationship_candidates_by_artifact`
- `relationship_confidence_summary`
- `relationship_limitations`

Quando ha candidatos, o profile registra `relationship_final_validation_missing` com reason:

```text
RELATIONSHIP_VALIDATION_REQUIRED
```

## Validation e Speaker Truth

Validation distingue:

- `relationship_candidate_present`
- `relationship_evidence_present`
- `relationship_final_validation_missing`
- `relationship_not_truth_eligible`

`SemanticSelfReview` adiciona pergunta bloqueante `RELATIONSHIP_FINAL_VALIDATION_REQUIRED`, entao candidatos nao promovem Validation, Completion ou Speaker Truth.

## Summary behavior

`UniversalTaskSessionService` adicionou summary leve:

```json
{
  "relationship_cognition": {
    "status": "available|blocked|not_available",
    "candidate_count": 0,
    "observation_count": 0,
    "evidence_count": 0,
    "relation_families": [],
    "confidence_summary": {},
    "truth_eligible": false,
    "reason_codes": [],
    "source": "artifact_relationship_binding"
  }
}
```

Sem listas gigantes inline.

## Fase 0/CVL awareness

CVL agora reconhece metadata declarativa `relationship_cognition` e pode prever:

- `MEDIA_RELATIONSHIP_CAPABILITY_MISSING`
- `RELATIONSHIP_EVIDENCE_INSUFFICIENT`
- `RELATIONSHIP_VALIDATION_REQUIRED`

A previsao vem de profile metadata/coverage/capability availability, nao de nome de projeto, arquivo ou FireTest.

## Service-equivalent validation

Cenario minimo validado em testes:

- entidades media-like/text-like com sinais suficientes criam candidatos;
- sinal isolado de stem nao cria candidato;
- extensao nao aparece como autoridade;
- capability ausente bloqueia via registry;
- relationship observation gera EvidenceRecord;
- ArtifactSemanticProfile recebe binding;
- Validation permanece blocked quando relacao final nao foi validada;
- summary leve nao carrega payload gigante.

## Testes executados

```text
python -m pytest tests/unit/test_media_relationship_foundation.py -q
7 passed in 0.36s
```

```text
python -m pytest tests/unit/test_media_relationship_foundation.py tests/unit/test_contract_driven_perception_service.py tests/unit/test_artifact_semantic_contract_service.py tests/unit/test_cognitive_validation_laboratory_service.py tests/unit/test_universal_task_session_service.py -q
59 passed in 8.49s
```

```text
python -m py_compile ...
PASS
```

## Hardcode audit

Busca por FireTest/projeto/caminho/extensoes especificas encontrou apenas nomes existentes do CVL (`FireTestProfile`, `FireTestLaboratoryService`) em modulo/testes de CVL.

Nao foram adicionadas regras para:

- Pinhoabacaxi
- `music_inventory.csv`
- caminhos locais
- `.lrc`, `.jpg`, `.mp4`, `.m4a`
- `lyrics_for`, `artwork_for`, `album_art_for`, `sidecar_of`

## Public diagnostic

Nao executado nesta wave. O public path ainda tem finding conhecido de boundary sincronico/client timeout. H1B5.0 foi validada por caminho service-equivalent, conforme escopo.

## Gaps restantes

- Relationship final validation ainda nao existe.
- Artifact contract activation/rendering de campos de relacionamento ainda e minima.
- Public chat accepted_running/timeout_blocked segue como fronteira externa.
- H1B5.1 deve amadurecer provenance/binding ou ativacao de artifact contracts, dependendo da proxima prioridade.

## Proxima wave recomendada

H1B5.1 - Relationship Evidence & Provenance Binding Maturity.

Alternativa, se a prioridade for materializar em artifacts:

H1B5.1 - Relationship-Aware Artifact Contract Activation.

## Por que nao houve bypass

- Nao houve scanner paralelo.
- Nao houve registry paralelo.
- Nao houve chamada renderer -> detector.
- Nao houve backend escrevendo artifact.
- Nao houve hardcode de FireTest, arquivo, projeto ou path local.
- Extensao/stem/diretorio sao tratados como sinais genericos, nao autoridade final.
- Validation/Completion/Speaker Truth continuam preservados.

