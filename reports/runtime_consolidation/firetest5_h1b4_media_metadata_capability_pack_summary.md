# FireTest 5 - H1B4 Media Metadata Capability Pack

## Resultado

Status da wave: `READY_WITH_FINDINGS`.

A H1B4 foi implementada como um pacote plugavel de capability observacional:

```text
media_metadata_reader
-> backend policy
-> backend plugavel
-> RawMediaMetadataResult
-> MediaMetadataNormalizer
-> EvidenceRecord
-> EvidenceSet
-> ObservationExecutionBoundary
-> SemanticCoverage/Validation/Speaker Truth
```

O objetivo nao foi fazer o FireTest passar por atalho. A mudanca cria uma capability real da AIpinho para metadata de midia, mantendo backends como mecanismos substituiveis e preservando EvidenceRecord como ponte para truth.

## Decisao de Dependencia

`mutagen>=1.47,<2` foi adicionado como dependencia versionada em `pyproject.toml`.

Motivo:

- biblioteca Python madura para leitura de metadata de audio;
- nao depende de CLI no PATH;
- funciona como backend primario plugavel;
- nao altera contrato semantico da AIpinho.

Observacao operacional: o ambiente atual ainda nao tinha `mutagen` importavel durante os testes. O backend trata isso como `MEDIA_BACKEND_NOT_AVAILABLE` e nao produz evidencia falsa.

## Arquivos Criados

- `src/aipinho/capabilities/media_metadata/__init__.py`
- `src/aipinho/capabilities/media_metadata/descriptor.py`
- `src/aipinho/capabilities/media_metadata/adapter.py`
- `src/aipinho/capabilities/media_metadata/normalizer.py`
- `src/aipinho/capabilities/media_metadata/evidence.py`
- `src/aipinho/capabilities/media_metadata/policy.py`
- `src/aipinho/capabilities/media_metadata/backends/__init__.py`
- `src/aipinho/capabilities/media_metadata/backends/mutagen_backend.py`
- `src/aipinho/capabilities/media_metadata/backends/ffprobe_backend.py`
- `src/aipinho/capabilities/media_metadata/backends/native_minimal_backend.py`
- `tests/unit/test_media_metadata_capability_pack.py`

## Arquivos Alterados

- `pyproject.toml`
- `src/aipinho/schemas/artifacts/contract_perception.py`
- `src/aipinho/services/artifacts/observation_execution_boundary_service.py`
- `src/aipinho/services/runtime/runtime_doctor_service.py`
- `src/aipinho/services/runtime_doctor/runtime_doctor_service.py`
- `src/aipinho/services/runtime/universal_task_session_service.py`

## IRs / Contratos Adicionados

- `MediaMetadataCapabilityDescriptor`
- `MediaMetadataBackendDescriptor`
- `MediaMetadataBackendPolicy`
- `RawMediaMetadataResult`
- `RawMediaMetadataField`
- `MediaMetadataObservationResult`
- `MediaMetadataBackendError`
- `MediaMetadataBackendLimitations`

`EvidenceRecord` foi enriquecido com `backend_id`, para preservar provenance quando varios mecanismos observacionais forem comparados futuramente.

## Capability Canonica

Capability:

```text
capability_id = media_metadata_reader
```

Produz:

```text
codec
container
bitrate
sample_rate
channels
duration
artwork
metadata
```

Consome:

```text
audio_track_candidate
file_path
```

Preconditions declaradas:

```text
entity_role = audio_track_candidate
source_root_role in [library_root, corpus_root]
file_path present
file_exists
read_access
```

A capability rejeita entidades inelegiveis por `entity_role` e `source_root_role`. Ela nao usa FireTest, caminho local, CSV ou extensao como regra de selecao.

## Backends Implementados

### Mutagen Backend

Backend primario declarativo:

```text
backend_id = mutagen
```

Comportamento:

- se `mutagen` estiver disponivel, tenta ler metadata e retorna `RawMediaMetadataResult`;
- se nao estiver, retorna erro tipado `MEDIA_BACKEND_NOT_AVAILABLE`;
- nao cria `EvidenceRecord`;
- nao escreve CSV;
- nao acessa Validation, Completion ou Speaker Truth;
- nao derruba a run inteira por erro de arquivo.

### FFprobe Backend

Backend opcional:

```text
backend_id = ffprobe
```

Comportamento:

- detecta ausencia da CLI com `FFPROBE_NOT_AVAILABLE`;
- executa com timeout;
- usa JSON quando disponivel;
- retorna erros tipados para timeout, JSON invalido e runtime error;
- nao e dependencia obrigatoria do FireTest.

### Native Minimal Backend

Fallback evolutivo:

```text
backend_id = native_minimal
```

Escopo intencionalmente limitado:

- MP4/M4A: detecta `ftyp`, tenta `stsd`, `mvhd`/`mdhd` simples;
- MP3: detecta ID3/MPEG frame basico, bitrate/sample rate/channels do primeiro frame quando seguro;
- nunca tenta artwork/editorial metadata complexo;
- nunca decodifica audio;
- nunca inventa codec/duration quando nao ha evidencia suficiente.

