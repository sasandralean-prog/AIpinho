# FireTest 5 - H1B4.3 Public Evidence Propagation & Lightweight Runtime Summaries

## Veredito

`FIRETEST5_H1B4_3_PUBLIC_SUMMARY_BLOCK_EXPLAINED`

A H1B4.3 corrigiu a propagacao semantica no caminho governado/service-equivalent: evidencias de metadata agora chegam ao `ArtifactSemanticProfile`, viram observacoes vinculadas, aparecem no CSV materializado e deixam de ser reportadas falsamente como `ATTRIBUTE_NOT_OBSERVED`.

O caminho publico ainda nao pode ser declarado como completamente validado porque a execucao via `/api/v1/chat` excedeu o budget diagnostico de 900s e a run ficou sem `result.json` terminal. Os endpoints leves responderam depois do patch, mas a run publica usada para medicao ainda estava `RUNNING`, com apenas dois artifacts expostos no endpoint apesar de haver evento de criacao do `music_inventory.csv`.

## Objetivo

Corrigir o encanamento semantico publico:

```text
EvidenceRecord
-> AttributeObservation
-> ArtifactSemanticProfile
-> Renderer
-> ArtifactSemanticValidation
-> Completion
-> Speaker Truth
```

sem fazer backend escrever CSV, sem fazer renderer observar metadata, sem relaxar Validation, Completion ou Speaker Truth e sem introduzir hardcode de FireTest, caminho local, CSV ou dominio musical.

## Nao-goals Preservados

- Nao foi implementado H1B5.
- Nao foram criadas relacoes de sidecar.
- Nao foi recolocado `observations` no `media_metadata_reader`.
- Nao foi criado parser novo.
- Nao houve bypass de Validation, Completion ou Speaker Truth.
- Nao houve preenchimento direto de artifact por backend.

## Causa Raiz Encontrada

Havia duas falhas principais:

1. O `ArtifactSemanticContractService` recompilava o perfil a partir do artifact materializado e de `runtime_semantic_gaps`, mas nao consultava a evidencia/observacao ja vinculada ao artifact. Isso fazia a Validation publica continuar vendo `codec`, `container`, `bitrate`, `sample_rate`, `channels`, `duration`, `artwork` e `metadata` como ausentes mesmo quando `EvidenceRecord` existia.

2. O Runtime persistia payloads profundos inline em `run.json`, `result.json` e `events.json`. A sanitizacao anterior truncava strings, mas nao derramava listas/dicts grandes para referencias externas. Isso permitia arquivos de centenas de MB e timeouts nos endpoints publicos.

Tambem apareceu um terceiro finding publico:

3. A run publica diagnostica registrou evento de criacao do `music_inventory.csv`, mas o endpoint de artifacts retornou apenas dois artifacts. O arquivo existe no storage, mas nao ficou visivel de forma coerente pelo endpoint durante a run ainda `RUNNING`. Isso fica como gap de indexacao/lifecycle publico.

## Arquivos Alterados

- `src/aipinho/schemas/artifacts/artifact_semantic_profile.py`
- `src/aipinho/services/artifacts/artifact_semantic_contract_service.py`
- `src/aipinho/services/governance/runtime/readonly_analysis_artifact_runtime_service.py`
- `src/aipinho/services/runtime/task_run_store.py`
- `src/aipinho/services/runtime/universal_task_session_service.py`
- `src/aipinho/services/artifacts/universal_artifact_registry_service.py`
- `tests/unit/test_artifact_semantic_contract_service.py`
- `tests/unit/test_task_run_store.py`

## Mudancas Implementadas

### ArtifactSemanticProfile

`ArtifactSemanticProfile` recebeu campos leves para registrar o binding semantico:

```text
bound_attribute_observations
evidence_summary
```

Esses campos permitem que Validation e Runtime Doctor entendam quais atributos foram observados por `canonical_key`, sem depender do texto do CSV como fonte de verdade.

### ArtifactObservation Binding

O `readonly_analysis_artifact_runtime` agora compacta o contrato declarado antes de registrar o artifact e adiciona:

```text
artifact_observation_binding
bound_observed_canonical_keys
bound_counts_by_canonical_key
bound_evidence_refs_by_canonical_key
bound_observation_count
```

Esse binding e o ponto de encontro entre:

```text
Artifact Contract
ContractScopedEntitySet
EvidenceSet
AttributeObservation
Renderer
Validation
```

### Validation Semantica

`ArtifactSemanticContractService` agora suprime gaps `ATTRIBUTE_NOT_OBSERVED:<canonical_key>` quando existe observacao vinculada ao artifact para a mesma `canonical_key`.

