# FireTest 5 H1B1 - Attribute Identity & Evidence Semantics Summary

## Objetivo da Wave

Esta wave amadureceu a fundacao generica de Observational Cognition exposta pelo rerun do FireTest 5. O objetivo nao foi criar um observer de audio nem fazer o FireTest passar por atalho. O objetivo foi tornar a cadeia `Contract -> ObservationGoal -> CapabilityMatch -> EvidenceRecord -> SemanticCoverageReport -> Validation -> Completion -> Speaker Truth` mais causal, auditavel e reutilizavel.

## Regras preservadas

- Nenhum `MediaMetadataObserver` foi criado.
- Nenhum observer especifico de musica, audio, CSV ou FireTest foi criado.
- Nenhum bypass de Runtime, Policy, Validation, Completion ou Speaker Truth foi introduzido.
- Validation continua bloqueando semantic gaps sem evidencia suficiente.
- Speaker Truth continua impedido de declarar READY sem suporte de Timeline, Artifacts, Validation e Completion.
- Matching permanece derivado de contrato, atributo canonico, entity kind, strategy e capability descriptors.

## Arquivos alterados

- `src/aipinho/schemas/artifacts/contract_perception.py`
- `src/aipinho/schemas/artifacts/artifact_semantic_profile.py`
- `src/aipinho/schemas/artifacts/__init__.py`
- `src/aipinho/services/artifacts/observed_entity_compilation_service.py`
- `src/aipinho/services/artifacts/contract_driven_perception_service.py`
- `src/aipinho/services/artifacts/artifact_semantic_contract_service.py`
- `src/aipinho/services/governance/runtime/readonly_analysis_artifact_runtime_service.py`
- `src/aipinho/schemas/runtime/universal_task_session.py`
- `src/aipinho/services/runtime/universal_task_session_service.py`
- `tests/unit/test_contract_driven_perception_service.py`
- `tests/unit/test_artifact_semantic_contract_service.py`
- `tests/unit/test_universal_task_session_service.py`

## IRs adicionadas ou enriquecidas

### AttributeDescriptor / AttributeIdentity / ArtifactAttributeContract

Foi introduzida uma identidade canonica de atributo para separar label humano de chave operacional.

Campos principais:

- `canonical_key`
- `display_label`
- `raw_label`
- `locale`
- `semantic_type`
- `value_type`
- `requiredness`
- `nullable`
- `evidence_required`
- `coverage_threshold`
- `aliases`
- `normalization_notes`

### ObservationGoal

Passa a carregar `canonical_key`, labels, contrato de atributo, artifact binding e unbound reason quando aplicavel.

### ObservationStrategy

Passa a separar:

- `required_preconditions`
- `satisfied_preconditions`
- `missing_preconditions`

### CapabilityMatch

Agora aceita `capability_id = null` para match negativo auditavel e carrega trace IDs, `canonical_key`, preconditions e blocking reason.

### ObservationTask

Passa a propagar `contract_id`, `artifact_logical_path`, `artifact_kind`, `task_run_id` e `canonical_key`.

### EvidenceRecord / EvidenceSet

`EvidenceRecord` passa a carregar `canonical_key`. `EvidenceSet` passa a resumir `canonical_keys` observadas alem de nomes de atributos.

### SemanticCoverageReport

Passa a carregar binding de artifact/contract/task e diferencia cobertura estrutural, entidade, atributo, capability e evidencia.

### ArtifactSemanticProfile

Passa a ser enderecavel por:

- `artifact_id`
- `artifact_logical_path`
- `artifact_kind`
- `task_run_id`

Tambem preserva `canonical_schema` e `attribute_contracts`.

## Como AttributeIdentity funciona

A normalizacao agora ocorre em camada generica:

1. Preserva `raw_label` exatamente como recebido.
2. Mantem `display_label` para renderizacao humana.
3. Gera `canonical_key` ASCII/snake_case para matching, validation e coverage.
4. Usa aliases configurados e comparacao compacta conservadora para tolerar labels degradados por encoding.
5. Registra `normalization_notes` para auditoria.

