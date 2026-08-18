# FireTest 5 - H1B4.3.1 Governed Phase1 Runtime Budgets & Artifact Index Finalization

## Veredito

`FIRETEST5_H1B4_3_1_RUNTIME_BUDGET_BLOCK_EXPLAINED`

A wave corrigiu partes centrais da fronteira operacional:

- adicionou budget governado configuravel para a Fase 1;
- adicionou checkpoints de budget/cancelamento no runtime readonly de artifacts;
- separou `artifact_creation_started` de `artifact_created`;
- adicionou indice leve por `task_run_id` no registry oficial de artifacts;
- adicionou spill/ref para celulas CSV volumosas;
- adicionou paginacao leve em eventos;
- adicionou supervisao de lifecycle para terminalizar runs presas acima do budget;
- preservou Validation, Completion e Speaker Truth.

A validacao publica confirmou que a run nao ficou zumbi: terminou `blocked`, com `finished_at` e `result.json`. Porem, a run publica bloqueou antes de criar artifacts, entao o indice publico de artifacts nao foi exercitado pelo rerun; foi validado por teste unitario e permanece pronto para a proxima execucao que consiga atravessar `project_analysis`.

## Escopo

Esta wave atacou runtime/lifecycle, nao metadata nem sidecars.

Fluxo-alvo:

```text
/api/v1/chat
-> Fase 1 publica
-> budget governado
-> terminalidade coerente
-> artifact index por task_run_id
-> endpoints leves
-> Speaker Truth preservado
```

## Nao-goals

- Nao foi implementado H1B5.
- Nao foram criadas relacoes de sidecar.
- Nao foi resolvido `observations` via `media_metadata_reader`.
- Nao foi criado parser novo.
- Nao foi aumentado timeout para chamar isso de sucesso.
- Nao foi relaxado Validation, Completion ou Speaker Truth.
- Nao foi criado registry paralelo.

## Arquivos Alterados

- `src/aipinho/services/artifacts/universal_artifact_registry_service.py`
- `src/aipinho/services/governance/runtime/readonly_analysis_artifact_runtime_service.py`
- `src/aipinho/services/runtime/task_run_store.py`
- `src/aipinho/services/runtime/universal_task_session_service.py`
- `tests/unit/test_artifact_runtime_service.py`
- `tests/unit/test_universal_task_session_service.py`
- `tests/unit/test_task_run_store.py`
- `tests/unit/test_readonly_analysis_phase1_budgets.py`

## Mudancas Implementadas

### Runtime Budgets

Foi introduzido `Phase1RuntimeBudget`, configuravel por ambiente:

```text
AIPINHO_PHASE1_MAX_RUNTIME_SECONDS
AIPINHO_PHASE1_MAX_ARTIFACT_RENDER_SECONDS
AIPINHO_PHASE1_MAX_CSV_CELL_BYTES
AIPINHO_PHASE1_MAX_CSV_TOTAL_BYTES
AIPINHO_PHASE1_CANCEL_POLL_INTERVAL
```

Reason codes implementados:

```text
PHASE1_RUNTIME_BUDGET_EXCEEDED
ARTIFACT_RENDER_BUDGET_EXCEEDED
CANCEL_CHECKPOINT_REACHED
CSV_FIELD_SPILLED_TO_REF
ARTIFACT_RENDER_BUDGET_EXCEEDED
TASKRUN_LIFECYCLE_TIMEOUT
```

### Cancelamento Cooperativo

O runtime readonly agora checa cancelamento/budget em pontos seguros:

```text
before_project_analysis
after_project_analysis
before_artifact:<logical_path>
before_validation
```

Se `cancellation_requested=true`, a execucao bloqueia/cancela no proximo checkpoint seguro, sem interromper escrita no meio.

### Terminalidade Governada

`TaskRunStore.terminalize_if_runtime_budget_exceeded()` foi adicionado para transformar runs presas em estado terminal governado quando excedem budget sem `result.json`.

Comportamento:

```text
run.status = blocked
result.status = blocked
finished_at != null
event = run_blocked
reason_code = TASKRUN_LIFECYCLE_TIMEOUT
safe_to_report_success = false
```

Isso nao declara sucesso; apenas impede run zumbi.