Importante: extensoes suportadas nos descriptors sao descritivas, nao filtros magicos de entidade.

## Backend Policy

Policy default:

```text
strategy = primary_then_fallback
primary = mutagen
fallbacks = [ffprobe, native_minimal]
allow_partial_evidence = true
min_confidence = 0.7
fail_on_no_evidence = true
record_backend_limitations = true
```

A policy pode aceitar evidencia parcial, mas apenas campos com valor sustentado e confidence suficiente viram `EvidenceRecord`.

## Fluxo de Evidencia

O fluxo implementado e:

```text
backend
-> RawMediaMetadataResult
-> MediaMetadataNormalizer
-> EvidenceRecord
-> EvidenceSet
-> ObservationExecutionBoundaryService
```

O backend nunca escreve artifact e nunca decide truth.

`MediaMetadataNormalizer`:

- normaliza canonical keys;
- normaliza unidades;
- preserva `backend_id`;
- preserva `raw_ref`;
- preserva confidence por campo;
- preserva limitations;
- descarta campos sem sustentacao ou abaixo da confidence minima.

## Runtime Doctor / Summary

O Runtime Doctor passou a classificar novos reason codes como `observer_execution`:

- `MEDIA_BACKEND_NOT_AVAILABLE`
- `MEDIA_BACKEND_UNSUPPORTED_FORMAT`
- `MEDIA_BACKEND_NO_EVIDENCE`
- `MEDIA_BACKEND_PARTIAL_EVIDENCE`
- `MEDIA_BACKEND_CONTRADICTION`
- `MEDIA_BACKEND_LOW_CONFIDENCE`
- `MEDIA_BACKEND_RUNTIME_ERROR`
- `FFPROBE_NOT_AVAILABLE`
- `FFPROBE_TIMEOUT`
- `FFPROBE_INVALID_JSON`
- `FFPROBE_RUNTIME_ERROR`

O summary endpoint agora possui consolidacao leve para `media_metadata_capability` dentro de `observational_cognition`, quando essa informacao existir nos artifacts/contratos da run. Quando nenhuma execucao de media metadata ocorreu, o status permanece `not_configured`; nada e inventado.

## Testes Criados

Arquivo:

```text
tests/unit/test_media_metadata_capability_pack.py
```

Cobertura:

- descriptor da capability;
- descriptors dos backends;
- Mutagen ausente como erro tipado;
- FFprobe ausente como erro tipado;
- NativeMinimal MP4/M4A basico;
- NativeMinimal MP3 basico;
- NativeMinimal nao inventa codec/duration;
- normalizer gera evidencia apenas para campos suportados/confiaveis;
- adapter rejeita entidade inelegivel via boundary;
- boundary executa `media_metadata_reader` e retorna EvidenceRecord;
- summary leve agrega `media_metadata_capability`.

## Testes Executados

Passou:

```text
python -m pytest tests/unit/test_media_metadata_capability_pack.py tests/unit/test_observation_execution_boundary_service.py -q

17 passed in 0.52s
```

Verificacao ampla inconclusiva por timeout:

```text
python -m pytest tests/unit tests/governance -q
timeout apos 304s

python -m pytest tests/governance -q
timeout apos 184s
```

Nao houve evidencia de falha nesses comandos; apenas ausencia de conclusao dentro da janela operacional.

## Antes / Depois

Antes:

```text
ObservationTask
-> capability ausente
-> NO_MATCHING_CAPABILITY / OBSERVER_CAPABILITY_MISSING
```

Depois:

```text
ObservationTask
-> media_metadata_reader
-> ObserverBinding
-> ObservationExecutionBoundary
-> backend policy
-> RawMediaMetadataResult
-> EvidenceRecord ou erro tipado
```

Isso move a fronteira de "nao ha capability" para "capability existe, backend/evidencia determinam se ha cobertura suficiente".

## Gaps Restantes

- O ambiente precisa instalar/sincronizar `mutagen` para validar backend primario real.
- O fallback nativo ainda e propositalmente minimo.
- A H1B5 ainda precisa modelar sidecars/artwork/lyrics sem confundir entidades.
- A H1B6 ainda precisa comparar CVL vs runtime real apos execucao completa.
- Evidence Fusion entre backends foi preparado conceitualmente, mas nao implementado como arbitragem avancada.

## Por Que Nao Houve Bypass

- Nenhum backend escreve CSV.
- Nenhum backend decide Validation.
- Nenhum backend decide Completion.
- Nenhum backend decide Speaker Truth.
- Nenhum valor vira contrato satisfeito sem `EvidenceRecord`.
- A capability aceita apenas entidades ja classificadas como elegiveis por H1B2.1.
- Metadata nao e inferida por nome/extensao.
- FireTest, paths locais e artifact names nao aparecem como regra de decisao.

## Veredito

`READY_WITH_FINDINGS`

A AIpinho agora tem o esqueleto real da capability `media_metadata_reader`: declarativa, plugavel, executavel pela boundary e capaz de emitir evidencia. O proximo passo correto e validar a dependencia primarial real (`mutagen`) no ambiente e, depois, fazer rerun diagnostico para confirmar que metadata so entra no artifact via EvidenceRecord/SemanticCoverage.
