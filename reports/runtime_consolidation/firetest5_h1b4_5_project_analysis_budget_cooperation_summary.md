# FireTest 5 H1B4.5 - ProjectAnalysis Budget Cooperation

## Veredito

FIRETEST5_H1B4_5_PROJECT_ANALYSIS_BUDGET_COOPERATION_READY

Finding principal restante:

ARTIFACT_RENDER_RUNTIME_BUDGET_EXCEEDED_AFTER_PROJECT_ANALYSIS_PARTIAL_HANDOFF

## Objetivo

Fazer ProjectAnalysisService cooperar com o budget durante selecao e leitura de arquivos, sem aumentar timeout e sem transformar parcialidade em sucesso operacional.

## Escopo

- Budget cooperativo explicito para ProjectAnalysis.
- Plano governado de selecao de arquivos.
- Plano governado de leitura de arquivos.
- Handoff reserve antes de consumir o budget inteiro.
- Partial readiness explicita.
- Runtime boundary capaz de avancar apenas quando o parcial e seguro.
- Summary publico com bloco leve de ProjectAnalysis.
- Preservacao da Fase 0/CVL e calibracao H1B4.4.

## Nao-goals

- Nao implementar H1B5.
- Nao implementar sidecars.
- Nao resolver observations.
- Nao mexer em metadata parsing.
- Nao implementar accepted_running.
- Nao tentar FIRETEST5_READY.
- Nao aumentar timeout como solucao.

## Estado inicial

Antes desta wave, a Fase 1 publica bloqueava antes de artifact runtime:

- frontier: PROJECT_ANALYSIS_FILE_READ
- reason_code: PROJECT_ANALYSIS_FILE_READ_TIMEOUT
- artifact_creation_started_count: 0

Durante esta wave, o primeiro rerun revelou uma fronteira ainda mais precisa:

- PROJECT_ANALYSIS_FILE_SELECTION_TIMEOUT

Isso confirmou que a selecao tambem precisava cooperar com budget, nao apenas a leitura.

## Arquivos alterados

- src/aipinho/schemas/analysis/project_analysis_cooperation.py
- src/aipinho/schemas/analysis/__init__.py
- src/aipinho/schemas/analysis/file_selection.py
- src/aipinho/schemas/analysis/file_context_bundle.py
- src/aipinho/schemas/analysis/project_analysis_request.py
- src/aipinho/schemas/analysis/project_analysis_result.py
- src/aipinho/services/analysis/file_selection_service.py
- src/aipinho/services/analysis/file_context_builder.py
- src/aipinho/services/analysis/project_analysis_service.py
- src/aipinho/services/governance/runtime/readonly_analysis_artifact_runtime_service.py
- src/aipinho/services/runtime/universal_task_session_service.py
- config/runtime/task_run_event_policy.yaml
- tests/unit/test_project_analysis_service.py
- tests/unit/test_project_analysis_public_boundary.py

## Causa raiz

A demora nao estava mais em path resolution/root scan.

A regiao cara observada foi:

- FileSelectionService validando/statando candidatos.
- Selecao inteira so era avaliada depois de terminar.
- O budget global podia estourar dentro da selecao sem FileSelectionPlan parcial.
- File read ja tinha checkpoints por item, mas faltava handoff reserve e partial readiness formal.

## ProjectAnalysisBudgetCooperationPolicy

Policy publica final:

- max_total_seconds: 20.0
- max_selection_seconds: 13.0
- max_file_read_seconds: 9.0
- max_single_file_read_ms: 3000
- max_files_scanned: 5000
- max_files_selected: 12
- max_files_read: 80
- max_bytes_read: 2000000
- min_remaining_ms_for_handoff: 1500
- min_remaining_ms_for_result_serialization: 750
- allow_partial_result: true
- allow_partial_handoff: true

## FileSelectionPlan

Implementado com:

- candidate_count
- selected_count
- selection_strategy
- selection_budget_ms
- elapsed_ms
- selected_files
- rejected_files_summary
- selection_reason_codes
- budget_exceeded
- partial

A selecao agora pode parar por budget proprio e retornar parcial, em vez de deixar o timeout global matar o ProjectAnalysis sem plano.

## FileReadPlan

Implementado no FileContextBuilder com:

- selected_files
- read_order
- max_files_read
- max_bytes_read
- max_single_file_read_ms
- files_read
- bytes_read
- skipped_files
- read_errors
- budget_exceeded
- partial

A leitura continua incremental e checa budget/cancelamento via callbacks por item.

## Handoff reserve

ProjectAnalysis agora avalia reserva de tempo antes de continuar para etapas caras.

Se existe contexto minimo:

- retorna status partial
- reason_code PROJECT_ANALYSIS_PARTIAL_HANDOFF
- safe_to_continue true

Se nao existe contexto minimo:

- bloqueia com PROJECT_ANALYSIS_INSUFFICIENT_PARTIAL_CONTEXT
- safe_to_continue false

## ProjectAnalysisPartialReadiness

Resultado publico final:

- safe_to_continue_to_artifact_runtime: true
- minimum_context_available: true
- workspace_root_resolved: true
- tree_summary_available: true
- file_selection_available: true
- file_context_available: false
- missing_context: file_context
- confidence: 0.62

Isso permitiu handoff honesto para artifact runtime, marcado como parcial.

