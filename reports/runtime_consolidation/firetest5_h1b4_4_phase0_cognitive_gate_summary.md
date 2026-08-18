# FireTest 5 H1B4.4 - Phase 0 Cognitive Gate Summary

## Veredito

FIRETEST5_H1B4_4_PHASE0_COGNITIVE_GATE_READY

## Objetivo

Formalizar a Fase 0/CVL como gate cognitivo canonico: prever antes de executar, preservar a hipotese, anexar a hipotese a Fase 1 e calibrar previsao contra o resultado real.

Esta wave nao tentou buscar FIRETEST5_READY.

## Escopo

- Criar contratos canonicos de prontidao cognitiva.
- Garantir que a Fase 0 nao crie Task, TaskRun, Operation nem artifacts operacionais.
- Persistir CognitiveReadinessResult e relatorios CVL de Fase 0.
- Permitir que a Fase 1 referencie a Fase 0.
- Gerar CognitivePredictionCalibrationResult apos bloqueio da Fase 1.
- Expor cognitive_readiness leve no summary publico.

## Nao-goals preservados

- Nao resolver PROJECT_ANALYSIS_FILE_READ_TIMEOUT.
- Nao otimizar ProjectAnalysisService.
- Nao mexer em artifact rendering.
- Nao implementar H1B5.
- Nao criar sidecars.
- Nao resolver observations.
- Nao criar parser novo.
- Nao relaxar Validation, Completion ou Speaker Truth.

## Arquivos alterados

- src/aipinho/schemas/cvl/cognitive_readiness.py
- src/aipinho/schemas/cvl/__init__.py
- src/aipinho/services/cvl/cognitive_readiness_service.py
- src/aipinho/services/cvl/__init__.py
- src/aipinho/schemas/chat/chat_request.py
- src/aipinho/services/governance/runtime/readonly_analysis_artifact_runtime_service.py
- src/aipinho/services/runtime/universal_task_session_service.py
- config/runtime/task_run_event_policy.yaml
- tests/unit/test_cognitive_readiness_service.py

## Contratos criados

- CognitiveReadinessResult
- CognitiveReadinessDecision
- CognitivePrediction
- CognitiveDependencyGraph
- CognitiveCoverageReport
- CognitiveSimulationResult
- CognitiveFrontierReport
- CognitivePredictionCalibrationResult

## Invariantes da Fase 0

Resultado final:

- runtime_executed = false
- task_created = false
- task_run_created = false
- operation_created = false
- operational_artifacts_created = false
- task_runs_before = 30
- task_runs_after = 30
- task_run_created_by_phase0 = false

Se qualquer uma dessas invariantes falhar, CognitiveReadinessResult e invalido.

## Decisao cognitiva gerada

- readiness_id: cognitive_readiness_a31b5763e9b64b478174dcfa4d6b0d3f
- decision: NO_GO_EXPECTED_BLOCK
- confidence: 0.84
- safe_to_start_phase1: false
- requires_user_override: true

A execucao da Fase 1 apesar do NO_GO foi registrada como:

- runtime_executed_despite_cvl_no_go = true

## Previsao gerada

- prediction_id: cognitive_prediction_b75c882215c141a7a96de74a87d4cbe1
- predicted_outcome: blocked
- predicted_frontier: PROJECT_ANALYSIS_FILE_READ
- predicted_component: ProjectAnalysisService
- predicted_reason_code: PROJECT_ANALYSIS_FILE_READ_TIMEOUT
- predicted_blocking_stage: after_file_read_item
- predicted_failure_mode: governed_timeout

Importante: essa fronteira especifica nao foi hardcoded no servico. Ela veio de frontier_context explicito, com provenance em:

- reports/runtime_consolidation/firetest5_h1b4_3_3a_project_analysis_zero_progress_timeout_summary.md

Busca por termos especificos nos modulos novos do CVL retornou NO_MATCHES para:

- PROJECT_ANALYSIS_FILE_READ_TIMEOUT
- PROJECT_ANALYSIS_FILE_READ
- music_inventory
- media_metadata_reader
- Pinhoabacaxi
- pinho music