Exemplo esperado:

```json
{
  "canonical_key": "extension",
  "display_label": "extens?o",
  "raw_label": "extens?o",
  "normalization_notes": [
    "lossy_or_replacement_character_present",
    "matched_near_alias:extension"
  ]
}
```

Importante: o Runtime nao recupera acento inventando texto. Ele apenas impede que mojibake vire chave operacional.

## CapabilityMatch negativo auditavel

Antes, quando nenhuma capability existia, a lista de matches podia ficar vazia. Isso deixava ambigua a diferenca entre "matching nao tentou" e "matching tentou e nao encontrou".

Agora toda tentativa sem capability gera `CapabilityMatch` negativo:

```json
{
  "match_status": "NO_MATCHING_CAPABILITY",
  "capability_id": null,
  "match_score": 0.0,
  "coverage_score": 0.0,
  "confidence_score": 0.0,
  "blocking_reason": "NO_MATCHING_CAPABILITY"
}
```

Semantic gaps passam a referenciar esses `capability_match_ids`, mantendo causalidade auditavel.

## Precondition semantics

Foi corrigida a inconsistencia em que um match podia aparecer como `MATCHED` mesmo contendo `missing_preconditions`.

Nova regra:

- `MATCHED` exige `missing_preconditions = []`.
- Preconditions realmente ausentes produzem `PRECONDITION_FAILED` ou bloqueio de arbitragem.
- `required_preconditions`, `satisfied_preconditions` e `missing_preconditions` ficam separados.
- Para `read_existing_attribute`, quando o atributo esta no EntityEvidenceGraph, `attribute_present_in_entity_graph` aparece como satisfeita.

## EvidenceRecord e EvidenceSet

A wave reconciliou o caso em que o CSV tinha atributos preenchidos, mas `EvidenceRecord` aparecia ausente.

Agora atributos ja presentes no `ObservedEntityGraph` geram evidencia real:

```json
{
  "source": "observed_entity_graph",
  "acquisition_method": "read_existing_attribute",
  "capability_id": "observed_entity_attribute_reader",
  "canonical_key": "name",
  "provenance": {"source": "observed_entity_graph"}
}
```

`evidence_coverage` passa a depender de `EvidenceRecord/EvidenceSet` real, nao apenas de `CapabilityDecision`.

## Generic file attribute capability

Foi adicionada capability generica declarativa:

`file_path_attribute_extractor`

Ela pode produzir apenas atributos de path/arquivo:

- `extension`
- `basename`
- `stem`
- `parent_path`
- `file_name`

Ela nao observa e nao infere:

- codec
- container
- bitrate
- sample_rate
- channels/canais
- duration/duracao
- artwork
- metadata de midia

Essa capability e generica de filesystem/path, nao de audio.

## Required vs optional attributes

A percepcao agora diferencia `required`, `optional`, `nullable`, `computed`, `derived` e `best_effort` por contrato de atributo.

Validation continua rigorosa para atributos obrigatorios com evidencia requerida. Atributos opcionais/nullable podem continuar rastreados sem bloquear semantic completeness, desde que o contrato os declare assim.

Nenhuma decisao e feita por nome de campo.

## ArtifactSemanticProfile binding

`ArtifactSemanticProfile` agora preserva `artifact_logical_path`, `artifact_kind`, `task_run_id`, `canonical_schema` e `attribute_contracts`.

A validacao tambem separa:

- profile ausente;
- profile existente, mas semanticamente bloqueado.

Assim `artifact_semantic_profile:<logical_path>` nao e marcado como missing quando o profile existe e apenas contem gaps semanticos.

## Runtime summary endpoint

O schema publico agora aceita `BLOCKED` como status top-level.

Regra corrigida:

Se `result.status = blocked`, `validation.status = blocked` e approval nao e requerido, o top-level status nao deve ser `WAITING_USER`.

O summary tambem passou a expor secao leve:

```json
{
  "observational_cognition": {
    "status": "blocked",
    "blocking_reason": "NO_MATCHING_CAPABILITY",
    "semantic_coverage": {
      "structural": 1.0,
      "entity": 1.0,
      "attribute": 0.5,
      "capability": 0.5,
      "evidence": 0.5
    },
    "missing_capabilities": ["codec"],
    "missing_attributes": ["codec"],
    "observation_goals": {
      "total": 1,
      "blocked": 1,
      "ready": 0
    }
  }
}
```

A UI/API nao precisa mais parsear artifact IDs brutos para entender o bloqueio observacional.

## Antes / depois dos gaps

Antes:

```text
ATTRIBUTE_NOT_OBSERVED
capability_match_ids = []
EvidenceRecord = 0 mesmo com atributos preenchidos
status publico = WAITING_USER
```

Depois:

```text
ATTRIBUTE_NOT_OBSERVED
reason_code = NO_MATCHING_CAPABILITY
capability_match_ids aponta para CapabilityMatch negativo
EvidenceRecord existe para atributos observados/derivados
status publico = BLOCKED quando nao ha approval pendente
```

## Gaps que ainda devem permanecer no FireTest 5

Sem observer real de metadata de midia, estes atributos devem continuar bloqueando se forem obrigatorios no contrato:

- codec
- container
- bitrate
- sample_rate
- channels/canais
- duration/duracao
- artwork
- metadata

`extension` pode deixar de bloquear quando houver path/name suficiente, porque e atributo generico de arquivo, nao metadata de audio.

## Por que MediaMetadataObserver nao foi criado

Criar um observer de midia agora poderia fazer o FireTest 5 avancar, mas seria uma solucao de dominio. Esta wave precisava fortalecer a infraestrutura que explica por que falta capability, nao fornecer a capability concreta.

O proximo passo correto e plugar observers concretos futuramente como capabilities declarativas, apos a boundary de execucao observacional estar suficientemente clara.

## Testes executados

Comando focado:

```bash
python -m pytest tests/unit/test_contract_driven_perception_service.py tests/unit/test_artifact_semantic_contract_service.py tests/unit/test_universal_task_session_service.py -q
```

Resultado:

```text
26 passed in 4.10s
```

Compilacao dos arquivos alterados:

```bash
python -m py_compile src/aipinho/schemas/artifacts/contract_perception.py src/aipinho/schemas/artifacts/artifact_semantic_profile.py src/aipinho/services/artifacts/observed_entity_compilation_service.py src/aipinho/services/artifacts/contract_driven_perception_service.py src/aipinho/services/artifacts/artifact_semantic_contract_service.py src/aipinho/services/governance/runtime/readonly_analysis_artifact_runtime_service.py src/aipinho/schemas/runtime/universal_task_session.py src/aipinho/services/runtime/universal_task_session_service.py
```

Resultado: PASS.

## Testes amplos e riscos residuais

`python -m pytest tests/unit -q` excedeu o timeout de 4 minutos. Em modo diagnostico, a primeira falha foi:

```text
tests/unit/test_agent_delegation_service.py::test_delegation_request_result_parent_child_and_timeline
PermissionError: agent_profile_disabled
```

Esse bloqueio ocorre em fixture/configuracao de agent profile e nao foi tocado por esta wave.

`python -m pytest tests/governance -q` excedeu o timeout de 3 minutos. Em modo diagnostico, a primeira falha foi:

```text
tests/governance/test_g16_legacy_chat_services_folded.py::test_chat_service_remains_content_provider_for_plain_conversation
Expected: conversation
Observed: workspace_analysis_readonly
```

Esse ponto pertence a fronteira de Semantic Intent / Public Chat, nao a Observational Cognition H1B1 desta wave.

## Veredito

READY_WITH_FINDINGS.

A wave consolidou a explicabilidade causal de atributo/capability/evidencia sem criar observer especifico, sem relaxar as autoridades finais e sem alterar o FireTest. O FireTest 5 provavelmente continuara bloqueando em metadata de midia ate existir uma capability observacional real, mas o bloqueio agora deve ser mais preciso, rastreavel e consumivel por Runtime Doctor/API/UI.