## ProjectAnalysisResult antes/depois

Antes:

- timeout em file_read ou selection
- safe_to_continue false
- artifact_creation_started nao alcancado

Depois:

- status: partial
- reason_code: PROJECT_ANALYSIS_PARTIAL_HANDOFF
- files_discovered: 76
- files_selected: 12
- files_read: 0
- bytes_read: 0
- remaining_budget_ms_at_return: 4375
- handoff_reserve_reached: true
- safe_to_continue: true

## Runtime boundary antes/depois

Antes:

- ProjectAnalysis bloqueado impedia artifact runtime.

Depois:

- ProjectAnalysis parcial seguro emite:
  - project_analysis_handoff_reserve_reached
  - project_analysis_partial
  - project_analysis_finished
- Runtime avanca para:
  - artifact_creation_started

Artifacts criados carregam:

- project_analysis_status: partial
- project_analysis_reason_code: PROJECT_ANALYSIS_PARTIAL_HANDOFF
- project_analysis_partial_readiness

## Fase 0 preservada

Fase 0 final:

- readiness_id: cognitive_readiness_280f1a39c4d34a169c22ee93ef815866
- decision: NO_GO_EXPECTED_BLOCK
- predicted_frontier: PROJECT_ANALYSIS_FILE_READ
- predicted_component: ProjectAnalysisService
- predicted_reason_code: PROJECT_ANALYSIS_FILE_READ_TIMEOUT
- task_run_created_by_phase0: false

A previsao nao foi reescrita para parecer que acertou.

## Calibracao antes/depois

A H1B4.4 tinha calibracao matched contra ProjectAnalysis file read timeout.

Depois da H1B4.5:

- calibration.status: partial_match
- actual_frontier: ARTIFACT_RENDER
- actual_component: readonly_analysis_artifact_runtime
- actual_reason_code: PHASE1_RUNTIME_BUDGET_EXCEEDED
- overall_accuracy_score: 0.48
- confidence_error: 0.36

Interpretacao: a previsao antiga foi honestamente superada pela mudanca operacional. ProjectAnalysis atravessou como parcial seguro e a fronteira mudou para artifact render.

## Public rerun result

Run publica final:

- task_run_id: task_run_d84888dc1f93473092f1c91440fce35e
- client_status: client_timeout
- client_response_time_ms: 300179
- run_status: BLOCKED
- result_status: blocked
- validation_status: blocked
- completion_status: blocked
- speaker_truth.safe_to_report_success: false

O timeout do cliente confirma que PUBLIC_CHAT_RESPONSE_BOUNDARY segue como finding, mas nao era goal desta wave.

## Artifact runtime

- artifact_creation_started_count: 1
- artifact_created_count: 0
- artifact_state.status: partial
- terminal_event_count: 1
- terminalization_already_applied_count: 2

Artifact render foi exercitado e bloqueou em:

- frontier: ARTIFACT_RENDER
- reason_code: PHASE1_RUNTIME_BUDGET_EXCEEDED
- stage: after_registry_create_before_event

Nao houve artifact_created completed depois do terminal.

## Testes executados

```text
python -m pytest tests/unit/test_project_analysis_service.py tests/unit/test_project_analysis_public_boundary.py -q
15 passed in 88.24s
```

```text
python -m pytest tests/unit/test_project_analysis_service.py tests/unit/test_project_analysis_public_boundary.py tests/unit/test_readonly_analysis_phase1_budgets.py tests/unit/test_cognitive_readiness_service.py tests/unit/test_cognitive_validation_laboratory_service.py tests/unit/test_universal_task_session_service.py -q
48 passed in 137.26s
```

```text
python -m py_compile ...
PASS
```

## Hardcode audit

Busca final por FireTest/projeto/caminho nos servicos/schemas alterados encontrou apenas:

- readonly_analysis_artifact_runtime_service.py usando firetest5_phase0_vs_phase1_calibration.json, existente da H1B4.4.

Nao foram adicionados hardcodes de:

- FireTest como regra de selecao
- Pinhoabacaxi
- music_inventory.csv
- caminhos locais

## Gaps restantes

- Public Chat Response Boundary ainda e sincronico e pode exceder timeout do cliente.
- Artifact render voltou a ser a fronteira principal.
- Artifact registrado antes do terminal apareceu no endpoint, mas artifact_created event nao foi emitido porque o budget estourou em after_registry_create_before_event.
- H1B4.3.3 deve ser repetida agora que ProjectAnalysis atravessa.

## Recomendacao

Proxima wave:

H1B4.6 - Public Chat Accepted Running Boundary ou rerun H1B4.3.3 artifact render terminality, dependendo da prioridade.

Como a run publica ainda levou o cliente a timeout, eu recomendaria primeiro tratar o boundary publico accepted_running/timeout_blocked. Depois repetir H1B4.3.3 com coleta limpa.

## Por que nao houve bypass

- ProjectAnalysis nao foi pulado.
- ProjectAnalysis parcial foi marcado como parcial.
- O Runtime so avancou porque partial_readiness.safe_to_continue_to_artifact_runtime era true.
- Artifacts carregaram provenance de ProjectAnalysis parcial.
- Validation permaneceu blocked.
- Completion permaneceu blocked.
- Speaker Truth permaneceu safe_to_report_success=false.
- A previsao da Fase 0 nao foi alterada para parecer correta.