## Dependency graph

O grafo canonico representa o caminho:

Intent -> Lifecycle -> Workspace -> Contracts -> ProjectAnalysis -> ObservedEntity -> Perception -> Capability -> Observer -> ArtifactRuntime -> Validation -> Completion -> SpeakerTruth

Contratos esperados:

- analysis_readonly
- task_run_terminality
- artifact_runtime
- speaker_truth

Capabilities esperadas:

- read_workspace
- artifact_generate

## Coverage report

Coverage cognitivo foi produzido por dominio, incluindo:

- Intent
- Lifecycle
- Workspace
- Contracts
- ProjectAnalysis
- Perception
- CapabilityRegistry
- ObserverInfrastructure
- Evidence
- ArtifactRuntime
- Validation
- Completion
- SpeakerTruth
- RuntimeDoctor
- CVL

Coverage continua sendo diagnostico cognitivo, nao sucesso operacional.

## Simulation result

A simulacao canonica agora reflete a previsao final:

- simulated_blocking_point: ProjectAnalysis
- simulated_reason_code: PROJECT_ANALYSIS_FILE_READ_TIMEOUT
- simulated_confidence: 0.84

A simulacao nao criou Task, TaskRun, Operation, artifact operacional nem modificou workspace.

## Cognitive frontier

- primary_frontier: PROJECT_ANALYSIS_FILE_READ
- secondary_frontiers:
  - PUBLIC_CHAT_RESPONSE_BOUNDARY
  - ARTIFACT_RENDER_TERMINALITY_AFTER_PROJECT_ANALYSIS
- frontier_confidence: 0.84

## Como a Fase 1 referencia a Fase 0

ChatContext recebeu campos opcionais:

- cognitive_readiness_id
- phase0_result_ref
- phase0_prediction_id
- phase0_decision

ReadonlyAnalysisArtifactRuntimeService anexa esses refs ao TaskRun e emite:

- phase0_prediction_attached

O summary publico expoe um bloco leve:

- readiness_id
- decision
- confidence
- predicted_frontier
- predicted_component
- predicted_reason_code
- runtime_executed_despite_no_go
- calibration.status
- calibration.overall_accuracy_score

## Rerun diagnostico minimo

Fluxo executado:

1. Fase 0/CVL formalizada gerou CognitiveReadinessResult.
2. Confirmado que a Fase 0 nao criou TaskRun.
3. Fase 1 executada via /api/v1/chat com phase0_result_ref.
4. Summary, truth, events e artifacts foram coletados.
5. Calibracao phase0_vs_phase1 foi gerada.

Run publica final:

- task_run_id: task_run_368cdfb317f644ba84a2c899baab4938
- operation_id: chatop_368cdfb317f644ba84a2c899baab4938
- client_response_status: 200
- client_response_time_ms: 249402
- client_status: blocked
- message_type: assistant_degraded_answer
- summary.status: BLOCKED
- result.status: blocked
- validation.status: blocked
- completion.status: blocked
- Speaker Truth safe_to_report_success: false

Artifact state:

- status: blocked_before_artifact_creation
- count: 0
- reason_code: PROJECT_ANALYSIS_FILE_READ_TIMEOUT

## Calibracao phase0_vs_phase1

- calibration_id: cognitive_calibration_8aae1489f02a4f149b12b025fa63487f
- status: matched
- actual_outcome: blocked
- actual_frontier: PROJECT_ANALYSIS_FILE_READ
- actual_component: ProjectAnalysisService
- actual_reason_code: PROJECT_ANALYSIS_FILE_READ_TIMEOUT
- prediction_matched_outcome: true
- prediction_matched_frontier: true
- prediction_matched_component: true
- prediction_matched_reason_code: true
- prediction_matched_contract: true
- prediction_matched_causal_chain: true
- confidence_was_calibrated: true
- confidence_error: 0.06
- specificity_score: 1.0
- causal_accuracy_score: 0.6667
- overall_accuracy_score: 0.9
- false_positive: false
- false_negative: false

## Eventos

