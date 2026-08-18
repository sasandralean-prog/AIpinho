# FireTest 5 - H1B4 Runtime Activation, Backend Wiring & Evidence Recording

## Objetivo

Ativar a capability `media_metadata_reader` no Runtime real sem criar bypass, sem hardcode de FireTest, sem escrever direto no CSV e sem relaxar Validation, Completion ou Speaker Truth.

O objetivo desta wave foi remover a ambiguidade anterior:

```text
media_metadata_capability.status = not_configured
selected_backend = null
available_backends = []
evidence_records_created = 0
```

Depois da atualização, a capability passa a ser conhecida, executável pela `ObservationExecutionBoundary` e capaz de produzir `EvidenceRecord` quando algum backend sustenta evidência real.

## Estado Inicial

Último FireTest limpo pós-Semantic Maturity:

```text
Resultado: BLOCKED_AT_PHASE_1_WITH_CVL_MATCH
CVL previsto: evidence_recording
Runtime observado: observer_execution_or_backend
music_inventory.csv: 1051 linhas
project_like_rows: 0
Speaker Truth safe_to_report_success: false
media_metadata_reader: not_configured
```

Interpretação inicial:

```text
O Runtime já selecionava corretamente entidades do corpus.
O Runtime já derivava extensão genericamente.
O Runtime ainda não ativava media_metadata_reader no caminho real de percepção/evidência.
```

## Arquivos Alterados

- `C:\Dev\AIpinho\src\aipinho\schemas\artifacts\contract_perception.py`
- `C:\Dev\AIpinho\src\aipinho\capabilities\media_metadata\descriptor.py`
- `C:\Dev\AIpinho\src\aipinho\capabilities\media_metadata\normalizer.py`
- `C:\Dev\AIpinho\src\aipinho\capabilities\media_metadata\policy.py`
- `C:\Dev\AIpinho\src\aipinho\capabilities\media_metadata\backends\mutagen_backend.py`
- `C:\Dev\AIpinho\src\aipinho\services\artifacts\observation_execution_boundary_service.py`
- `C:\Dev\AIpinho\src\aipinho\services\artifacts\contract_driven_perception_service.py`
- `C:\Dev\AIpinho\src\aipinho\services\artifacts\observed_entity_compilation_service.py`
- `C:\Dev\AIpinho\src\aipinho\services\governance\runtime\readonly_analysis_artifact_runtime_service.py`
- `C:\Dev\AIpinho\src\aipinho\services\cvl\cognitive_validation_laboratory_service.py`
- `C:\Dev\AIpinho\tests\unit\test_media_metadata_capability_pack.py`
- `C:\Dev\AIpinho\tests\unit\test_contract_driven_perception_service.py`
- `C:\Dev\AIpinho\tests\unit\test_cognitive_validation_laboratory_service.py`

## Dependências Verificadas

Ambiente usado:

```text
Python: C:\Program Files\Python311\python.exe
```

Resultado:

```text
mutagen declarado no pyproject.toml: sim
mutagen importável no ambiente executado: não
ffprobe disponível no PATH: não
native_minimal disponível: sim
```

Reason codes usados:

```text
MUTAGEN_NOT_IMPORTABLE
FFPROBE_NOT_AVAILABLE
MEDIA_BACKEND_UNSUPPORTED_FORMAT
```

## Ativação Real

Antes:

```text
ContractDrivenPerception selecionava capability/strategy,
mas não executava ObservationTask real por entidade.
```

Depois:

```text
ObservationPlan
→ ObservationTask READY_FOR_OBSERVER
→ ObservationExecutionBoundaryService
→ MediaMetadataObserverAdapter
→ backend policy
→ native_minimal fallback
→ RawMediaMetadataResult
→ EvidenceRecord
→ EvidenceSet
→ SemanticCoverageReport
```

Leitores internos e cálculos determinísticos continuam no fluxo de percepção. A `ObservationExecutionBoundary` foi restringida a estratégias `execute_observer`, evitando concorrência com `observed_entity_attribute_reader` e `file_path_attribute_extractor`.

## Capability Registry

`media_metadata_reader` agora é registrada no `CapabilityRegistry` padrão junto com as capabilities genéricas:

```text
observed_entity_attribute_reader
file_path_attribute_extractor
media_metadata_reader
```

Contrato declarado:

```text
domain = media_metadata
produces = codec, container, bitrate, sample_rate, channels, duration, artwork, metadata, observations
consumes = audio_track_candidate, file_path
evidence_type = media_metadata_evidence
observer_binding.adapter_id = media_metadata_reader
```

## ObserverBinding

O binding real aponta para:

```text
media_metadata_reader
→ ObservationExecutionBoundaryService
→ MediaMetadataObserverAdapter
```

Preconditions preservadas:

```text
entity_role = audio_track_candidate
source_root_role in [library_root, corpus_root]
file_path present
file_exists
read_access
```

Entidades de corpus continuam semanticamente registradas como `corpus_file`. Para a execução observacional de metadata, a task carrega uma hipótese operacional `audio_track_candidate` quando o contrato exige metadata de mídia e a entidade vem de `library_root`/`corpus_root`. Essa hipótese não é truth; ela apenas autoriza uma tentativa governada.

## Backend Policy

Política efetiva:

```json
{
  "capability_id": "media_metadata_reader",
  "strategy": "primary_then_fallback",
  "primary": "mutagen",
  "fallbacks": ["ffprobe", "native_minimal"],
  "allow_partial_evidence": true,
  "min_confidence": 0.7,
  "fail_on_no_evidence": true,
  "record_backend_limitations": true
}
```

Status observado:

```text
mutagen: blocked / MUTAGEN_NOT_IMPORTABLE
ffprobe: blocked / FFPROBE_NOT_AVAILABLE
native_minimal: available, partial evidence
```

## Evidence Recording

Rerun diagnóstico service-equivalent:

```text
candidate_entity_count = 2272
selected_entity_count = 1051
selected_root_roles = [library_root]
project_like_selected_count = 0
observation_execution_result_count = 1051
evidence_records_created_by_media_metadata_reader = 1644
total_evidence_record_count = 4797
selected_backend = native_minimal
```

Canonical keys com evidência:

```text
name
extension
size_bytes
codec
container
sample_rate
```

Canonical keys ainda ausentes:

```text
bitrate
channels
duration
artwork
metadata
observations
```

Importante:

```text
Nenhum valor de metadata foi escrito diretamente no CSV.
Nenhum backend decide Validation.
Nenhum backend decide Completion.
Nenhum backend decide Speaker Truth.
```

## Semantic Coverage

Snapshot final:

```json
{
  "structural_coverage": 1.0,
  "entity_coverage": 1.0,
  "attribute_coverage": 0.5,
  "capability_coverage": 1.0,
  "evidence_coverage": 0.5,
  "semantic_confidence": 0.7,
  "is_semantically_complete": false,
  "blocking_reasons": ["MEDIA_BACKEND_UNSUPPORTED_FORMAT"]
}
```

Leitura:

```text
Capability existe e executa.
Entidades corretas foram selecionadas.
EvidenceRecord real existe para parte dos atributos.
Validation deve continuar bloqueando porque coverage/evidence ainda são insuficientes.
```

## Summary/API e Runtime Doctor

O renderer agora publica no payload de percepção:

```text
observation_execution_results
media_metadata_capability
```

O summary leve passa a ter dados suficientes para explicar a fronteira:

```json
{
  "media_metadata_capability": {
    "status": "partial",
    "capability_id": "media_metadata_reader",
    "selected_backend": "native_minimal",
    "available_backends": ["native_minimal"],
    "blocked_backends": ["ffprobe", "mutagen", "native_minimal"],
    "missing_dependency": ["ffprobe", "mutagen"],
    "evidence_records_created": 1644,
    "attributes_observed": ["codec", "container", "sample_rate"],
    "attributes_missing": ["bitrate", "channels", "duration", "artwork", "metadata", "observations"]
  }
}
```

## CVL

O CVL foi refinado para diferenciar fronteiras mais granulares:

```text
CAPABILITY_NOT_REGISTERED
BACKEND_NOT_CONFIGURED
DEPENDENCY_MISSING
OBSERVER_BINDING_MISSING
OBSERVER_EXECUTION_FAILED
EVIDENCE_RECORDING_FAILED
EVIDENCE_COVERAGE_INSUFFICIENT
SEMANTIC_VALIDATION_BLOCKED
```

Teste novo confirma que `backend_not_configured` é previsto antes de `evidence_recording` quando a capability existe, mas o backend está ausente/inoperante.

## Testes Criados/Atualizados

Novos/atualizados:

```text
media_metadata_reader aparece no Capability Registry padrão
mutagen ausente gera MUTAGEN_NOT_IMPORTABLE
adapter rejeita entidade inelegível com erro semântico tipado
renderer publica media_metadata_capability
CVL diferencia backend_not_configured de evidence_recording
path absoluto de entidade é resolvido por source_root + relative_path
```

Executados com sucesso:

