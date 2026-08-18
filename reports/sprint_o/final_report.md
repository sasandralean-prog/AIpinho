# Sprint O — Intelligent Planner & Autonomous Task Decomposition

Veredito: INTELLIGENT_PLANNER_READY

Data: 2026-07-04

## Objetivo

Implementar um Planner inteligente capaz de decompor tarefas complexas em Execution Graphs governados, sem workflows especificos por agente, provider, mobile ou launcher.

## Arquitetura implementada

- Planning Engine para classificar objetivo, complexidade, risco e necessidade de approval/review.
- Task Decomposer para gerar nodes dinamicos por tipo de tarefa, stack e capabilities.
- Execution Strategy Builder para estrategia, grupos paralelos, risco, custo e alternativas descartadas.
- Dependency Resolver para dependencias entre nodes planejados.
- Graph Optimizer para ordem topologica.
- Risk-aware Planner para constraints de policy, Speaker Truth e approval.
- Planning Report persistido dentro da TaskRun/Execution Graph como parte da mesma fonte da verdade.

## Componentes criados

- `src/aipinho/schemas/runtime/intelligent_planner.py`
- `src/aipinho/services/runtime/intelligent_planner_service.py`
- `config/runtime/planning_policy.yaml`
- `config/runtime/planning_constraints.yaml`
- `config/runtime/planning_cost_policy.yaml`
- `config/runtime/planning_parallel_policy.yaml`
- `config/runtime/planning_review_policy.yaml`
- `apps/launcher/ui/tabs/planning_tab.py`
- `tests/unit/test_intelligent_planner_service.py`

## Componentes alterados

- `src/aipinho/schemas/runtime/execution_graph.py`
- `src/aipinho/services/runtime/execution_graph_service.py`
- `src/aipinho/services/runtime/task_runtime_service.py`
- `src/aipinho/api/routers/task_runtime_router.py`
- `src/aipinho/services/mobile_view_models/pipeline_mobile_aggregator.py`
- `apps/launcher/ui/launcher_app.py`
- `apps/launcher/ui/api/pipeline_client.py`
- `apps/mobile/android/app/src/main/java/br/com/aipinho/mobile/network/TaskRuntimeClient.kt`
- `apps/mobile/android/app/src/main/java/br/com/aipinho/mobile/ui/screens/PipelineScreen.kt`
- `apps/mobile/android/app/src/test/java/br/com/aipinho/mobile/PipelineApprovalActionContractTest.kt`
- `tests/integration/test_launcher_multi_agent_ui_contract.py`
- `config/runtime/task_run_event_policy.yaml`

## Endpoints

- `GET /api/v1/task-runs/{run_id}/planning/report`
- `POST /api/v1/task-runs/{run_id}/planning/nodes/{node_id}/replan`

O endpoint cooperativo existente `POST /api/v1/task-runs/{run_id}/execution-graph/cooperative` agora cria primeiro um Planning Report e constroi o Execution Graph a partir dele.

## UX

- Launcher ganhou aba `Planning`, lendo o mesmo view-model mobile.
- Pipeline do Launcher continua exibindo Execution Graph e node actions.
- Mobile passou a mostrar resumo `Execution Plan` no card da fila.
- Mobile ganhou client methods `planningReport` e `replanNode`.

## Testes executados

- `python -m py_compile` nos arquivos Python alterados.
- `python -m pytest tests/unit/test_intelligent_planner_service.py tests/unit/test_multi_agent_execution_graph.py tests/unit/test_task_runtime_service.py tests/integration/test_launcher_multi_agent_ui_contract.py -q`
  - Resultado: 34 passed.
- `python -m pytest tests/unit/test_external_collaboration_layer.py tests/unit/test_real_delegation_runtime.py tests/unit/test_runtime_delegation_events.py -q`
  - Resultado: 9 passed.
- `./gradlew.bat :app:testDebugUnitTest --tests br.com.aipinho.mobile.PipelineApprovalActionContractTest --tests br.com.aipinho.mobile.MultiAgentMobileUiContractTest`
  - Resultado: BUILD SUCCESSFUL.
- `./gradlew.bat :app:assembleDebug`
  - Resultado: BUILD SUCCESSFUL.
- `powershell -ExecutionPolicy Bypass -File scripts/package_launcher_desktop.ps1`
  - Resultado: `C:\Dev\AIpinho\dist\AIpinhoLauncher.exe`.

## Smoke real

Criado TaskRun via API e chamado:

- `POST /api/v1/task-runs/{run_id}/execution-graph/cooperative`
- `GET /api/v1/task-runs/{run_id}/planning/report`
- `GET /api/v1/task-runs/{run_id}/execution-graph/poll`

Resultado:

- `run_id`: `task_run_e3381da22b624b4396f47cb255b9e790`
- `graph_id`: `exec_graph_4b3aaa40dc3b444eaa72d9f56ce25fd5`
- `planning_report_id`: `planning_report_8bd0d865930f4215bfecd5ef0a56a372`
- task type: `android`
- strategy: `risk_aware_adaptive_graph`
- nodes: `node_planner,node_executor,node_debugger,node_vision,node_ocr,node_review,node_memory,node_supervisor,node_final`
- poll status: `ready`

## Build e instalacao

- APK: `C:\Dev\AIpinho\apps\mobile\android\app\build\outputs\apk\debug\app-debug.apk`
- Instalacao em dispositivo fisico `ZF5253V88S`: Success.
- Launcher: `C:\Dev\AIpinho\dist\AIpinhoLauncher.exe`
- Copia atualizada: `C:\Users\rafae\Desktop\AIpinhoLauncher.exe`

## Backend

Backend 9088 reiniciado pelo fluxo canonico:

- PID atual: `36140`
- Local: `http://127.0.0.1:9088/api/v1/health`
- Tailscale: `http://100.107.124.8:9088/api/v1/health`

## Riscos restantes

- O planner ainda usa heuristicas configuraveis de stack/capability; a etapa futura Sprint O/P pode plugar modelo real para razoes mais profundas, mantendo o mesmo contrato.
- O replanejamento atual foca retry/replan de node e dependentes; ainda nao altera dinamicamente topologia de nodes em runtime.
- O Launcher mostra Planning Report por view-model mobile para evitar duplicacao, mas ainda pode ganhar acoes dedicadas de replan visual por node.

## Veredito

INTELLIGENT_PLANNER_READY
