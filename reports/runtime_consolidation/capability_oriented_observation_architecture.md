# AIpinho - Capability-Oriented Observation Architecture

## Objetivo

Esta wave evoluiu a fronteira de percepção da AIpinho sem criar observers específicos, regras de domínio, hardcodes ou fluxo paralelo. A mudança fortalece a cadeia canônica já existente:

```text
ContractObservationPlan
  -> CandidateEntitySet
  -> SpecializationHypothesis
  -> ObservationGoal
  -> ObservationStrategy
  -> CapabilityMatching
  -> CapabilityArbitration
  -> ObservationPlan
  -> AttributeObservation
  -> SemanticCoverage
```

## Responsabilidades

- `ObservationGoal`: representa o objetivo cognitivo da observação, isto é, qual atributo contratual deve ser conhecido, para quais entidades, com qual confiança mínima e origem contratual.
- `ObservationStrategy`: representa caminhos possíveis de observação, como ler atributo existente, calcular, inferir, consultar componente, executar observer ou combinar evidências.
- `CapabilityRegistry`: catálogo declarativo de capabilities observacionais. Ele não decide, não executa e não conhece contratos específicos.
- `CapabilityMatch`: explica quais capabilities são candidatas para uma estratégia e por quê.
- `CapabilityDecision`: registra a arbitragem determinística entre capabilities, incluindo alternativas rejeitadas, score, critérios e reason code.
- `AttributeObservation`: agora carrega method, capability, strategy, duration, provenance, evidence, timestamp e observer version.
- `SemanticCoverage`: agora distingue cobertura por domínio cognitivo e reason codes estruturados.

## Reason Codes

Foram introduzidos ou integrados reason codes genéricos:

- `NO_MATCHING_CAPABILITY`
- `CAPABILITY_REJECTED`
- `LOW_CONFIDENCE`
- `MULTIPLE_CAPABILITIES_AVAILABLE`
- `EXECUTION_FAILED`
- `ATTRIBUTE_VALUE_NOT_OBSERVED`

Quando um atributo não pode ser observado por ausência de capability, a cadeia preserva causalidade:

```text
ATTRIBUTE_NOT_OBSERVED
  -> OBSERVER_CAPABILITY_MISSING
  -> NO_MATCHING_CAPABILITY
```

## Runtime Doctor

O Runtime Doctor passou a compreender os novos domínios:

- `observation_goal`
- `observation_strategy`
- `capability_registry`
- `capability_matching`
- `capability_arbitration`
- `observer_execution`

Isso permite diferenciar falhas de seleção, matching, empate, rejeição, baixa confiança e execução ausente.

## Arquivos Alterados

- `src/aipinho/schemas/artifacts/contract_perception.py`
- `src/aipinho/schemas/artifacts/__init__.py`
- `src/aipinho/services/artifacts/contract_driven_perception_service.py`
- `src/aipinho/schemas/runtime/runtime_doctor.py`
- `src/aipinho/services/runtime/runtime_doctor_service.py`
- `src/aipinho/services/runtime_doctor/runtime_doctor_service.py`
- `tests/unit/test_contract_driven_perception_service.py`
- `tests/unit/test_runtime_doctor_service.py`

## Compatibilidade

A implementação preserva as autoridades existentes:

- Artifact Runtime continua responsável por artifacts.
- Validation continua responsável por bloquear ou passar.
- Completion continua dependente de Validation.
- Speaker Truth não foi alterado.
- Nenhum observer específico foi criado.
- Nenhuma lógica específica para FireTest, música, codec, CSV ou mídia foi adicionada.

## Validação Executada

```text
python -m pytest tests\unit\test_contract_driven_perception_service.py tests\unit\test_runtime_doctor_service.py -q
19 passed

python -m pytest tests\unit\test_contract_driven_perception_service.py tests\unit\test_observed_entity_compilation_service.py tests\unit\test_artifact_semantic_contract_service.py tests\unit\test_runtime_doctor_service.py tests\unit\test_runtime_operator_ro.py -q
46 passed

python -m pytest tests\governance\test_g21_readonly_analysis_intent.py -q
15 passed

python -m pytest tests\governance\test_runtime_vertical_slice.py -q
11 passed
```

A execução combinada dos dois arquivos de governance excedeu o timeout local, mas ambos passaram quando executados separadamente.

## Veredito

READY

A AIpinho agora consegue explicar não apenas que um atributo não foi observado, mas em qual ponto da cadeia cognitiva a observação deixou de ser possível: goal, strategy, registry, matching, arbitration ou execution.