Isso corrige o falso negativo sem transformar renderer, CSV ou summary em autoridade de verdade.

### Runtime Payload Spilling

`TaskRunStore` agora derrama payloads grandes para `payload_refs`, usando:

```text
content_ref
hash
size_bytes
record_count
reason_code = RUNTIME_PAYLOAD_SPILLED_TO_REF
```

Tambem foi adicionada coerencia terminal: se `result.status` e terminal, `run.status` e `finished_at` sao sincronizados.

### Summary Publico Leve

`UniversalTaskSessionService.summary()` passou a montar summary leve diretamente de `run`, `result`, `events` e `artifacts`, sem chamar o caminho completo de `get_session()`.

Tambem foi adicionada agregacao leve de `observational_cognition` a partir de `artifact_observation_binding`.

### Artifact Registry

`UniversalArtifactRegistryService.by_task()` agora filtra artifacts por task/run antes de montar registros publicos, evitando materializar todo o registry para entao filtrar.

## Resultado Service-Equivalent

Arquivo:

```text
reports/runtime_consolidation/firetest5_h1b4_3_evidence_propagation_trace.json
```

Resumo observado:

```text
selected_entity_count = 1051
csv_rows = 1051
csv_size_bytes = 682937
evidence_records.total = 11221
evidence_records.by_backend.mutagen = 8068
attribute_observations.total = 92
artifact_semantic_profile.bound_evidence_count = 62
artifact_semantic_profile.bound_attribute_count = 92
validation.status = blocked
false_missing_candidates = []
```

Celulas nao vazias por atributo:

```text
nome = 1051
extensao = 1051
tamanho = 1051
codec = 923
container = 928
bitrate = 918
sample_rate = 923
canais = 918
duracao = 918
artwork = 918
metadata = 918
observacoes = 0
```

Validation deixou de reportar metadata tecnica como falsa ausencia:

```text
missing_attributes_reported:
  ATTRIBUTE_NOT_OBSERVED:observations
```

Interpretacao:

```text
EvidenceRecord existe
-> AttributeObservation foi criado
-> ArtifactSemanticProfile recebeu binding
-> Renderer materializou valores observados
-> Validation viu o mesmo estado semantico
```

O bloqueio restante em `observations` e correto: `media_metadata_reader` nao e autoridade desse campo.

## Resultado Public Path

Execucao diagnostica:

```text
session_id = firetest5_h1b4_3_public_validation_20260812_033847
task_run_id = task_run_e0996a23a45b4ca6a86b1968cfc05a45
endpoint = /api/v1/chat
resultado = timeout_or_error
erro = O tempo limite da operacao foi atingido
```

Estado do store para a run:

```text
run.json = 75.637 bytes
events.json = 7.044 bytes
result.json = ausente
payload_refs = ausente
run.status = RUNNING
```

Eventos relevantes:

```text
artifact_created: reports/firetest5/phase1_discovery.md
artifact_created: reports/firetest5/project_inventory.md
artifact_created: reports/firetest5/music_inventory.csv
run_cancel_requested
```

Endpoint de artifacts retornou apenas:

```text
phase1_discovery.md
project_inventory.md
```

Finding:

```text
PUBLIC_ARTIFACT_INDEX_BINDING_GAP
```

O arquivo `music_inventory.csv` existe no storage, mas nao ficou visivel no endpoint da run publica enquanto a execucao permanecia sem `result.json` terminal.

## Endpoints Publicos Leves

Medicao pos-patch:

```text
summary   200 OK  17.385 ms  2.902 bytes
truth     200 OK  36.654 ms  1.831 bytes
events    200 OK     631 ms  5.802 bytes
artifacts 200 OK   4.277 ms 16.218 bytes
```

Arquivos:

```text
reports/runtime_consolidation/firetest5_h1b4_3_endpoint_timings_after_fast_summary.json
reports/runtime_consolidation/firetest5_h1b4_3_endpoint_summary_after.json
reports/runtime_consolidation/firetest5_h1b4_3_endpoint_truth_after.json
reports/runtime_consolidation/firetest5_h1b4_3_endpoint_events_after.json
reports/runtime_consolidation/firetest5_h1b4_3_endpoint_artifacts_after.json
```

Comparacao com H1B4.2:

```text
Antes:
  run.json = 333 MB
  events.json = 254 MB
  result.json = 564 MB

Depois, na run publica diagnostica ainda sem result terminal:
  run.json = 75 KB
  events.json = 7 KB
  summary response = 2.9 KB
```