- event_count_total: 14
- terminal_event_count: 1
- terminalization_already_applied_count: 2
- artifact_creation_started_count: 0
- artifact_created_count: 0

Sequencia principal:

1. run_created
2. task_bootstrap_created
3. PlanningStarted
4. PlanningFinished
5. ExecutionPlanCreated
6. phase0_prediction_attached
7. run_queued
8. run_started
9. project_analysis_started
10. project_analysis_budget_exceeded
11. run_blocked
12. terminalization_already_applied
13. phase0_prediction_calibrated
14. terminalization_already_applied

## Validation, Completion e Speaker Truth

Preservados:

- Validation permaneceu blocked.
- Completion permaneceu blocked.
- Speaker Truth permaneceu safe_to_report_success=false.
- CVL nao decidiu sucesso operacional.
- A previsao nao virou Truth.

## Testes executados

Focados:

```text
python -m pytest tests/unit/test_cognitive_readiness_service.py -q
4 passed in 28.91s
```

Regressao focada:

```text
python -m pytest tests/unit/test_cognitive_readiness_service.py tests/unit/test_cognitive_validation_laboratory_service.py tests/unit/test_project_analysis_service.py tests/unit/test_project_analysis_public_boundary.py tests/unit/test_readonly_analysis_phase1_budgets.py tests/unit/test_universal_task_session_service.py -q
42 passed in 78.91s
```

Compilacao:

```text
python -m py_compile src/aipinho/schemas/cvl/cognitive_readiness.py src/aipinho/schemas/cvl/__init__.py src/aipinho/services/cvl/cognitive_readiness_service.py src/aipinho/services/cvl/__init__.py src/aipinho/schemas/chat/chat_request.py src/aipinho/services/governance/runtime/readonly_analysis_artifact_runtime_service.py src/aipinho/services/runtime/universal_task_session_service.py
PASS
```

## Reports e artifacts gerados

- reports/runtime_consolidation/firetest5_phase0_cognitive_readiness_result.json
- reports/runtime_consolidation/firetest5_h1b4_4_phase0_generation_check.json
- reports/runtime_consolidation/firetest5_phase0_vs_phase1_calibration.json
- reports/runtime_consolidation/firetest5_h1b4_4_phase0_cognitive_gate_collected.json
- reports/firetest5/phase0_cognitive_readiness.md
- reports/firetest5/phase0_prediction.md
- reports/firetest5/phase0_dependency_graph.md
- reports/firetest5/phase0_coverage.md
- reports/firetest5/phase0_simulation.md
- reports/firetest5/phase0_frontier.md
- reports/firetest5/phase6_prediction_accuracy.md
- reports/firetest5/phase6_cvl_validation.md

Esses sao reports CVL de Fase 0, nao artifacts operacionais de TaskRun.

## Gaps restantes

- PROJECT_ANALYSIS_FILE_READ_TIMEOUT continua sendo a fronteira operacional real.
- Public Chat Response Boundary ainda responde apenas depois de uma execucao longa; accepted_running nao foi implementado nesta wave.
- Artifact rendering H1B4.3.3 nao foi revalidado nesta run porque ProjectAnalysis bloqueou antes de artifact_creation_started.

## Recomendacao

Proxima wave recomendada:

H1B4.5 - ProjectAnalysis File Read Budget Cooperation

Objetivo: fazer ProjectAnalysis cooperar melhor com budget durante selecao/leitura de arquivos, sem aumentar timeout e sem mascarar bloqueio.

Depois que ProjectAnalysis atravessar sob budget, repetir o diagnostico H1B4.3.3 de artifact render terminality no caminho publico.

## Por que nao houve bypass

- Fase 0 nao executou Runtime.
- Fase 0 nao criou Task, TaskRun, Operation nem artifact operacional.
- A previsao especifica veio de frontier_context explicito com provenance.
- O servico CVL nao contem hardcode da fronteira atual.
- A Fase 1 executou no Runtime governado real.
- O bloqueio permaneceu bloqueio.
- Speaker Truth continuou exigindo evidencia real.
