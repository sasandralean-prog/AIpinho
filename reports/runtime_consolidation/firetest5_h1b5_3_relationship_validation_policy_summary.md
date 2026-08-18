# H1B5.3 — Relationship Validation Policy / Final Relation Readiness

Veredito:

```text
FIRETEST5_H1B5_3_RELATIONSHIP_VALIDATION_POLICY_READY
```

## Objetivo

Criar uma política governada para decidir quando um `RelationshipCandidate` está pronto para validação final, sem transformar readiness, confidence ou sinais isolados em Truth.

## Escopo

- `RelationshipValidationPolicy`
- `RelationshipValidationResult`
- `RelationshipValidationPolicyService`
- avaliação de readiness com provenance, evidence, confidence, conflicts, negative evidence e ambiguity
- integração com `ArtifactSemanticProfile`
- campos de artifact contract para status/códigos/contadores de validation readiness
- summary leve
- awareness no CVL/Fase 0
- validação service-equivalent

## Não-goals Preservados

- não buscar `FIRETEST5_READY`
- não validar relação final por extensão, stem ou diretório
- não declarar `lyrics_for`, `artwork_for`, `album_art_for` ou `sidecar_of` como verdade operacional
- não criar Knowledge Graph/H1D
- não mexer em public chat boundary
- não relaxar Validation, Completion ou Speaker Truth

## Arquivos Alterados

- `src/aipinho/schemas/artifacts/relationship.py`
- `src/aipinho/schemas/artifacts/artifact_semantic_profile.py`
- `src/aipinho/schemas/artifacts/__init__.py`
- `src/aipinho/services/artifacts/relationship_validation_policy_service.py`
- `src/aipinho/services/artifacts/artifact_semantic_contract_service.py`
- `src/aipinho/services/governance/runtime/readonly_analysis_artifact_runtime_service.py`
- `src/aipinho/services/runtime/universal_task_session_service.py`
- `src/aipinho/services/cvl/cognitive_validation_laboratory_service.py`
- `tests/unit/test_relationship_validation_policy.py`
- `tests/unit/test_relationship_aware_artifact_contract_activation.py`
- `tests/unit/test_media_relationship_foundation.py`

## RelationshipValidationPolicy

Política adicionada com:

- `minimum_signal_diversity`
- `minimum_confidence`
- `required_positive_signal_types`
- `forbidden_conflicts`
- `required_provenance_fields`
- `required_evidence_record_types`
- `negative_evidence_threshold`
- `ambiguity_policy`
- `truth_policy`
- `allow_validated_status`

Nenhuma regra depende de extensão, nome de projeto, caminho local ou artifact específico.

## RelationshipValidationResult

Resultado criado com:

- `status = not_ready|validation_ready|validated|rejected|blocked|conflicted`
- `reason_codes`
- `signals_passed`
- `signals_failed`
- `missing_requirements`
- `conflicts`
- `negative_evidence`
- `provenance_ok`
- `evidence_ok`
- `truth_eligible = false`
- `speaker_claim_allowed = false`

Mesmo quando `status = validation_ready`, Speaker Truth permanece bloqueado para claims finais.

## Ambiguity Handling

A política detecta:

- `one_source_many_targets`
- `many_sources_one_target`

Quando `ambiguity_policy.allow_ambiguous` não está explicitamente habilitado, ambiguidade gera:

```text
RELATIONSHIP_AMBIGUITY_UNRESOLVED
```

e impede readiness final.

## Conflict Handling

Conflitos bloqueantes geram:

```text
RELATIONSHIP_CONFLICT_BLOCKED
```

e status:

```text
conflicted
```

Negative evidence pode impedir readiness via:

```text
RELATIONSHIP_NEGATIVE_EVIDENCE_THRESHOLD_EXCEEDED
```

## Validation Ready vs Validated vs Truth

Estados separados:

- `not_ready`: faltam requisitos.
- `blocked`: ambiguidade ou bloqueio de política.
- `conflicted`: conflito bloqueante.
- `validation_ready`: candidato tem evidence/provenance/confidence suficientes para uma próxima camada validar.
- `validated`: somente quando a política permite explicitamente.

Mesmo `validated` nesta wave não habilita Speaker Truth automaticamente:

```text
truth_eligible = false
speaker_claim_allowed = false
```

## ArtifactSemanticProfile Integration

O profile agora preserva:

- `relationship_validation_results`
- `relationship_validation_summary`
- `validation_ready_count`
- `validated_relationship_count`
- `blocked_relationship_count`
- `conflicted_relationship_count`
- `truth_eligible_relationship_count`

`relationship_final_validation_missing` continua sendo gap semântico quando há candidates, preservando Validation conservadora.

## Artifact Contract Behavior

Campos suportados:

- `relationship_validation_status`
- `relationship_validation_reason_codes`
- `relationship_validation_ready_count`
- `relationship_conflicted_count`

Esses campos são derivados de binding/profile/perception já existentes. O renderer não observa, não chama detector e não cria EvidenceRecord.

## Validation / Completion / Speaker Truth

Validation segue bloqueada para relação final enquanto houver apenas candidates/readiness.

Completion não foi relaxado.

Speaker Truth não declara relação final. A única afirmação segura permanece limitada a candidatos, evidência, provenance e readiness quando suportados por `EvidenceRecord`/profile.

## CVL Awareness

CVL agora reconhece fronteiras:

- `RELATIONSHIP_VALIDATION_POLICY_MISSING`
- `RELATIONSHIP_AMBIGUITY_UNRESOLVED`
- `RELATIONSHIP_CONFLICT_BLOCKED`
- `RELATIONSHIP_TRUTH_POLICY_NOT_SATISFIED`

A previsão vem de `profile.metadata.relationship_cognition`, capability/profile/contexto declarados, não de strings de FireTest, projeto ou caminho local.

## Service-Equivalent Validation

Cenários cobertos:

- sinal isolado não vira `validation_ready`
- evidence suficiente sem provenance não vira `validation_ready`
- conflito bloqueante vira `conflicted`
- ambiguidade vira `blocked`
- evidence/provenance/confidence suficientes viram `validation_ready`
- `validated` só ocorre quando a política permite explicitamente
- `validation_ready` e `validated` não liberam Speaker Truth
- profile recebe summary/counters
- summary público permanece leve
- CVL prevê policy frontier

## Testes Executados

```text
python -m pytest tests/unit/test_relationship_validation_policy.py tests/unit/test_relationship_aware_artifact_contract_activation.py tests/unit/test_relationship_evidence_provenance_maturity.py tests/unit/test_media_relationship_foundation.py tests/unit/test_contract_driven_perception_service.py tests/unit/test_artifact_semantic_contract_service.py tests/unit/test_cognitive_validation_laboratory_service.py tests/unit/test_universal_task_session_service.py -q
```

Resultado:

```text
77 passed in 11.70s
```

Compilação:

```text
python -m py_compile src/aipinho/schemas/artifacts/relationship.py src/aipinho/schemas/artifacts/artifact_semantic_profile.py src/aipinho/schemas/artifacts/__init__.py src/aipinho/services/artifacts/relationship_validation_policy_service.py src/aipinho/services/artifacts/artifact_semantic_contract_service.py src/aipinho/services/governance/runtime/readonly_analysis_artifact_runtime_service.py src/aipinho/services/runtime/universal_task_session_service.py src/aipinho/services/cvl/cognitive_validation_laboratory_service.py
```

Resultado: PASS.

Auditoria anti-hardcode nos arquivos novos/alterados da sequência: sem matches para FireTest/projeto/caminho/extensões específicas/relações finais proibidas.

## Gaps Restantes

- Public path pode continuar bloqueando antes do relationship flow por fronteiras externas já conhecidas.
- Relationship final validation ainda depende de política operacional mais ampla e integração com Success Contract real.
- Speaker Truth continua conservador e não deve declarar relação final sem Validation/Completion/Speaker Truth governados.

## Próxima Wave Recomendada

Se a prioridade for execução pública:

```text
H1B6 — Public Runtime Response Boundary accepted_running / timeout_blocked
```

Se a prioridade for FireTest 5 controlado:

```text
FireTest 5 diagnostic with Phase 0/CVL + relationship flow service-equivalent + public blocker registration
```

## Por Que Não Houve Bypass

- A capability de relationship permanece governada pelo registry/arbitration já existente.
- O renderer apenas materializa campos derivados.
- Backend não escreve artifact.
- EvidenceRecord não vira Truth.
- Confidence não vira Truth.
- Validation/Completion/Speaker Truth permanecem autoridades separadas.

## Regra Final Preservada

H1B5.3 permite dizer:

```text
há candidatos validation-ready, com evidence, provenance, confidence e política avaliadas
```

Ainda não permite dizer:

```text
esta relação é final e segura para Speaker Truth
```
