# FireTest 5 - H1B4.3.2 ProjectAnalysis Budget Checkpoints & Public Chat Response Boundary

## Veredito

`FIRETEST5_H1B4_3_2_PROJECT_ANALYSIS_BOUNDARY_READY_WITH_ARTIFACT_RENDER_LIFECYCLE_FINDING`

A wave fechou a fronteira de `ProjectAnalysisService`: a Fase 1 publica agora entra e sai de ProjectAnalysis com budget/resultado governado, erro tipado e diagnostico preservado. No rerun publico, ProjectAnalysis concluiu rapidamente como `partial` e a execucao avancou ate `artifact_creation_started`/`artifact_created`.

O bloqueio dominante se deslocou para uma fronteira posterior: renderizacao longa de artifact (`music_inventory.csv`) ainda pode continuar depois de uma terminalizacao por budget supervisionado. Isso nao foi mascarado.

## Escopo

Implementado:

- `ProjectAnalysisBudget` generico e configuravel por ambiente.
- `ProjectAnalysisResult` enriquecido com status governado, reason code, erro, duracao, metricas, budget e `safe_to_continue`.
- Checkpoints de budget/cancelamento dentro do ProjectAnalysis.
- Interpretacao explicita de `safe_to_continue=false` no runtime readonly.
- Eventos canonicos de ProjectAnalysis e `artifact_creation_started`.
- `artifact_state=blocked_before_artifact_creation` quando a run bloqueia antes de criar artifacts.
- Filtro mais estrito de artifact IDs para evitar pseudo-artifacts vindos de strings diagnosticas.

Nao implementado:

- H1B5.
- Sidecars.
- `observations`.
- Novo parser.
- Green artificial do FireTest 5.

## Arquivos Alterados

- `src/aipinho/schemas/analysis/project_analysis_budget.py`
- `src/aipinho/schemas/analysis/project_analysis_result.py`
- `src/aipinho/services/analysis/project_analysis_service.py`
- `src/aipinho/services/governance/runtime/readonly_analysis_artifact_runtime_service.py`
- `src/aipinho/schemas/runtime/universal_task_session.py`
- `src/aipinho/services/runtime/universal_task_session_service.py`
- `config/runtime/task_run_event_policy.yaml`
- `tests/unit/test_project_analysis_public_boundary.py`

## Budget Implementado

`ProjectAnalysisBudget`:

- `max_total_seconds`
- `max_files_scanned`
- `max_files_read`
- `max_bytes_read`
- `max_output_bytes`
- `cancel_poll_interval`
- `allow_partial_result`

Variaveis:

- `AIPINHO_PROJECT_ANALYSIS_MAX_SECONDS`
- `AIPINHO_PROJECT_ANALYSIS_MAX_FILES_SCANNED`
- `AIPINHO_PROJECT_ANALYSIS_MAX_FILES_READ`
- `AIPINHO_PROJECT_ANALYSIS_MAX_BYTES_READ`
- `AIPINHO_PROJECT_ANALYSIS_MAX_OUTPUT_BYTES`
- `AIPINHO_PROJECT_ANALYSIS_CANCEL_POLL_INTERVAL`
- `AIPINHO_PROJECT_ANALYSIS_ALLOW_PARTIAL`

## Checkpoints

Implementados no ProjectAnalysis:

- `before_scan`
- `after_scan_batch`
- `before_file_read`
- `after_file_read_batch`
- `before_symbol_extraction`
- `after_symbol_extraction_batch`
- `before_result_serialization`

Reason codes:

- `PROJECT_ANALYSIS_TIMEOUT`
- `PROJECT_ANALYSIS_CANCELLED`
- `PROJECT_ANALYSIS_FILE_SCAN_BUDGET_EXCEEDED`
- `PROJECT_ANALYSIS_FILE_READ_BUDGET_EXCEEDED`
- `PROJECT_ANALYSIS_OUTPUT_BUDGET_EXCEEDED`
- `PROJECT_ANALYSIS_BOUNDARY_ERROR`

## Public Rerun

Arquivo:

`reports/runtime_consolidation/firetest5_h1b4_3_2_public_project_analysis_rerun.json`

Run:

`task_run_a51357625212411193db4550616125ff`

