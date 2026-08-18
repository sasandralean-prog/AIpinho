# FireTest 5 Clean Public Diagnostic After TaskRun Hygiene

## Veredito

```text
FIRETEST5_CLEAN_AFTER_HYGIENE_PHASE0_CALIBRATED_BLOCKED_AT_PROJECT_ANALYSIS_SINGLE_FILE_READ_BUDGET
```

## Higiene Executada

- hygiene_report: `reports/runtime_consolidation/firetest5_taskrun_hygiene_before_clean_rerun.md`
- candidates: `2`
- applied: `2`
- active_after_count: `0`
- deletes_evidence: `False`

TaskRuns reconciliados:
- `task_run_c34f13ea90424209ae2742f7b30a9ee3`: `created` -> `cancelled`; session `firetest5_h1b4_3_3_public_artifact_terminality_20260812`
- `task_run_e0996a23a45b4ca6a86b1968cfc05a45`: `running` -> `cancelled`; session `firetest5_h1b4_3_public_validation_20260812_033847`

## Precheck

- `/api/v1/health`: ok
- `/api/v1/runtime/hygiene/queue-health`: active_runs=0, queued_runs=0, stale_runs=0, pending_approvals=0
- active non-terminal TaskRuns before rerun: `0`

## Fase 0 / CVL

- readiness_id: `cognitive_readiness_9e5b18e3a2db48b9ad4dffe6c0635abf`
- decision: `NO_GO_EXPECTED_BLOCK`
- confidence: `0.82`
- predicted_frontier: `PROJECT_ANALYSIS`
- predicted_component: `ProjectAnalysisService`
- predicted_reason_code: `PROJECT_ANALYSIS_SINGLE_FILE_READ_BUDGET_EXCEEDED`
- runtime_executed: `False`
- task_created: `False`
- task_run_created: `False`
- operation_created: `False`
- operational_artifacts_created: `False`

## Fase 1 Publica

- session_id: `firetest5_clean_after_hygiene_20260812_221154`
- task_run_id: `task_run_f5530951ede84b99b5fbbbcc63e5da91`
- client_response_status: `blocked`
- client_response_time_ms: `279299`
- client_exit_code: `0`
- summary.status: `BLOCKED`
- run.status: `blocked`
- result.status: `blocked`
- finished_at: `2026-08-13T01:16:38.112896+00:00`
- validation.status: `blocked`
- completion.status: `blocked`
- speaker_truth.safe_to_report_success: `False`

## Fronteira Observada

- actual_frontier: `PROJECT_ANALYSIS`
- actual_component: `ProjectAnalysisService`
- actual_reason_code: `PROJECT_ANALYSIS_SINGLE_FILE_READ_BUDGET_EXCEEDED`
- project_analysis.status: `timeout`
- project_analysis.reason_code: `PROJECT_ANALYSIS_SINGLE_FILE_READ_BUDGET_EXCEEDED`
- last_checkpoint: `project_analysis_single_file_read_budget_exceeded`
- last_completed_checkpoint: `after_file_read_item`
- blocking_operation: `file_read`
- duration_ms: `25796`
- files_discovered: `76`
- files_scan_attempted: `127`
- files_scanned: `78`
- files_read: `3`
- bytes_read: `17214`
- current_path_sample: `src/main/kotlin/com/pinhoabacaxi/musicasdesktop/audio/dsp/DesktopEqualizerTemplateJsonCodec.kt`
- safe_to_continue: `False`

A run bloqueou antes de `artifact_creation_started`; portanto a pilha relationship H1B5 continua validada service-equivalent, mas nao exercitada pelo caminho publico.

## Terminalidade e Artifacts

- terminal_event_count: `1`
- duplicate_terminal_attempt_count: `2`
- post_terminal_event_count: `3`
- artifact_creation_started_count: `0`
- artifact_created_count: `0`
- post_terminal_artifact_created_count: `0`
- artifact_endpoint_status: `blocked_before_artifact_creation`
- artifact_endpoint_count: `0`

## Relationship / Observational Cognition

- relationship_cognition.status: `not_available`
- relationship_candidate_count: `0`
- relationship_observation_count: `0`
- relationship_evidence_count: `0`
- media_metadata_capability.status: `not_configured`
- public_path_blocked_before_relationship_capability: `True`

## Calibracao Phase0 vs Phase1

- calibration.status: `matched`
- overall_accuracy_score: `0.9625`
- confidence_error: `0.1425`
- divergence: Prediction matched the dominant Phase 1 boundary.

## Testes / Validacao Auxiliar

- `python -m pytest tests/unit/test_relationship_stack_integration_audit.py -q` -> `9 passed in 3.50s`

## Artifacts de Evidencia

- run_dir: `C:\Dev\AIpinho\reports\firetest5\firetest5_clean_after_hygiene_20260812_221154`
- `phase1_client_response.json`
- `phase1_endpoint_summary.json`
- `phase1_endpoint_truth.json`
- `phase1_endpoint_events.json`
- `phase1_endpoint_artifacts.json`
- `phase1_store_run.json`
- `phase1_store_result.json`
- `phase1_store_events.json`
- `phase0_vs_phase1_calibration.json`

## Gaps Restantes

- `ProjectAnalysisService` ainda bloqueia por `PROJECT_ANALYSIS_SINGLE_FILE_READ_BUDGET_EXCEEDED` antes de artifact runtime.
- A relationship stack H1B5 nao foi exercitada publicamente porque o public path bloqueou antes de artifacts/perception.
- O boundary publico ainda demora varios minutos para responder, apesar de nao ter estourado o timeout de 360s nesta rodada.

## Recomendacao

Proxima acao recomendada: repair slice focado em `ProjectAnalysisService` single-file read budget/selection-read cooperation. Depois repetir FireTest 5 publico. H1B6 continua como divida de UX/runtime boundary, mas o blocker primario desta run e ProjectAnalysis.

## Garantias Preservadas

- limpeza sem apagar evidencia;
- Fase 0 nao criou Runtime/Task/TaskRun/Operation;
- run publica nao modificou workspace;
- Validation e Completion permaneceram blocked;
- Speaker Truth permaneceu `safe_to_report_success=false`;
- nenhum artifact operacional foi fingido como completo.