O endpoint `truth` ainda e lento para um summary tao pequeno. Isso deve ser tratado como finding de performance residual, nao como falha de truth.

## Tratamento de Observations

`observations` nao foi produzido por `media_metadata_reader`.

Estado correto:

```text
observations = unresolved semantic authority
```

Proximas opcoes arquiteturais:

```text
artifact_diagnostic_note_producer
semantic_review_note
validation_observation_note
artifact_contract_optional_note
unresolved_required_attribute com gap explicito
```

Nao foi criada string vazia, "ok", comentario sintetico ou qualquer valor inventado.

## Testes Executados

```text
python -m pytest tests/unit/test_universal_task_session_service.py tests/unit/test_task_run_store.py tests/unit/test_artifact_semantic_contract_service.py -q
Resultado: 26 passed
```

```text
python -m pytest tests/unit/test_contract_driven_perception_service.py tests/unit/test_media_metadata_capability_pack.py -q
Resultado: 30 passed, 1 skipped
```

```text
python -m pytest tests/unit/test_artifact_runtime_service.py tests/unit/test_runtime_doctor_service.py tests/unit/test_validation_gate_service.py tests/unit/test_speaker_service.py -q
Resultado: 32 passed
```

Total confirmado nesta rodada:

```text
88 passed
1 skipped
```

Teste/finding de timeout:

```text
tests/unit/test_public_runtime_api_ex3.py
Resultado: timeout em execucao isolada/anterior
Classificacao: PUBLIC_RUNTIME_TEST_PERFORMANCE_GAP
```

## Gaps Restantes

```text
PUBLIC_CHAT_LONG_RUNNING_PHASE1
PUBLIC_ARTIFACT_INDEX_BINDING_GAP
PUBLIC_RUN_NOT_TERMINAL_AFTER_CLIENT_TIMEOUT
PUBLIC_CANCEL_RESPONSIVENESS_GAP
TRUTH_ENDPOINT_LATENCY_GAP
OBSERVATIONS_AUTHORITY_MISSING
CSV_METADATA_FIELD_SIZE_FINDING
```

O `CSV_METADATA_FIELD_SIZE_FINDING` apareceu porque o CSV com metadata observada possui celulas grandes o suficiente para exigir aumento de `csv.field_size_limit` no diagnostico. Isso nao invalida a evidencia, mas sugere que metadata estruturada precisa de estrategia de rendering resumida/paginada antes de um FireTest final.

## Por Que Nao Houve Bypass

- Backend continua retornando evidencia, nao artifact.
- Renderer continua materializando valores vindos de observacoes vinculadas, nao chamando backend.
- Validation continua decidindo completude sem ler diretamente backend ou CSV como verdade.
- Completion e Speaker Truth continuam dependentes de Validation.
- `observations` continua bloqueado porque nao existe autoridade semantica definida.
- Nenhuma regra foi adicionada para FireTest, caminho local, nome de CSV ou extensao especifica.

## Recomendacao

Antes de H1B5, executar uma H1B4.3.1 curta:

```text
Governed Phase1 Runtime Budgets & Artifact Index Finalization
```

Objetivos:

```text
1. Fazer a Fase 1 publica concluir em estado terminal governado.
2. Garantir que artifact_created sempre resulte em artifact visivel por task_run_id.
3. Tornar cancelamento cooperativo e responsivo durante geracao longa.
4. Reduzir/estruturar rendering de metadata volumosa no CSV.
5. Fazer summary/truth/artifacts refletirem o mesmo artifact set terminal.
```

Depois disso, a proxima fronteira natural permanece H1B5:

```text
Sidecar / Artwork / Lyrics Relationship Model minimo
```

## Conclusao

A H1B4.3 avancou a fronteira certa.

No caminho governado, a AIpinho agora consegue fazer a metadata real atravessar:

```text
EvidenceRecord
-> AttributeObservation
-> ArtifactSemanticProfile
-> Renderer
-> Validation
```

O falso `ATTRIBUTE_NOT_OBSERVED` para metadata observada desapareceu.

O caminho publico ainda nao esta pronto para declarar `FIRETEST5_READY`, porque a execucao longa nao chegou a um resultado terminal e a indexacao de artifacts ficou incoerente para o `music_inventory.csv`.

Veredito honesto:

```text
Public semantic propagation: PASS no service-equivalent
Public lightweight summary: PARTIAL PASS
Public full /api/v1/chat validation: BLOCKED por runtime/lifecycle/artifact index
Speaker Truth: seguro
Validation: preservada
```