Resultado:

- `/api/v1/chat`: timeout do cliente em `90026 ms`.
- `run.status`: `blocked`.
- `result.status`: `blocked`.
- `finished_at`: preenchido.
- `safe_to_report_success`: `false`.
- `project_analysis_status`: `completed`.
- Primeiro evento de artifact: `artifact_creation_started`.
- Artifacts indexados: `3`.

Artifacts indexados publicamente:

- `reports/firetest5/phase1_discovery.md`
- `reports/firetest5/project_inventory.md`
- `reports/firetest5/music_inventory.csv`

Payloads finais:

- `events.json`: `10627 bytes`
- `result.json`: `32969 bytes`
- `run.json`: `1062828 bytes`

## Achado Novo

`ARTIFACT_RENDER_CONTINUED_AFTER_TERMINAL_BUDGET`

Sequencia observada:

```text
artifact_creation_started: music_inventory.csv
run_blocked: TASKRUN_LIFECYCLE_TIMEOUT
artifact_created: music_inventory.csv
run_blocked
run_blocked
```

Interpretacao:

ProjectAnalysis nao e mais a fronteira dominante. A run atravessou ProjectAnalysis e criou artifacts. Porem, a renderizacao longa de artifact ainda nao possui checkpoints internos/cancelamento cooperativo suficientes para impedir evento pos-terminal.

Esse finding deve ser tratado antes de H1B5.

## Artifact Index

Antes:

- index unitario passava, mas nao era exercitado publicamente.

Depois:

- artifact index foi exercitado no caminho publico para artifacts reais.
- o endpoint/indice reconheceu artifacts criados por `task_run_id`.
- pseudo-artifacts como `artifact_result` e strings diagnosticas deixaram de ser tratados como artifact real.

## Testes

Executado:

```bash
python -m pytest tests/unit/test_project_analysis_public_boundary.py tests/unit/test_readonly_analysis_phase1_budgets.py tests/unit/test_artifact_runtime_service.py tests/unit/test_task_run_store.py tests/unit/test_universal_task_session_service.py tests/unit/test_media_metadata_capability_pack.py tests/unit/test_contract_driven_perception_service.py -q
```

Resultado:

```text
61 passed, 1 skipped
```

Compilacao:

```bash
python -m py_compile src/aipinho/schemas/analysis/project_analysis_budget.py src/aipinho/schemas/analysis/project_analysis_result.py src/aipinho/services/analysis/project_analysis_service.py src/aipinho/services/governance/runtime/readonly_analysis_artifact_runtime_service.py src/aipinho/services/runtime/universal_task_session_service.py
```

Resultado: passou.

## Preservacao de Autoridades

- ProjectAnalysis nao escreve artifact.
- Backend de metadata nao escreve CSV.
- Renderer nao observa metadata.
- Validation nao foi relaxada.
- Completion nao foi relaxado.
- Speaker Truth permaneceu `safe_to_report_success=false`.
- Nenhum hardcode de FireTest, caminho local, `music_inventory.csv` ou dominio foi introduzido.

## Gaps Restantes

- `/api/v1/chat` ainda e sincrono demais para runs longas.
- Artifact rendering precisa de checkpoints internos e cancelamento cooperativo.
- Deve haver protecao contra eventos pos-terminal.
- Deve haver idempotencia de terminalizacao para evitar multiplos `run_blocked`.
- `evidence_phase1.zip` ainda nao foi criado na run publica validada.

## Recomendacao

Antes de H1B5:

`H1B4.3.3 - Artifact Render Cooperative Budgets & Terminal Event Idempotency`

Objetivo sugerido:

- adicionar checkpoints dentro de `_artifact_content`/perception/renderizacao tabular;
- impedir artifact_created depois de terminal event;
- tornar `run_blocked` idempotente;
- fazer `/api/v1/chat` retornar resposta governada/accepted-running sem esperar a run inteira;
- preservar artifact partial state quando renderizacao for interrompida.

## Conclusao

A AIpinho atravessou a fronteira de ProjectAnalysis no caminho publico. Isso e progresso real.

O novo gargalo nao e mais analise de projeto. E renderizacao/terminalidade cooperativa durante artifact generation longa.

Bloqueio correto, sem green falso.
