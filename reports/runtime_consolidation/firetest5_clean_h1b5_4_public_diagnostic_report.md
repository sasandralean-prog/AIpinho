# FireTest 5 Clean Public Diagnostic - H1B5.4 Context

## Veredito

```text
FIRETEST5_CLEAN_H1B5_4_BLOCKED_AT_PROJECT_ANALYSIS_SINGLE_FILE_READ_BUDGET
```

## Objetivo

Executar uma run limpa e higienizada do FireTest 5 com Fase 0/CVL formalizada, Fase 1 pelo endpoint publico `/api/v1/chat`, coleta dos endpoints canonicos e registro honesto do blocker publico atual.

## Escopo Executado

- processo publico local novo na porta 9088 ja ativo antes da chamada publica;
- Fase 0/CVL sem Runtime, Task, TaskRun, Operation ou artifacts operacionais;
- Fase 1 via `POST /api/v1/chat`;
- coleta de response, summary, truth, events, artifacts, result, run e artifact index;
- calibracao Phase0 vs Phase1;
- revalidacao service-equivalent da relationship stack H1B5.4.

## Fase 0 / CVL

- readiness_id: `cognitive_readiness_8b705c334fba4b3ead2f8acd9e8bcc03`
- decision: `NO_GO_EXPECTED_BLOCK`
- confidence: `0.78`
- predicted_frontier: `ARTIFACT_RENDER`
- predicted_component: `readonly_analysis_artifact_runtime`
- predicted_reason_code: `PHASE1_RUNTIME_BUDGET_EXCEEDED`
- runtime_executed: `False`
- task_created: `False`
- task_run_created: `False`
- operation_created: `False`
- operational_artifacts_created: `False`

## Fase 1 Publica

- session_id: `firetest5_clean_h1b5_4_20260812_160409`
- task_run_id: `task_run_999b3a4db8b9443a97c962796b02d7ba`
- client_response_status: `blocked`
- client_response_time_ms: `254578`
- client_exit_code: `0`
- summary.status: `BLOCKED`
- run.status: `blocked`
- result.status: `blocked`
- finished_at: `2026-08-12T19:08:49.033624+00:00`
- validation.status: `blocked`
- completion.status: `blocked`
- speaker_truth.safe_to_report_success: `False`

## Fronteira Observada

- actual_frontier: `PROJECT_ANALYSIS`
- actual_component: `ProjectAnalysisService`
- actual_reason_code: `PROJECT_ANALYSIS_SINGLE_FILE_READ_BUDGET_EXCEEDED`
- project_analysis.status: `timeout`
- project_analysis.reason_code: `PROJECT_ANALYSIS_SINGLE_FILE_READ_BUDGET_EXCEEDED`
- project_analysis.last_checkpoint: `project_analysis_single_file_read_budget_exceeded`
- project_analysis.last_completed_checkpoint: `after_file_read_item`
- project_analysis.blocking_operation: `file_read`
- files_discovered: `76`
- files_scanned: `78`
- files_read: `7`
- bytes_read: `23236`
- safe_to_continue: `False`

A run bloqueou novamente antes de `artifact_creation_started`, portanto a pilha relationship H1B5 nao foi exercitada pelo caminho publico nesta rodada.

## Terminalidade e Artifacts

- terminal_event_count: `1`
- duplicate_terminal_attempt_count: `2`
- post_terminal_event_count: `3`
- artifact_creation_started_count: `0`
- artifact_created_count: `0`
- post_terminal_artifact_created_count: `0`
- artifact_late_rejected_count: `0`
- artifact_endpoint_status: `blocked_before_artifact_creation`
- artifact_endpoint_count: `0`

Nao houve `artifact_created completed` pos-terminal. Nesta run, o runtime bloqueou antes da criacao de artifacts.

## Relationship / Observational Cognition

- relationship_cognition.status: `not_available`
- relationship_candidate_count: `0`
- relationship_observation_count: `0`
- relationship_evidence_count: `0`
- media_metadata_capability.status: `not_configured`
- public_path_blocked_before_relationship_capability: `True`

## Calibracao Phase0 vs Phase1

- calibration.status: `mismatch`
- overall_accuracy_score: `0.4`
- confidence_error: `0.38`
- divergence: Prediction diverged from actual runtime boundary. Predicted ARTIFACT_RENDER/readonly_analysis_artifact_runtime/PHASE1_RUNTIME_BUDGET_EXCEEDED; actual PROJECT_ANALYSIS/ProjectAnalysisService/PROJECT_ANALYSIS_SINGLE_FILE_READ_BUDGET_EXCEEDED.

A previsao acertou o outcome bloqueado, mas errou frontier/component/reason: a expectativa era `ARTIFACT_RENDER`, enquanto a execucao real retornou a `PROJECT_ANALYSIS` por budget de leitura de arquivo individual.

## Testes / Validacao Auxiliar

- `python -m pytest tests/unit/test_relationship_stack_integration_audit.py -q` -> `9 passed in 3.21s`

## Artifacts de Evidencia

- run_dir: `C:\Dev\AIpinho\reports\firetest5\firetest5_clean_h1b5_4_20260812_160409`
- `phase1_client_response.json`
- `phase1_endpoint_summary.json`
- `phase1_endpoint_truth.json`
- `phase1_endpoint_events.json`
- `phase1_endpoint_artifacts.json`
- `phase1_store_run.json`
- `phase1_store_result.json`
- `phase1_store_events.json`
- `phase0_vs_phase1_calibration.json`

## Higiene Residual

Foi detectado um `TaskRun` antigo ainda marcado como `running`, anterior a esta execucao limpa:

- residual_task_run_id: `task_run_e0996a23a45b4ca6a86b1968cfc05a45`
- residual_session_id: `firetest5_h1b4_3_public_validation_20260812_033847`
- latest_event_type: `run_cancel_requested`
- action_taken: `reported_only_no_state_mutation`

Esse residual nao e o `task_run_id` desta run e nao foi terminalizado automaticamente nesta rodada.

## Gaps Restantes

- `ProjectAnalysisService` ainda pode bloquear antes de artifact runtime por `PROJECT_ANALYSIS_SINGLE_FILE_READ_BUDGET_EXCEEDED`.
- A fronteira publica de relationship stack permanece nao exercitada por `/api/v1/chat` porque a run bloqueia antes dos artifacts/perception.
- `PUBLIC_CHAT_RESPONSE_BOUNDARY` segue como divida externa, embora esta chamada tenha retornado antes do limite de 360s do cliente.

## Recomendacao

Proxima wave recomendada: repair slice focado em ProjectAnalysis single-file read budget cooperation, antes de repetir FireTest 5 publico relationship-aware. H1B6 continua relevante, mas nesta run o blocker primario voltou a ser ProjectAnalysis antes de artifact runtime.

## Garantias Preservadas

- nao houve alteracao de codigo durante a run;
- Fase 0 nao virou Runtime;
- Validation e Completion permaneceram blocked;
- Speaker Truth permaneceu `safe_to_report_success=false`;
- relationship service-equivalent passou, mas nao foi promovido a Truth publica;
- nenhum artifact operacional foi fingido como completo.