### Artifact Index Finalization

`UniversalArtifactRegistryService.create()` agora atualiza indice leve:

```text
data/runtime/artifact_index/by_task_run/{task_run_id}.json
data/runtime/artifact_index/by_artifact/{artifact_id}.json
```

O endpoint `by_task()` consulta esse indice antes de cair no registry completo.

IDs semanticos com caracteres nao portaveis no Windows sao preservados no payload, mas canonicalizados apenas no nome do arquivo de indice.

### Artifact Events

Antes:

```text
artifact_created
-> _create_artifact(...)
```

Isso permitia timeline dizer que um artifact foi criado antes do registro real.

Depois:

```text
artifact_creation_started
-> _create_artifact(...)
-> artifact_created com artifact_id/storage_ref/size_bytes
```

Assim, `artifact_created` passa a significar artifact registrado.

### CSV Metadata Field Policy

Campos volumosos agora passam por `_render_csv_cell()`.

Se a celula exceder budget:

```json
{
  "content_ref": "...",
  "hash": "...",
  "size_bytes": 1234,
  "canonical_key": "metadata",
  "reason_code": "CSV_FIELD_SPILLED_TO_REF",
  "preview": "..."
}
```

O valor nao e removido nem truncado silenciosamente. Ele vira ref auditavel com hash.

### Endpoints Leves

`UniversalTaskSessionService.events()` agora retorna:

```text
event_count_total
events_truncated
next_cursor
```

`summary`, `events` e `artifacts` aplicam supervisao de budget antes de montar a resposta leve.

Tambem foi corrigido um falso artifact ID: `artifact_result` nao e mais interpretado como `artifact_id`.

## Lifecycle Antes/Depois

### Antes

Run publica H1B4.3:

```text
/api/v1/chat = timeout
run.status = RUNNING
result.json = ausente
finished_at = null
```

### Depois

Run publica H1B4.3.1:

```text
task_run_id = task_run_76acee60438b4937a27f901e0184b2af
/api/v1/chat = timeout do cliente
run.status = blocked
result.status = blocked
finished_at = 2026-08-12T08:58:15.164096+00:00
result.json = 37 KB
events.json = 5.9 KB
run.json = 76 KB
Speaker Truth safe_to_report_success = false
```

Diagnostico:

```text
reports/runtime_consolidation/firetest5_h1b4_3_1_lifecycle_diagnostic.json
```

Resultado:

```text
terminal_transition_missing = false
server_completed = true
client_timeout = true
```

## Public Rerun

Request:

```text
reports/runtime_consolidation/firetest5_h1b4_3_1_public_chat_request.json
```

Resultado:

```text
reports/runtime_consolidation/firetest5_h1b4_3_1_public_chat_error.json
```

O cliente ainda atingiu timeout:

```text
TimeoutError('timed out')
```

Mas o servidor concluiu depois e persistiu estado terminal `blocked`.

Eventos principais:

```text
run_created
task_bootstrap_created
PlanningStarted
PlanningFinished
ExecutionPlanCreated
run_queued
run_started
project_analysis_started
project_analysis_finished
run_failed
run_blocked
```

Finding importante:

```text
PROJECT_ANALYSIS_LONG_RUNNING_BEFORE_ARTIFACT_CREATION
```

A run bloqueou antes de criar artifacts, entao esta execucao publica nao exercitou `music_inventory.csv` nem `evidence_phase1.zip`.

## Endpoint Timings

Arquivo:

```text
reports/runtime_consolidation/firetest5_h1b4_3_1_endpoint_timings_final.json
```

Resultados finais:

```text
summary   200 OK  13.091 ms  2.981 bytes
truth     200 OK  21.058 ms  1.460 bytes
events    200 OK   1.729 ms  4.942 bytes
artifacts 200 OK   9.022 ms    230 bytes
```

Os payloads estao leves. `truth` e `summary` ainda tem latencia residual relevante, mas nao carregam payload monstruoso.

## Artifact Index

Validado por teste unitario:

```text
test_artifact_runtime_lookup_uses_task_run_index_without_result_payload
```

Garantia:

```text
artifact criado
-> indice by_task_run escrito
-> lookup por task_run_id funciona sem result.json
-> resposta contem metadata leve sem abrir CSV/ZIP inteiro
```

