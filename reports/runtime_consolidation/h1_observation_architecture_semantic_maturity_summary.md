# Horizonte 1 - Observation Architecture, Capability Ecosystem e Semantic Maturity

Data: 2026-08-11

## Resultado

Status: `READY_WITH_FINDINGS`

Esta wave implementou uma fundacao incremental para maturidade semantica do Runtime, sem criar dominio especifico, observer especifico, bypass, classificador paralelo ou nova autoridade de Validation/Completion/Speaker Truth.

O escopo implementado foi propositalmente conservador:

```text
EvidenceRecord
-> KnowledgeRecord
-> SemanticAssertion
-> SemanticSelfReview
-> SemanticCoverage2
-> Runtime summary leve
```

A implementacao nao tentou concluir todos os 14 sprints como um bloco unico. Ela entregou a camada transversal necessaria para que as proximas evolucoes de Capability, CVL e Runtime Doctor consumam conhecimento/auditoria sem mover autoridade.

## Objetivo Arquitetural Atendido

Antes:

```text
Observation
-> Evidence
-> SemanticCoverage
-> Validation
```

Agora:

```text
Observation
-> EvidenceRecord
-> KnowledgeRecord
-> SemanticAssertion
-> SemanticSelfReview
-> SemanticCoverage2
-> Validation / Completion / Speaker Truth
```

O Runtime passa a diferenciar:

- valor observado;
- evidencia;
- conhecimento compilado;
- assertion semantica;
- hipotese sem suporte;
- readiness para truth.

## Regras Preservadas

- Nenhuma capability especifica de musica/audio/CSV/FireTest foi criada.
- Nenhum MediaMetadataObserver foi criado.
- Nenhuma regra por extensao, caminho, workspace ou artifact foi adicionada.
- Nenhum bypass de Validation, Completion ou Speaker Truth foi introduzido.
- Nenhum classificador concorrente de intent foi criado.
- Renderer continua sem decidir verdade.
- Backend/observer continua sem decidir Completion.
- Assertion sem evidencia nao vira truth.

## Arquivos Alterados

- `src/aipinho/schemas/artifacts/contract_perception.py`
- `src/aipinho/schemas/artifacts/__init__.py`
- `src/aipinho/services/artifacts/contract_driven_perception_service.py`
- `src/aipinho/services/runtime/universal_task_session_service.py`
- `tests/unit/test_contract_driven_perception_service.py`

## IRs Adicionadas

### KnowledgeRecord

Representa conhecimento compilado exclusivamente a partir de evidencia.

Campos principais:

- `entity_ref`
- `attribute_name`
- `canonical_key`
- `value`
- `state`
- `evidence_ids`
- `capability_ids`
- `observer_ids`
- `confidence`
- `provenance`
- `limitations`
- `history`

Estados suportados:

```text
UNKNOWN
DISCOVERED
OBSERVED
INFERRED
CORROBORATED
VERIFIED
CONFLICTED
INSUFFICIENT_EVIDENCE
REJECTED
```

Regra central:

```text
Sem EvidenceRecord, nao ha KnowledgeRecord.
```

### SemanticAssertion

Representa uma afirmacao semantica produzida pelo Runtime.

Ela pode estar em estados como:

```text
OBSERVED
VERIFIED
INSUFFICIENT_EVIDENCE
UNKNOWN
CONFLICTED
```

Campos principais:

- `assertion_kind`
- `state`
- `subject_ref`
- `predicate`
- `object_value`
- `canonical_key`
- `evidence_ids`
- `knowledge_ids`
- `capability_ids`
- `confidence`
- `truth_eligible`
- `blocking_reasons`

Regra central:

```text
Assertion sem evidencia pode existir como hipotese,
mas truth_eligible = false.
```

### SemanticQualityQuestion

Representa uma pergunta generica de qualidade semantica.

Perguntas iniciais implementadas:

- `EVIDENCE_PRESENT`
- `TRACEABILITY_PRESENT`
- `CONFIDENCE_SUFFICIENT`
- `HYPOTHESIS_NOT_PROMOTED_AS_FACT`

Essas perguntas sao genericas e independentes de dominio.

### SemanticSelfReview

Representa a autoauditoria interna antes de qualquer promocao para truth.

Campos principais:

- `questions`
- `assertion_count`
- `evidence_count`
- `knowledge_count`
- `findings`
- `truth_readiness`
- `can_promote_to_validation`
- `can_speaker_claim`
- `reason_codes`

Regra central:

```text
Self Review nao decide Validation.
Ele apenas explica se as assertions estao prontas para serem consideradas.
```

### SemanticCoverage2

Expande coverage para dimensoes separadas:

- structural
- entity
- attribute
- capability
- evidence
- knowledge
- semantic
- truth

Campos principais:

- `structural_coverage`
- `entity_coverage`
- `attribute_coverage`
- `capability_coverage`
- `evidence_coverage`
- `knowledge_coverage`
- `semantic_coverage`
- `truth_coverage`
- `dimension_statuses`
- `blocking_reasons`
- `is_truth_ready`

## Servicos Enriquecidos

### ContractDrivenPerceptionService

Novas etapas compiladas dentro do fluxo existente:

```text
knowledge_records()
semantic_assertions()
semantic_self_review()
semantic_coverage_2()
```

Essas etapas consomem `EvidenceSet`, `ObservationPlan` e `SemanticCoverageReport`.

Elas nao executam observers, nao escolhem capabilities, nao renderizam artifacts e nao alteram Validation.

### UniversalTaskSessionService

O summary leve de `observational_cognition` agora pode expor:

```json
{
  "semantic_coverage": {
    "knowledge": 0.5,
    "truth": 0.5,
    "semantic": 0.64
  },
  "knowledge": {
    "records": 1,
    "assertions": 2,
    "truth_eligible_assertions": 1,
    "self_review_truth_readiness": "blocked",
    "self_review_can_speaker_claim": false,
    "self_review_reason_codes": ["NO_MATCHING_CAPABILITY"]
  }
}
```

Isso melhora observabilidade sem obrigar UI/API a abrir artifacts profundos.

## Comportamento Semantico

Caso com atributo observado:

```text
ObservedEntity possui name
-> AttributeObservation observed
-> EvidenceRecord(name)
-> KnowledgeRecord(name, state=OBSERVED/VERIFIED)
-> SemanticAssertion(name, truth_eligible=true)
```

Caso com atributo requerido sem capability:

```text
Contrato exige codec
-> ObservationGoal(codec)
-> CapabilityMatch(NO_MATCHING_CAPABILITY)
-> CapabilityDecision(BLOCKED_NO_CAPABILITY)
-> ObservationTask(BLOCKED_NO_CAPABILITY)
-> sem EvidenceRecord(codec)
-> sem KnowledgeRecord(codec)
-> SemanticAssertion(codec, state=INSUFFICIENT_EVIDENCE)
-> truth_eligible=false
-> SemanticSelfReview blocked
-> SemanticCoverage2 truth_coverage parcial
```

Caso com atributo optional sem evidencia:

```text
Contrato declara requiredness=optional e evidence_required=false
-> ausencia nao bloqueia semantic completeness
-> assertion fica UNKNOWN
-> truth_eligible=false
-> self-review nao gera fail
```

## Testes Adicionados

Arquivo:

```text
tests/unit/test_contract_driven_perception_service.py
```

Novos testes:

- `test_semantic_knowledge_layer_only_promotes_evidence_backed_attributes`
- `test_optional_missing_attribute_is_reviewed_without_truth_promotion`

Cobrem:

- EvidenceRecord gera KnowledgeRecord.
- Atributo sem evidencia nao gera KnowledgeRecord.
- Assertion sem evidencia fica `INSUFFICIENT_EVIDENCE`.
- Assertion sem evidencia nao vira `truth_eligible`.
- Self Review bloqueia speaker claim quando falta evidencia.
- Coverage2 mede knowledge/truth separadamente.
- Optional sem evidencia nao vira sucesso falso nem bloqueio indevido.

## Testes Executados

```text
python -m pytest tests/unit/test_contract_driven_perception_service.py -q
13 passed

python -m pytest tests/unit/test_media_metadata_capability_pack.py tests/unit/test_observation_execution_boundary_service.py tests/unit/test_artifact_semantic_contract_service.py tests/unit/test_universal_task_session_service.py -q
36 passed

python -m pytest tests/unit/test_universal_task_session_service.py -q
8 passed

python -m pytest tests/governance/test_runtime_vertical_slice.py::test_public_chat_and_service_path_apply_corpus_entity_selection_policy -q
1 passed

python -m pytest tests/unit/test_contract_driven_perception_service.py tests/unit/test_media_metadata_capability_pack.py tests/unit/test_observation_execution_boundary_service.py tests/unit/test_artifact_semantic_contract_service.py tests/unit/test_universal_task_session_service.py tests/governance/test_runtime_vertical_slice.py::test_public_chat_and_service_path_apply_corpus_entity_selection_policy -q
50 passed
```

