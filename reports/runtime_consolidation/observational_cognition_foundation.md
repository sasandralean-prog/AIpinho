# AIpinho - Observational Cognition Foundation

Data: 2026-08-10

## Objetivo

Esta wave implementa a fundacao generica de Observational Cognition para representar de forma causal por que um artifact ainda nao pode ser considerado semanticamente completo quando faltam capabilities observacionais.

Ela nao implementa observer especifico de audio, midia, musica, CSV ou FireTest.

## Filosofia preservada

- Sem bypass de Runtime, Validation, Completion ou Speaker Truth.
- Sem hardcode por dominio, extensao, artifact, workspace, fase ou prompt.
- Sem regra especifica para FireTest 5.
- Sem MediaMetadataObserver nesta wave.
- Renderer continua renderizando; nao decide verdade.
- Validation continua bloqueando semantic gaps.
- Completion continua dependente de Validation.
- Speaker Truth continua impedido de declarar READY sem evidencia.

## Fluxo canonico fortalecido

```text
Contract
↓
Required Attributes
↓
ObservationGoal
↓
ObservationStrategy
↓
Capability Registry v2
↓
Capability Matching
↓
Capability Arbitration
↓
ObservationTask
↓
Observer Execution futuro
↓
Evidence Model
↓
Evidence Confidence
↓
SemanticCoverageReport
↓
Artifact Semantic Validation
↓
Completion
↓
Speaker Truth
```

## IRs adicionadas ou enriquecidas

| IR | Responsabilidade |
| --- | --- |
| `ObservationGoal` | Representa o que precisa ser observado a partir de contrato, entidade e atributo. |
| `ObservationStrategy` | Representa uma rota possivel de observacao; nao executa nada. |
| `ObservationCapability` | Capability declarativa v2 com produces, consumes, entity types, evidence types, profiles, risk e binding futuro. |
| `CapabilityMatch` | Resultado auditavel do matching entre goal/strategy/capability. |
| `CapabilityArbitrationDecision` | Alias canonico de decisao de arbitragem, mantendo compatibilidade com `CapabilityDecision`. |
| `ObservationTask` | Unidade observacional futura, planejada ou bloqueada, sem executar observer nesta wave. |
| `EvidenceRecord` | Evidencia generica, auditavel, com provenance/confidence. |
| `EvidenceSet` | Colecao governada de evidencias observacionais. |
| `SemanticCoverageReport` | Report explicito de structural/entity/attribute/capability/evidence coverage. |

## Como NO_MATCHING_CAPABILITY fica representado agora

Quando um contrato exige um atributo sem capability compativel:

```text
ObservationGoal criado
ObservationStrategy criada
CapabilityMatch ausente
CapabilityDecision.status = no_matching_capability
CapabilityDecision.decision_status = BLOCKED_NO_CAPABILITY
ObservationTask.status = BLOCKED_NO_CAPABILITY
AttributeObservation.observation_state = unsupported
EvidenceSet nao contem evidencia para o atributo
SemanticCoverageReport.missing_capabilities contem o atributo
SemanticCoverageReport.is_semantically_complete = false
ArtifactSemanticProfile recebe semantic gap
Validation bloqueia
Completion bloqueia
Speaker Truth nao declara READY
```

## Por que nao criar MediaMetadataObserver agora

Criar um observer especifico neste ponto resolveria sintomas do FireTest 5, mas poderia reacoplar a arquitetura ao dominio de musica/audio. A wave atual separa infraestrutura de observacao de observers concretos. Depois desta fundacao, observers reais devem ser plugados como capabilities declarativas, cada uma publicando:

- quais atributos produz;
- quais entradas consome;
- quais entidades suporta;
- quais evidencias retorna;
- precondicoes;
- custo;
- latencia;
- confianca;
- risco;
- binding de execucao.

## Arquivos principais alterados

- `src/aipinho/schemas/artifacts/contract_perception.py`
- `src/aipinho/services/artifacts/contract_driven_perception_service.py`
- `src/aipinho/services/governance/runtime/readonly_analysis_artifact_runtime_service.py`
- `src/aipinho/schemas/artifacts/__init__.py`
- `tests/unit/test_contract_driven_perception_service.py`
- `tests/unit/test_artifact_semantic_contract_service.py`

## Testes executados

```text
python -m pytest tests/unit/test_contract_driven_perception_service.py -q
python -m pytest tests/unit/test_artifact_semantic_contract_service.py -q
python -m pytest tests/unit/test_runtime_doctor_service.py -q
python -m pytest tests/governance/test_lifecycle_core.py tests/unit/test_validation_gate_service.py tests/unit/test_workflow_truth_runtime.py -q
python -m pytest tests/unit/test_cognitive_validation_laboratory_service.py tests/unit/test_observed_entity_compilation_service.py -q
```

Todos passaram.

## Proximo passo recomendado

A proxima wave deve evoluir observers concretos como plugins/capabilities, nao como logica central do Runtime. Antes de qualquer observer de dominio, e recomendavel consolidar:

- policy cognitiva de arbitragem quando multiplas capabilities empatarem;
- catalogo declarativo externo para capabilities observacionais;
- endpoint/doctor summary leve para `SemanticCoverageReport`;
- execution boundary para `ObservationTask`.