No rerun publico H1B4.3.1, nenhum artifact foi criado antes do bloqueio, entao o endpoint retornou corretamente:

```text
artifact_state.status = none
count = 0
artifact_ids = []
```

Isso nao invalida o indice; apenas mostra que a proxima fronteira publica ainda esta antes da criacao de artifacts.

## Validation / Completion / Speaker Truth

Estado final publico:

```text
validation.status = blocked
completion.status = blocked
speaker_truth.safe_to_report_success = false
truth.status = blocked
```

Nenhuma camada declarou READY.

## Testes Executados

Suites principais:

```text
python -m pytest tests/unit/test_artifact_runtime_service.py tests/unit/test_universal_task_session_service.py tests/unit/test_task_run_store.py tests/unit/test_readonly_analysis_phase1_budgets.py tests/unit/test_contract_driven_perception_service.py tests/unit/test_media_metadata_capability_pack.py tests/unit/test_artifact_semantic_contract_service.py tests/unit/test_runtime_doctor_service.py tests/unit/test_validation_gate_service.py tests/unit/test_speaker_service.py -q
Resultado: 95 passed, 1 skipped
```

Suites adicionais:

```text
python -m pytest tests/unit/test_task_run_cancellation_service.py tests/unit/test_task_runtime_service.py tests/unit/test_task_bootstrap_runtime_service.py -q
Resultado: 21 passed
```

Total desta rodada:

```text
116 passed
1 skipped
```

## Gaps Restantes

```text
PUBLIC_CHAT_CLIENT_TIMEOUT_BEFORE_RESPONSE
PROJECT_ANALYSIS_LONG_RUNNING_BEFORE_ARTIFACT_CREATION
TRUTH_ENDPOINT_LATENCY_GAP
SUMMARY_ENDPOINT_LATENCY_GAP
ARTIFACT_INDEX_NOT_EXERCISED_BY_PUBLIC_RERUN_BECAUSE_NO_ARTIFACT_CREATED_BEFORE_BLOCK
OBSERVATIONS_AUTHORITY_MISSING
```

Tambem foi observado `readonly_artifact_execution_failed` com `ValueError` na run publica. A partir desta wave, o runtime passa a persistir `error_message` junto de `error_type`, para que a proxima execucao exponha a causa concreta sem depender de traceback local.

## Recomendacao

Antes de H1B5, executar uma H1B4.3.2 curta:

```text
ProjectAnalysis Budget Checkpoints & Public Chat Response Boundary
```

Objetivos:

```text
1. Colocar budget/checkpoints dentro de ProjectAnalysisService ou em seu boundary.
2. Fazer /api/v1/chat retornar resposta governada quando a execucao continua ou excede budget.
3. Persistir erro tipado completo quando artifact runtime falha antes da criacao do primeiro artifact.
4. Reexecutar Fase 1 ate pelo menos artifact_creation_started/artifact_created.
5. So entao validar publicamente o artifact index com music_inventory.csv real.
```

Depois disso, se artifact index e lifecycle ficarem estaveis, a sequencia natural volta para H1B5.

## Por Que Nao Houve Bypass

- O backend continua sem escrever artifact diretamente.
- O renderer continua sem observar metadata.
- O summary nao inventa artifact.
- A run bloqueada nao vira sucesso.
- O CSV nao recebe metadata falsa.
- Validation e Completion continuam bloqueando.
- Speaker Truth continua `safe_to_report_success=false`.
- Nenhuma regra menciona FireTest, caminho local, `music_inventory.csv` ou extensao especifica como criterio operacional.

## Conclusao

A H1B4.3.1 melhorou o comportamento publico, mas ainda nao fecha a Fase 1 publica completa.

O resultado correto e:

```text
terminalidade publica: PASS
endpoints leves: PASS com latencia residual
artifact index: PASS em unidade, nao exercitado no rerun publico
public /api/v1/chat completo: BLOCKED por longa execucao antes dos artifacts
truth: PRESERVED
```

Veredito final:

```text
FIRETEST5_H1B4_3_1_RUNTIME_BUDGET_BLOCK_EXPLAINED
```