```text
python -m pytest tests/unit/test_media_metadata_capability_pack.py tests/unit/test_contract_driven_perception_service.py tests/unit/test_cognitive_validation_laboratory_service.py -q
36 passed

python -m pytest tests/unit/test_runtime_doctor_service.py tests/unit/test_validation_gate_service.py tests/unit/test_speaker_service.py tests/unit/test_h1c1_conversation_runtime_truth.py -q
30 passed

python -m pytest tests/unit/test_artifact_runtime_service.py tests/unit/test_artifact_semantic_contract_service.py tests/unit/test_contract_compiler.py -q
23 passed

python -m pytest tests/governance/test_no_legacy_operational_bypass.py -q
2 passed
```

Execuções não concluídas:

```text
python -m pytest tests/unit -q
timeout após 10 minutos

python -m pytest tests/governance/test_g21_readonly_analysis_intent.py -q
timeout após 2 minutos
```

Finding não corrigido nesta wave:

```text
python -m pytest tests/governance/test_g23_capability_truth.py -q
1 failed, 1 passed

Falha:
test_plain_conversation_cannot_deny_governed_capabilities
Esperado: intent_type = capability_truth
Obtido: intent_type = permission_grant_request
```

Esse achado pertence à camada conversacional/capability truth, não à H1B4 observacional. Não foi corrigido aqui para evitar mistura de responsabilidades.

## Rerun Diagnóstico

Arquivo gerado:

```text
C:\Dev\AIpinho\reports\runtime_consolidation\firetest5_h1b4_runtime_activation_diagnostic.json
```

Resumo:

```text
project_root/library_root separados: sim
music_inventory selecionaria apenas library_root: sim
project_like_selected_count: 0
media_metadata_reader conhecida: sim
ObserverBinding real: sim
Backend selecionado: native_minimal
EvidenceRecord real para metadata: sim, parcial
Validation semanticamente completa: não
Speaker Truth deve continuar bloqueado: sim
```

## Antes / Depois

Antes:

```text
media_metadata_capability.status = not_configured
selected_backend = null
available_backends = []
missing_dependency = []
evidence_records_created = 0
```

Depois:

```text
media_metadata_capability.status = partial
selected_backend = native_minimal
available_backends = [native_minimal]
missing_dependency = [ffprobe, mutagen]
evidence_records_created = 1644
attributes_observed = [codec, container, sample_rate]
attributes_missing = [bitrate, channels, duration, artwork, metadata, observations]
```

## Gaps Restantes

1. `mutagen` está declarado, mas não está instalado/importável no ambiente Python usado.
2. `ffprobe` não está disponível no PATH.
3. `native_minimal` é propositalmente limitado; produz evidência parcial e bloqueia quando a assinatura não é suportada.
4. `bitrate`, `channels`, `duration`, `artwork`, `metadata` e `observations` ainda não possuem cobertura suficiente no diagnóstico real.
5. Sidecars como `.lrc` e artwork ainda exigem H1B5 para relação semântica própria.
6. Há finding separado em `test_g23_capability_truth.py` sobre meta-conversa/capability truth.

## Por Que Não Houve Bypass

- A capability não seleciona entidades por extensão.
- Entidades continuam vindo de H1B2.1 (`library_root`/`corpus_root`).
- O backend não escreve artifact.
- O renderer consome `AttributeObservation`/`EvidenceRecord`, não saída bruta do backend.
- Validation continua bloqueando quando evidence coverage é insuficiente.
- Completion continua dependente de Validation.
- Speaker Truth continua dependente de Timeline + Artifacts + Validation + Completion.

## Veredito

```text
FIRETEST5_H1B4_FRONTIER_EXPLAINED
```

A H1B4 ativou a capability real no caminho canônico e deslocou a fronteira:

```text
Antes:
media_metadata_reader invisível/not_configured

Agora:
media_metadata_reader conhecido
→ ObserverBinding real
→ native_minimal executa via boundary
→ EvidenceRecord parcial nasce
→ SemanticCoverageReport bloqueia por evidência incompleta
```

Isso não é `FIRETEST5_READY`, e não deve ser tratado como tal. É um avanço causal: a AIpinho agora sabe executar a capability de metadata quando possível e explicar por que ainda não pode declarar sucesso completo.

## Recomendação

Próximo passo canônico:

```text
H1B4.1 / Dependency Sync
```

Instalar/sincronizar a dependência declarada `mutagen` no ambiente oficial do runtime, usando o mecanismo de dependência do projeto, e rerodar a Fase 1 diagnóstica.

Depois:

```text
H1B5 - Sidecar / Artwork / Lyrics Relationship Model
```

Motivo: o corpus contém `.lrc`, `.jpg` e outros arquivos relacionados. Eles não devem ser tratados como faixas de áudio, mas podem virar evidência relacional para lyrics/artwork quando o contrato permitir.
