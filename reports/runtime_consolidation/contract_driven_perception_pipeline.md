# Contract-Driven Perception Pipeline

## Status

READY

Esta wave introduziu uma camada generica de percepcao dirigida por contrato entre `ObservedEntityGraph` e o renderer de artifacts. A implementacao nao adiciona runtime paralelo, nao altera Validation, Completion ou Speaker Truth, e nao cria regras especificas para FireTest, midia, audio, CSV ou extensoes.

## Fluxo Cognitivo

```text
ObservedEntityGraph
  -> ContractObservationPlan
  -> CandidateEntitySet
  -> SpecializationHypothesis
  -> ObservationPlan
  -> AttributeObservation
  -> SemanticCoverage
  -> Contract-Aware Renderer
  -> ArtifactSemanticProfile
  -> Validation
  -> Completion
  -> Speaker Truth
```

## Novas IRs

- `ContractObservationPlan`: representa o que o contrato precisa observar.
- `CandidateEntitySet`: ranqueia entidades observadas que podem satisfazer o contrato.
- `SpecializationHypothesis`: registra hipoteses de especializacao derivadas do contrato sem alterar a entidade original.
- `ObservationPlan`: declara quais atributos ainda precisam ser observados e qual capability poderia observa-los.
- `AttributeObservation`: registra valor, confianca, evidencia, observer e metodo de aquisicao.
- `SemanticCoverage`: mede quanto do contrato foi observado, o que falta, o que e ambiguo e o que nao possui capability.

## Responsabilidades Preservadas

- `ObservedEntityCompilationService` continua compilando evidencias brutas em entidades observadas.
- `ContractDrivenPerceptionService` apenas compila percepcao a partir do contrato e do grafo.
- `ReadonlyAnalysisArtifactRuntimeService` continua sendo o renderer governado de artifacts readonly.
- `ArtifactSemanticContractService` continua sendo a fronteira de perfil e validacao semantica de artifact.
- `RuntimeDoctorService` apenas classifica melhor os gaps.
- Validation, Completion e Speaker Truth permanecem autoridades finais.

## Gaps Mais Explicaveis

`ATTRIBUTE_NOT_OBSERVED` foi mantido para compatibilidade, mas agora pode carregar:

- `reason_code`
- `perception_domain`
- `details`

Exemplos genericos:

- `OBSERVER_CAPABILITY_MISSING`
- `ENTITY_SELECTION_EMPTY`
- `ATTRIBUTE_VALUE_NOT_OBSERVED`
- `NO_ENTITY_OVERLAPS_CONTRACT_ATTRIBUTES`

## Runtime Doctor

Foram adicionados dominios diagnosticos:

- `contract_observation`
- `entity_selection`
- `observation_planning`
- `observer_capability`
- `attribute_observation`
- `coverage_analysis`

Assim o Doctor consegue diferenciar schema incompleto de incapacidade de observacao.

## Arquivos Alterados

- `src/aipinho/schemas/artifacts/contract_perception.py`
- `src/aipinho/schemas/artifacts/artifact_semantic_profile.py`
- `src/aipinho/schemas/artifacts/__init__.py`
- `src/aipinho/schemas/runtime/runtime_doctor.py`
- `src/aipinho/services/artifacts/contract_driven_perception_service.py`
- `src/aipinho/services/artifacts/artifact_semantic_contract_service.py`
- `src/aipinho/services/governance/runtime/readonly_analysis_artifact_runtime_service.py`
- `src/aipinho/services/runtime/runtime_doctor_service.py`
- `src/aipinho/services/runtime_doctor/runtime_doctor_service.py`
- `tests/unit/test_contract_driven_perception_service.py`
- `tests/unit/test_runtime_doctor_service.py`

## Validacao

- `python -m pytest tests/unit/test_contract_driven_perception_service.py tests/unit/test_observed_entity_compilation_service.py tests/unit/test_artifact_semantic_contract_service.py tests/unit/test_runtime_doctor_service.py -q`
  - 30 passed
- `python -m pytest tests/governance/test_g21_readonly_analysis_intent.py -q`
  - 15 passed
- `python -m pytest tests/governance/test_runtime_vertical_slice.py -q`
  - 11 passed
- `python -m pytest tests/unit/test_runtime_operator_ro.py -q`
  - 13 passed

Uma execucao combinada dos tres arquivos de governanca/operador excedeu o timeout de 240s, mas os mesmos arquivos passaram isoladamente.

## Veredito

A AIpinho agora nao apenas sabe que um atributo esta ausente. Ela consegue explicar se a ausencia veio de selecao de entidades, planejamento de observacao, capability de observer ou observacao de atributo. O proximo bloqueio esperado no FireTest deve ser mais rico e mais localizado, sem depender de regras especificas de dominio.
