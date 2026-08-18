# Sprint N - Multi-Agent Execution Graph & Cooperative Runtime

## Veredito

MULTI_AGENT_EXECUTION_GRAPH_READY

## Objetivo

Transformar a delegacao real do Sprint M em uma base de execucao cooperativa por grafo, onde a AIpinho continua sendo a autoridade unica de criacao, execucao, validacao, memoria, artifacts e resposta final.

## Arquitetura implementada

- `ExecutionGraph` foi expandido para suportar grafo cooperativo alem do grafo derivado de `TaskRunPlan`.
- `ExecutionNode` agora possui executor, runtime profile, inputs, outputs, artifacts, speakertruth, review, approval, memory candidates, retry count e metricas.
- Foram adicionados `ExecutionDependency`, `NodeRuntime` e `ExecutionResult`.
- `ExecutionGraphService` ganhou criacao de grafo cooperativo, polling, start/complete/fail/retry/cancel por node.
- `TaskRuntimeService` expoe operacoes governadas de graph/node sem permitir que provider externo crie/finalize grafo.
- Eventos oficiais adicionados: `execution_graph_created`, `node_started`, `node_completed`, `node_failed`, `node_waiting`, `edge_completed`, `graph_completed`, `graph_failed`, `graph_review_requested`.
- O Pipeline Mobile ViewModel agora inclui `execution_graph` como fonte comum para Mobile e Launcher.
- Launcher Pipeline renderiza Execution Graph, nodes, dependencias, artifacts e botoes Retry Node / Cancel Node.
- Mobile Pipeline mostra resumo do Execution Graph e adiciona acoes Retry node / Cancel node usando endpoints governados.

## Fluxo cooperativo

Um grafo cooperativo padrao contem:

1. `node_planner`
2. `node_executor`
3. `node_debugger`
4. `node_vision` quando o objetivo envolve Android/UI/visual/OCR
5. `node_ocr` quando o objetivo envolve Android/UI/visual/OCR
6. `node_review`
7. `node_memory`
8. `node_supervisor`
9. `node_final`

Executor, Debugger, Vision e OCR podem ficar prontos em paralelo apos o Planner. Review depende dos outputs paralelos. Memory produz candidatos, mas nao grava memoria diretamente. Supervisor valida. AIpinho finaliza.

## Endpoints

- `GET /api/v1/task-runs/{run_id}/execution-graph`
- `POST /api/v1/task-runs/{run_id}/execution-graph/cooperative`
- `GET /api/v1/task-runs/{run_id}/execution-graph/poll`
- `POST /api/v1/task-runs/{run_id}/execution-graph/nodes/{node_id}/start`
- `POST /api/v1/task-runs/{run_id}/execution-graph/nodes/{node_id}/complete`
- `POST /api/v1/task-runs/{run_id}/execution-graph/nodes/{node_id}/fail`
- `POST /api/v1/task-runs/{run_id}/execution-graph/nodes/{node_id}/retry`
- `POST /api/v1/task-runs/{run_id}/execution-graph/nodes/{node_id}/cancel`

## Arquivos alterados

- `src/aipinho/schemas/runtime/execution_graph.py`
- `src/aipinho/services/runtime/execution_graph_service.py`
- `src/aipinho/services/runtime/task_runtime_service.py`
- `src/aipinho/api/routers/task_runtime_router.py`
- `src/aipinho/services/mobile_view_models/pipeline_mobile_aggregator.py`
- `config/runtime/task_run_event_policy.yaml`
- `apps/launcher/ui/api/pipeline_client.py`
- `apps/launcher/ui/tabs/pipeline_tab.py`
- `apps/mobile/android/app/src/main/java/br/com/aipinho/mobile/network/TaskRuntimeClient.kt`
- `apps/mobile/android/app/src/main/java/br/com/aipinho/mobile/ui/screens/PipelineScreen.kt`
- `tests/integration/test_launcher_multi_agent_ui_contract.py`
- `apps/mobile/android/app/src/test/java/br/com/aipinho/mobile/PipelineApprovalActionContractTest.kt`

## Arquivos criados

- `tests/unit/test_multi_agent_execution_graph.py`
- `reports/sprint_n/final_report.md`
- `reports/sprint_n/final_report.json`

## Testes executados

- `python -m py_compile src\aipinho\schemas\runtime\execution_graph.py src\aipinho\services\runtime\execution_graph_service.py src\aipinho\services\runtime\task_runtime_service.py src\aipinho\api\routers\task_runtime_router.py src\aipinho\services\mobile_view_models\pipeline_mobile_aggregator.py`
- `python -m pytest tests\unit\test_multi_agent_execution_graph.py tests\unit\test_task_runtime_service.py tests\integration\test_launcher_multi_agent_ui_contract.py -q`
- `python -m pytest tests\unit\test_external_collaboration_layer.py tests\unit\test_real_delegation_runtime.py tests\unit\test_runtime_delegation_events.py -q`
- `.\gradlew.bat :app:testDebugUnitTest --tests br.com.aipinho.mobile.PipelineApprovalActionContractTest --tests br.com.aipinho.mobile.MultiAgentMobileUiContractTest`
- `.\gradlew.bat :app:assembleDebug`
- `powershell -ExecutionPolicy Bypass -File scripts\package_launcher_desktop.ps1`

## Resultados dos testes

- Python Sprint N + runtime/launcher: `25 passed`.
- Python delegacao Sprint M regressao: `9 passed`.
- Android UI contracts: `BUILD SUCCESSFUL`.
- Android assembleDebug: `BUILD SUCCESSFUL`.
- Launcher build: `BUILD SUCCESSFUL`.

## Smoke real

Backend reiniciado em `0.0.0.0:9088`.

Smoke executado:

1. Criado `TaskRun` pelo endpoint `/api/v1/task-runs`.
2. Criado grafo cooperativo via `/api/v1/task-runs/{run_id}/execution-graph/cooperative`.
3. Completado `node_planner`.
4. Poll do graph executado.

Resultado:

- `run_id`: `task_run_81f3e9ee065447c8b79dd999a3b71c0a`
- `graph_id`: `exec_graph_0899397c507c448dbcc47fb6ab1faba9`
- `graph_type`: `cooperative`
- `ready_nodes`: `node_executor,node_debugger,node_vision,node_ocr`
- `poll_status`: `ready`

## UX

Launcher atualizado em:

- `C:\Users\rafae\Desktop\AIpinhoLauncher.exe`

APK gerado em:

- `C:\Dev\AIpinho\apps\mobile\android\app\build\outputs\apk\debug\app-debug.apk`

Instalacao no celular fisico nao foi realizada nesta rodada porque o ADB retornou `no devices/emulators found`.

## Speaker Truth

O grafo registra `speakertruth` no nivel de node e de graph. Provider externo nao cria node, nao altera artifact registry, nao cria memoria, nao finaliza graph e nao substitui a autoridade da AIpinho.

## Riscos restantes

- O Sprint N implementa o contrato e o lifecycle do grafo cooperativo. A decomposicao inteligente automatica completa fica para o Sprint O.
- Os nodes ainda executam por contratos e endpoints governados; nao foi criado mesh P2P nem execucao soberana de provider.
- A decisao de quais memory candidates entram na memoria permanente segue fora do node, como previsto.

## Proximos passos

- Sprint O: Planner inteligente para decompor tarefas reais em grafos automaticamente.
- Sprint P: Registro plugavel de agentes especializados por capacidades/contratos, sem alterar o orquestrador.
- Fire Test 5: validar o ecossistema em projeto real, com planner, executor, debugger, vision, review, speaker truth e finalizacao pela AIpinho.

