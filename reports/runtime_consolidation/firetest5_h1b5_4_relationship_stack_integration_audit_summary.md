# H1B5.4 — Relationship Stack Integration Audit

Veredito:

```text
FIRETEST5_H1B5_4_RELATIONSHIP_STACK_INTEGRATION_AUDIT_READY
```

## Objetivo

Auditar se H1B5.0-H1B5.3 formam uma pilha semântica única e governada, atravessando de `RelationshipGoal` até validation readiness e summary sem bypass, hardcode, fluxo paralelo ou Truth prematuro.

## Escopo

- leitura dos relatórios H1B5.0-H1B5.3;
- extração de contratos prévios;
- audit de contract drift;
- teste end-to-end service-equivalent;
- matriz de autoridades;
- audit de fallback silencioso;
- audit de summary payload;
- audit de CVL/Fase 0;
- audit anti-hardcode;
- uma correção pequena de coerência no elo EvidenceRecord/readiness.

## Não-goals

- não implementar H1B6;
- não mexer em `/api/v1/chat`;
- não implementar `accepted_running`/`timeout_blocked`;
- não rodar FireTest público;
- não resolver ProjectAnalysis;
- não implementar Knowledge Graph/H1D;
- não transformar `validation_ready` ou `validated` em Truth;
- não criar nova capability, registry paralelo, renderer observador ou regra específica.

## Relatórios Lidos

- `reports/runtime_consolidation/firetest5_h1b5_0_media_relationship_foundation_summary.md`
- `reports/runtime_consolidation/firetest5_h1b5_1_relationship_evidence_provenance_summary.md`
- `reports/runtime_consolidation/firetest5_h1b5_2_relationship_aware_artifact_contract_summary.md`
- `reports/runtime_consolidation/firetest5_h1b5_3_relationship_validation_policy_summary.md`

Extração gerada:

```text
reports/runtime_consolidation/firetest5_h1b5_4_prior_wave_contracts_extracted.json
```

## Fluxo End-to-End Auditado

O teste `tests/unit/test_relationship_stack_integration_audit.py` cobre:

```text
RelationshipGoal
-> CapabilityRegistry
-> CapabilityArbitration/preconditions
-> media_relationship_candidate_detector
-> RelationshipCandidate
-> RelationshipEvidenceSignal
-> RelationshipProvenanceTrace
-> RelationshipConfidenceModel
-> RelationshipNegativeEvidence / RelationshipConflict
-> RelationshipObservation
-> EvidenceRecord
-> ArtifactSemanticProfile
-> relationship-aware artifact contract fields
-> renderer materialization from perception_payload only
-> RelationshipValidationPolicy
-> RelationshipValidationResult
-> Validation/SemanticSelfReview
-> Summary relationship_cognition
-> Speaker Truth blocked for final relation
```

Cenários cobertos:

- candidate maduro com `validation_ready`;
- sinal isolado;
- conflito bloqueante;
- ambiguidade;
- provenance ausente;
- EvidenceRecord ausente;
- renderer safety;
- registry guard;
- `validated` sem Speaker Truth automático.

## Contract Drift Audit

Gerado:

```text
reports/runtime_consolidation/firetest5_h1b5_4_contract_drift_audit.json
```

Achado principal:

- Antes da correção H1B5.4, `RelationshipValidationPolicyService` aceitava `evidence_refs` como suficiente para `evidence_ok`.
- Isso poderia permitir `validation_ready` sem `EvidenceRecord` canônico.
- Corrigido nesta wave: readiness agora exige `EvidenceRecord(evidence_type=relationship_observation)` correspondente.

Drifts restantes:

- nenhum bloqueante.
- `RELATIONSHIP_CONFLICT_UNRESOLVED` permanece como wording legado de H1B5.1; readiness usa `RELATIONSHIP_CONFLICT_BLOCKED`.

## Authority Boundary Matrix

Gerado:

```text
reports/runtime_consolidation/firetest5_h1b5_4_authority_boundary_matrix.md
```

Resumo:

- CapabilityRegistry seleciona capability; não decide Truth.
- Detector produz candidates/evidence/observations; não valida relação final.
- EvidenceRecord preserva evidência; não vira Truth.
- ArtifactSemanticProfile faz binding; não observa nem chama detector.
- Renderer materializa; não observa, não infere, não cria evidence.
- RelationshipValidationPolicyService calcula readiness; não libera Speaker Truth.
- Validation/Completion/Speaker Truth seguem autoridades separadas.
- CVL prevê; não executa Runtime.

## Silent Fallback Audit

Gerado:

```text
reports/runtime_consolidation/firetest5_h1b5_4_silent_fallback_audit.json
```

Resultado:

```text
PASS
```

Casos validados:

- missing provenance -> `not_ready`;
- missing EvidenceRecord -> `not_ready`;
- missing RelationshipGoal -> `not_available`, detector não roda;
- missing registry match -> `blocked`, detector não roda;
- conflict -> `conflicted`;
- missing Truth policy -> `speaker_claim_allowed=false`;
- renderer sem payload governado não observa nem cria evidence.

## Summary Payload Audit

Gerado:

```text
reports/runtime_consolidation/firetest5_h1b5_4_summary_payload_audit.json
```

`relationship_cognition` segue leve:

- contém counts/status/confidence summary/reason codes/ref counts;
- não contém lista de candidates;
- não contém payload bruto de evidence;
- não contém provenance trace completo;
- não contém conteúdo de arquivo.

## CVL/Fase 0 Coherence Audit

Gerado:

```text
reports/runtime_consolidation/firetest5_h1b5_4_cvl_phase0_coherence_audit.json
```

Frontiers auditadas:

- `MEDIA_RELATIONSHIP_CAPABILITY_MISSING`
- `RELATIONSHIP_EVIDENCE_INSUFFICIENT`
- `RELATIONSHIP_PROVENANCE_MISSING`
- `RELATIONSHIP_CONFIDENCE_INSUFFICIENT`
- `RELATIONSHIP_VALIDATION_REQUIRED`
- `RELATIONSHIP_VALIDATION_POLICY_MISSING`
- `RELATIONSHIP_AMBIGUITY_UNRESOLVED`
- `RELATIONSHIP_CONFLICT_BLOCKED`
- `RELATIONSHIP_TRUTH_POLICY_NOT_SATISFIED`

Origem da previsão:

- `profile.metadata.relationship_cognition`;
- estado de capability;
- coverage;
- policy state;
- validation/truth policy state.

Não foi encontrada previsão por string de projeto, path local, artifact específico ou extensão específica.

## Anti-Hardcode Audit

Gerado:

```text
reports/runtime_consolidation/firetest5_h1b5_4_antihardcode_audit.md
```

Resultado:

```text
PASS
```

Achados permitidos:

- `FireTestProfile`, `FireTestSuite`, `FireTestLaboratoryService` no CVL/testes.

Achados bloqueantes:

- nenhum.

## Correções Realizadas

Arquivos alterados nesta wave:

- `src/aipinho/services/artifacts/relationship_validation_policy_service.py`
- `src/aipinho/services/artifacts/artifact_semantic_contract_service.py`
- `tests/unit/test_relationship_stack_integration_audit.py`
- `tests/unit/test_relationship_validation_policy.py`
- `tests/unit/test_relationship_aware_artifact_contract_activation.py`

Correção:

- `RelationshipValidationPolicyService.validate_many` agora recebe `evidence_records`.
- `ArtifactSemanticContractService` coleta relationship EvidenceRecords de `artifact_relationship_binding.relationship_evidence_records` ou `perception.evidence_set.records`.
- `validation_ready` exige EvidenceRecord canônico correspondente por `candidate_id`, `observation_id` ou `evidence_id`.
- Missing EvidenceRecord gera:

```text
RELATIONSHIP_CANONICAL_EVIDENCE_RECORD_MISSING
```

Essa correção é de coerência e fecha um fallback silencioso. Não cria capability, registry, renderer, parser ou Truth nova.

## Testes Executados

Teste H1B5.4 isolado:

```text
python -m pytest tests/unit/test_relationship_stack_integration_audit.py -q
```

Resultado:

```text
9 passed in 3.53s
```

Conjunto integrado:

```text
python -m pytest tests/unit/test_relationship_stack_integration_audit.py tests/unit/test_relationship_validation_policy.py tests/unit/test_relationship_aware_artifact_contract_activation.py tests/unit/test_relationship_evidence_provenance_maturity.py tests/unit/test_media_relationship_foundation.py tests/unit/test_contract_driven_perception_service.py tests/unit/test_artifact_semantic_contract_service.py tests/unit/test_cognitive_validation_laboratory_service.py tests/unit/test_universal_task_session_service.py -q
```

Resultado:

```text
86 passed in 15.76s
```

## Py Compile

Executado:

```text
python -m py_compile src/aipinho/services/artifacts/relationship_validation_policy_service.py src/aipinho/services/artifacts/artifact_semantic_contract_service.py src/aipinho/services/governance/runtime/readonly_analysis_artifact_runtime_service.py src/aipinho/services/runtime/universal_task_session_service.py src/aipinho/services/cvl/cognitive_validation_laboratory_service.py tests/unit/test_relationship_stack_integration_audit.py tests/unit/test_relationship_validation_policy.py tests/unit/test_relationship_aware_artifact_contract_activation.py
```

Resultado: PASS.

## Gaps Restantes

- Public path ainda pode bloquear antes do relationship flow.
- FireTest público não foi executado nesta wave.
- `validated` continua não sendo Speaker Truth automático.
- Success Contract final de relação ainda precisa de diagnóstico controlado antes de qualquer afirmação operacional final.

## Próxima Recomendação

Executar FireTest 5 diagnóstico controlado com:

```text
Phase 0/CVL
relationship flow service-equivalent
public blocker registration
```

Se o caminho público bloquear antes do relationship flow:

```text
H1B6 — Public Runtime Response Boundary accepted_running / timeout_blocked
```

## Por Que Não Houve Bypass

- Detector só roda após `RelationshipGoal` e capability disponível no registry.
- Teste confirma que missing registry match bloqueia antes do detector.
- Renderer só chama `_relationship_render_field_value` sobre `perception_payload`.
- Backend não escreve artifact.
- EvidenceRecord não vira Truth.

## Por Que Não Houve Hardcode

- Auditoria não encontrou regra nova baseada em FireTest/projeto/path/extensão/artifact específico.
- Entidades dos testes são sintéticas e exercitam sinais genéricos.
- Extensão, stem, diretório e nome continuam sinais ou fixtures, não autoridade.

## Por Que Não Houve Fluxo Paralelo

- A cadeia passa pelo `ContractDrivenPerceptionService`.
- `CapabilityRegistry` segue sendo o ponto de seleção.
- `ArtifactSemanticProfile` recebe binding do payload governado.
- `RelationshipValidationPolicyService` consome observations/provenance/EvidenceRecord já produzidos.

## Por Que Renderer Não Virou Observer

- Renderer não chama `media_relationship_candidate_detector`.
- Renderer não cria `RelationshipEvidence`, `RelationshipObservation` ou `EvidenceRecord`.
- Renderer não infere por extensão/nome/path.
- Renderer apenas materializa campos `relationship_*` presentes no payload.

## Por Que Validation Ready Não Virou Truth

- `RelationshipValidationResult.truth_eligible=false`.
- `RelationshipValidationResult.speaker_claim_allowed=false`.
- `ArtifactSemanticProfile.truth_eligible_relationship_count=0`.
- `relationship_final_validation_missing` continua gap quando há candidates.
- `SemanticSelfReview.can_speaker_claim=false`.

## Speaker Truth Conservador

Mesmo com:

```text
RelationshipValidationResult.status = validation_ready
```

ou:

```text
RelationshipValidationResult.status = validated
```

a wave preserva:

```text
truth_eligible = false
speaker_claim_allowed = false
```

Logo, a AIpinho pode relatar candidatos e readiness auditável, mas não pode declarar relação final.
