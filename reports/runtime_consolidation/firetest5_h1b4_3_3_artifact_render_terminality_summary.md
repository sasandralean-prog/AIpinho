# FireTest 5 - H1B4.3.3 Artifact Render Cooperative Budgets & Terminal Event Idempotency

## Veredito

`FIRETEST5_H1B4_3_3_ARTIFACT_RENDER_TERMINALITY_READY_WITH_PUBLIC_CHAT_FINDING`

A wave corrigiu a fronteira principal observada na H1B4.3.2: artifact rendering agora checa budget, cancelamento e terminal state durante a renderizacao longa, antes de registry create e antes de emitir `artifact_created`.

O objetivo nao foi buscar `FIRETEST5_READY`.

## Escopo

Implementado:

- `ArtifactRenderBudget` generico, consolidado com `Phase1RuntimeBudget`.
- Checkpoints cooperativos em renderizacao tabular/CSV.
- Guarda explicita contra `artifact_created completed` depois de terminal event.
- Politica late artifact padrao: `reject`.
- Evento `artifact_late_rejected` com `ARTIFACT_RENDER_LATE_ARTIFACT_REJECTED`.
- Terminalizacao idempotente: primeiro terminal vence.
- Tentativas posteriores viram `terminalization_already_applied`.
- Artifacts `partial/interrupted/rejected` aparecem no endpoint por linhas do `result.outputs`, com `safe_to_use=false`.
- Summary de metadata deixa de reportar `media_metadata_capability.status=not_configured` quando ha bound observations de atributos de midia sem provenance inline suficiente.

Nao implementado:

- H1B5.
- Sidecars.
- Knowledge Graph/H1D.
- Parser novo.
- `accepted_running` amplo para `/api/v1/chat`.
- Metadata como Truth.
- Relaxamento de Validation, Completion ou Speaker Truth.

## Arquivos Alterados

- `src/aipinho/services/governance/runtime/readonly_analysis_artifact_runtime_service.py`
- `src/aipinho/services/runtime/task_run_store.py`
- `src/aipinho/services/runtime/universal_task_session_service.py`
- `config/runtime/task_run_event_policy.yaml`
- `tests/unit/test_readonly_analysis_phase1_budgets.py`
- `tests/unit/test_task_run_store.py`
- `tests/unit/test_universal_task_session_service.py`

## Causa Raiz

Antes, o runtime checava budget antes do artifact, mas a renderizacao longa do CSV nao tinha checkpoints internos suficientes. Se outro boundary terminalizasse a run, o renderer podia continuar ate `registry.create()` e depois emitir `artifact_created completed`.

Tambem havia dois caminhos emitindo terminal:

- catch de `GovernedPhase1Block`;
- fechamento final do `TaskRunResult`.

Isso permitia `run_blocked` repetido.

## Depois

Checkpoints implementados:

- `before_artifact_render`
- `before_entity_iteration`
- `after_entity_batch`
- `before_csv_cell_render`
- `after_csv_row_batch`
- `before_artifact_write`
- `before_registry_create`
- `after_registry_create_before_event`
- `before_validation`

Se a run ja tem terminal event, a tentativa de artifact vira:

```text
artifact_late_rejected
reason_code = ARTIFACT_RENDER_LATE_ARTIFACT_REJECTED
safe_to_use = false
```

`artifact_created completed` pos-terminal fica proibido no caminho do runtime readonly.

## ArtifactRenderBudget

Campos principais:

- `max_total_seconds`
- `max_artifact_seconds`
- `max_rows`
- `max_columns`
- `max_cells`
- `max_cell_bytes`
- `max_total_bytes`
- `max_metadata_inline_bytes`
- `cancel_poll_interval`
- `allow_partial_artifact`
- `late_artifact_policy = reject`

Variaveis suportadas:

- `AIPINHO_ARTIFACT_RENDER_MAX_SECONDS`
- `AIPINHO_ARTIFACT_RENDER_MAX_ARTIFACT_SECONDS`
- `AIPINHO_ARTIFACT_RENDER_MAX_ROWS`
- `AIPINHO_ARTIFACT_RENDER_MAX_COLUMNS`
- `AIPINHO_ARTIFACT_RENDER_MAX_CELLS`
- `AIPINHO_ARTIFACT_RENDER_MAX_CELL_BYTES`
- `AIPINHO_ARTIFACT_RENDER_MAX_TOTAL_BYTES`
- `AIPINHO_ARTIFACT_RENDER_CANCEL_POLL_INTERVAL`
- `AIPINHO_ARTIFACT_RENDER_ALLOW_PARTIAL`
- `AIPINHO_ARTIFACT_RENDER_LATE_POLICY`

## Endpoint de Artifacts

Artifacts parciais/interrompidos vindos de `result.outputs.artifact_result.artifacts` agora aparecem no endpoint, mesmo sem `artifact_id` de registry.

Estado agregado vira `partial` quando algum artifact tem:

```text
status in partial|interrupted|failed|rejected
safe_to_use = false
```

Validation continua bloqueada para artifacts nao-ready.

## Metadata Summary

Foi feita apenas auditoria/correcao local de summary.

Se existem bound observations para atributos como `codec`, `container`, `duration`, `metadata`, mas nao existe provenance inline suficiente da capability, o summary usa:

```text
media_metadata_capability.status = unknown_due_to_payload_ref
```

Isso evita `not_configured` silencioso sem promover metadata a Truth.

## Public Chat Boundary

`PUBLIC_CHAT_RESPONSE_BOUNDARY_STILL_SYNCHRONOUS` permanece como finding secundario.

Foi feita tentativa de rerun publico na porta `8095`. O cliente excedeu timeout em aproximadamente 70s. A chamada criou o TaskRun `task_run_c34f13ea90424209ae2742f7b30a9ee3`, mas o estado persistido ficou em `created`, com apenas eventos de bootstrap/planning, sem `run_started`, sem `result.json` e sem artifacts. O processo `uvicorn` foi encerrado.

Esse rerun nao e evidencia canonica da fronteira de artifact rendering. Ele confirma apenas que `/api/v1/chat` ainda precisa de boundary publico melhor para execucoes longas/penduradas antes da execucao real. Esta wave nao reestruturou `/api/v1/chat` para `accepted_running`, porque isso e fronteira propria.

## Testes

Executado:

```text
python -m pytest tests/unit/test_artifact_runtime_service.py tests/unit/test_project_analysis_public_boundary.py tests/unit/test_contract_driven_perception_service.py tests/unit/test_media_metadata_capability_pack.py tests/unit/test_artifact_semantic_contract_service.py tests/unit/test_runtime_doctor_service.py tests/unit/test_validation_gate_service.py tests/unit/test_speaker_service.py tests/unit/test_readonly_analysis_phase1_budgets.py tests/unit/test_task_run_store.py tests/unit/test_universal_task_session_service.py -q
```

Resultado:

```text
103 passed, 1 skipped
```

Compilacao dos arquivos alterados: PASS.

## Gaps Restantes

- Rerun publico canonico ainda deve ser executado em uma janela propria.
- `/api/v1/chat` ainda precisa de boundary `accepted_running` ou `timeout_blocked` se a mudanca for priorizada.
- Partial artifact persistido no registry nao foi ampliado; esta wave expõe partial/interrupted pelo result endpoint sem criar registry paralelo.
- Observations/Knowledge/H1D continuam fora do escopo.

## Preservacao de Autoridades

- Backend nao escreve artifact.
- Renderer nao chama backend.
- Validation nao foi relaxada.
- Completion nao foi relaxado.
- Speaker Truth continua dependente de evidence/validation.
- Metadata renderizada nao virou Truth.
- Nenhum hardcode de FireTest, `music_inventory.csv` ou caminho local foi introduzido como regra operacional.

## Recomendacao

Executar um FireTest 5 diagnostico forte H1B4.3.3 com processo publico novo e coleta dedicada de:

- `terminal_event_count`
- `post_terminal_events`
- `artifact_late_rejected_count`
- `artifact_created_count`
- `music_inventory_status`
- `summary.media_metadata_capability.status`
- `speaker_truth.safe_to_report_success`

Se o rerun confirmar ausencia de `artifact_created completed` pos-terminal e terminal unico, a proxima fronteira pode ser `/api/v1/chat accepted_running` ou entao a auditoria maior de capability/evidence provenance.