## Por Que Nao Houve Bypass

A implementacao nao altera o criterio de sucesso.

Ela apenas torna mais explicito o motivo pelo qual uma conclusao pode ou nao ser promovida.

Antes:

```text
missing attribute
```

Agora:

```text
attribute required
-> no evidence
-> no knowledge
-> assertion insufficient evidence
-> self review blocked
-> truth not ready
```

Validation continua decidindo contrato.
Completion continua dependendo de Validation.
Speaker Truth continua dependendo de Timeline, Artifacts, Validation e Completion.

## O Que Ainda Falta

Esta wave nao implementou completamente:

- CVL Evolution para prever knowledge/truth readiness.
- Runtime Doctor domains dedicados para `semantic_assertions`, `self_review`, `truth_readiness`.
- Capability marketplace completo.
- Evidence Fusion.
- Media metadata execution real.
- Sidecar/relationship model.

Esses pontos agora possuem IRs de base para evoluir sem salto cognitivo.

## Recomendacao de Proxima Wave

Sequencia sugerida:

1. **H1 Semantic Doctor View**
   - Ensinar Runtime Doctor a expor `KnowledgeRecord`, `SemanticAssertion`, `SemanticSelfReview` e `SemanticCoverage2`.

2. **CVL Semantic Maturity Prediction**
   - Fazer o CVL prever `Evidence Availability`, `Knowledge Availability`, `Truth Readiness` e `Semantic Completion`.

3. **H1B4 Runtime Activation**
   - Ativar de forma auditavel `media_metadata_reader` no runtime real, garantindo que todo valor venha de `EvidenceRecord`.

4. **H1B5 Sidecar Relationship Model**
   - Diferenciar entidades de corpus relacionadas sem transformar sidecars em tracks.

## Conclusao

Esta wave adiciona a primeira camada epistemologica explicita da AIpinho.

O Runtime agora nao apenas observa atributos. Ele consegue representar:

```text
o que foi evidenciado
o que virou conhecimento
o que esta sendo afirmado
o que ainda e hipotese
o que pode ser considerado por Validation
o que Speaker Truth ainda nao pode dizer
```

Essa mudanca aumenta maturidade cognitiva sem aumentar permissividade.

---

# Continuação - CVL, Runtime Doctor e Observabilidade Epistemológica

Data: 2026-08-11

## Resultado

Status: `READY_WITH_FINDINGS`

Esta continuação fez o CVL, o Runtime Doctor e o summary do Runtime consumirem a camada epistemológica criada anteriormente.

O objetivo foi aumentar observabilidade e capacidade preditiva, sem criar nova autoridade.

## O Que Foi Implementado

### CVL Semantic Maturity Prediction

O `CognitiveGapPredictor` agora entende uma seção declarativa:

```json
{
  "semantic_maturity": {
    "evidence_availability": "insufficient",
    "knowledge_availability": "unknown",
    "semantic_completion": "partial",
    "truth_readiness": "not_ready",
    "validation_probability": "low",
    "confidence": 0.87
  }
}
```

Novos reason codes preditivos:

- `PREDICTED_EVIDENCE_AVAILABILITY_GAP`
- `PREDICTED_KNOWLEDGE_AVAILABILITY_GAP`
- `PREDICTED_SEMANTIC_COMPLETION_GAP`
- `PREDICTED_TRUTH_READINESS_GAP`
- `PREDICTED_VALIDATION_PROBABILITY_LOW`

Precedência preservada:

```text
Semantic Ingress
-> Workspace Role Boundary / Entity Selection
-> Semantic Maturity
-> Capability Matching
```

Ou seja, o CVL não pula fronteiras anteriores.

### CVL Semantic Coverage Metrics

O `CognitiveCoverageService` agora produz métricas adicionais:

- `evidence_availability`
- `knowledge_availability`
- `semantic_completion`
- `truth_readiness`
- `validation_probability`

Essas métricas são puramente declarativas e não executam Runtime.

### Runtime Doctor Epistemic Domains

Foram adicionados domínios diagnósticos:

- `evidence_recording`
- `knowledge_representation`
- `semantic_assertions`
- `semantic_self_review`
- `truth_readiness`

Reason codes mapeados:

- `EVIDENCE_MISSING`
- `TRACEABILITY_MISSING`
- `CONFIDENCE_OR_EVIDENCE_INSUFFICIENT`
- `UNSUPPORTED_ASSERTION_PROMOTED`
- `EVIDENCE_CONFLICT`
- `KNOWLEDGE_MISSING`
- `TRUTH_NOT_READY`

O Doctor agora também coleta reason codes vindos de:

```text
semantic_self_review.reason_codes
semantic_self_review.findings
semantic_coverage_2.blocking_reasons
```

Antes, ele só classificava reason codes quando havia `semantic_gaps` tradicionais. Isso foi corrigido para suportar a nova IR.

### Runtime Summary

O summary leve de `observational_cognition` agora expõe:

```json
{
  "semantic_coverage": {
    "knowledge": 0.5,
    "truth": 0.5,
    "semantic": 0.65
  },
  "knowledge": {
    "records": 1,
    "assertions": 2,
    "truth_eligible_assertions": 1,
    "self_review_truth_readiness": "blocked",
    "self_review_can_speaker_claim": false,
    "self_review_reason_codes": ["NO_MATCHING_CAPABILITY"]
  }
}
```

Isso permite que UI/API entenda a diferença entre:

```text
artifact existe
valor existe
evidence existe
knowledge existe
truth pode ser afirmada
```

## Arquivos Alterados nesta Continuação

- `src/aipinho/services/cvl/cognitive_validation_laboratory_service.py`
- `src/aipinho/services/runtime/runtime_doctor_service.py`
- `src/aipinho/services/runtime_doctor/runtime_doctor_service.py`
- `src/aipinho/schemas/runtime/runtime_doctor.py`
- `src/aipinho/services/runtime/universal_task_session_service.py`
- `tests/unit/test_cognitive_validation_laboratory_service.py`
- `tests/unit/test_runtime_doctor_service.py`
- `tests/unit/test_universal_task_session_service.py`

## Testes Adicionados / Atualizados

Novos testes relevantes:

- `test_gap_predictor_predicts_semantic_maturity_after_entity_selection`
- `test_cognitive_coverage_reports_semantic_maturity_dimensions`
- `test_runtime_doctor_classifies_semantic_self_review_reason_codes`

Teste de summary enriquecido:

- `test_universal_task_summary_exposes_observational_cognition_block`

## Testes Executados

```text
python -m pytest tests/unit/test_cognitive_validation_laboratory_service.py -q
10 passed

python -m pytest tests/unit/test_runtime_doctor_service.py -q
15 passed

python -m pytest tests/unit/test_universal_task_session_service.py -q
8 passed

python -m pytest tests/unit/test_contract_driven_perception_service.py tests/unit/test_cognitive_validation_laboratory_service.py tests/unit/test_runtime_doctor_service.py tests/unit/test_universal_task_session_service.py tests/unit/test_media_metadata_capability_pack.py tests/unit/test_observation_execution_boundary_service.py tests/unit/test_artifact_semantic_contract_service.py tests/governance/test_runtime_vertical_slice.py::test_public_chat_and_service_path_apply_corpus_entity_selection_policy -q
75 passed
```

## O Que Continua Fora de Escopo

Ainda não foi implementado:

- execução real de media metadata backend no ambiente;
- sidecar relationship model;
- evidence fusion avançado;
- marketplace completo de capabilities;
- política cognitiva sofisticada de arbitragem multi-capability;
- FireTest rerun pós-continuação.

## Leitura Arquitetural

Agora a AIpinho possui uma cadeia mais completa:

```text
Contract
-> ObservationGoal
-> CapabilityMatch
-> ObservationTask
-> EvidenceRecord
-> KnowledgeRecord
-> SemanticAssertion
-> SemanticSelfReview
-> SemanticCoverage2
-> Runtime Doctor / CVL / Summary
-> Validation
-> Completion
-> Speaker Truth
```

Nenhuma dessas novas camadas substitui as autoridades finais. Elas apenas tornam o estado cognitivo mais explícito e auditável.

## Próximo Passo Recomendado

O próximo passo seguro é escolher uma das duas frentes:

1. **H1B4 Runtime Activation**
   - Garantir que `media_metadata_reader` seja carregado no runtime real e que backend ausente/disponível gere evidência ou erro tipado.

2. **H1B5 Relationship Model**
   - Modelar sidecars/assets do corpus sem tratá-los como audio tracks.

Antes de um FireTest completo, uma rodada diagnóstica curta pode confirmar se o summary já exibe `knowledge/truth/self_review` no caminho público real.
