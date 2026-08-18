# AIpinho Engineering Evolution - Bloco G

Data: 2026-07-02

Veredito: BLOCK_G_EXECUTION_GRAPH_READY

## Objetivo

Implementar a base canonica de Execution Graph para transformar TaskRun linear em DAG auditavel, sem criar hardcode de workload e sem substituir o runtime por uma rota paralela.

## Evidencias Consultadas

- Relatorios de governanca Blocos A-F em `reports/governance_*`.
- Relatorios Fire Test em `reports/fire_tests`.
- Hotfixes recentes de approval/runtime e regressoes em `tests/governance` e `tests/unit`.
- Codigo runtime atual em `src/aipinho/services/runtime`.

## Arquitetura Implementada

Novos contratos:

- `ExecutionGraph`
- `ExecutionNode`
- `ExecutionEdge`
- `ExecutionContext`
- `ExecutionLifecycle`
- `ExecutionCheckpoint`
- `ExecutionResume`
- `ExecutionCancel`
- `ExecutionMetrics`

Novo servico:

- `ExecutionGraphService`
- `DependencyResolver`
- `ExecutionScheduler`

Integracao:

- Toda `TaskRun` passa a possuir `execution_graph`.
- O grafo e criado a partir de `TaskRunPlan`.
- O loop supervisionado atualiza nos quando steps iniciam/finalizam.
- O endpoint read-only `GET /api/v1/task-runs/{run_id}/execution-graph` expoe o DAG.
- O Debugger mobile renderiza card de Execution Graph para `trace_id` de `task_run_*`.

## Decisoes

- O runtime existente continua executando steps, mas o estado oficial agora materializa DAG.
- Dependencias sao resolvidas por categoria de acao: contexto, side effect, validacao e relatorio.
- `permission_requires_approval:*` com `approval_id` ligado agora e tratado como `waiting_input`, nao hard block.
- O grafo nao executa bypass; ele observa e organiza execucao governada.

## Arquivos Alterados

- `src/aipinho/schemas/runtime/execution_graph.py`
- `src/aipinho/schemas/runtime/task_run.py`
- `src/aipinho/services/runtime/execution_graph_service.py`
- `src/aipinho/services/runtime/task_runtime_service.py`
- `src/aipinho/services/runtime/supervised_execution_loop.py`
- `src/aipinho/api/routers/task_runtime_router.py`
- `src/aipinho/services/mobile_view_models/debugger_mobile_aggregator.py`
- `tests/unit/test_task_runtime_service.py`

## Testes Executados

Comando:

```powershell
python -m py_compile C:\Dev\AIpinho\src\aipinho\schemas\runtime\execution_graph.py C:\Dev\AIpinho\src\aipinho\schemas\runtime\task_run.py C:\Dev\AIpinho\src\aipinho\services\runtime\execution_graph_service.py C:\Dev\AIpinho\src\aipinho\services\runtime\task_runtime_service.py C:\Dev\AIpinho\src\aipinho\services\runtime\supervised_execution_loop.py C:\Dev\AIpinho\src\aipinho\api\routers\task_runtime_router.py C:\Dev\AIpinho\src\aipinho\services\mobile_view_models\debugger_mobile_aggregator.py C:\Dev\AIpinho\tests\unit\test_task_runtime_service.py
python -m pytest tests/unit/test_task_runtime_service.py tests/unit/test_hotfix_policy_kernel_approval_gate.py tests/governance/test_g21_readonly_analysis_intent.py tests/governance/test_lifecycle_core.py tests/governance/test_g24_preview_quality_gate.py -q
python -c "from aipinho.app_factory import create_app; app=create_app(); print(app.title); print(len(app.routes))"
```

Resultado:

```text
44 passed
AIpinho
942
```

## Smoke em Backend Vivo

Backend reiniciado pelo script canonico:

```text
C:\Dev\AIpinho\scripts\dev\stop_aipinho_9088.ps1
C:\Dev\AIpinho\scripts\dev\start_aipinho_9088.ps1
```

Resultado:

```text
AIpinho API started.
PID: 50904
Bind: 0.0.0.0:9088
Health: {"status":"ok","service":"AIpinho","version":"0.1.0","runtime":"local"}
```

Smoke criado:

```text
run_id: task_run_6afe37b2d331449b9f10f6b407bf2203
graph_id: exec_graph_44bedfda5ce148c296e3107c160d1675
endpoint: GET /api/v1/task-runs/task_run_6afe37b2d331449b9f10f6b407bf2203/execution-graph
endpoint_status: ok
nodes: 3
edges: 1
checkpoints: 1
graph_status: ready
```

## Regression Candidates

- Toda TaskRun criada deve conter `execution_graph`.
- ExecutionGraph deve ser aciclico.
- Runtime deve atualizar nos para `completed` quando steps completam.
- Approval com `approval_id` e `permission_requires_approval:*` deve aguardar input, nao bloquear seco.
- Endpoint de graph deve ser read-only e nao executar side effects.

## Rollback

Rollback seguro:

1. Remover campo `execution_graph` de `TaskRun`.
2. Remover chamadas a `ExecutionGraphService` em `TaskRuntimeService`.
3. Remover atualizacoes de graph em `SupervisedExecutionLoop`.
4. Remover endpoint `/task-runs/{run_id}/execution-graph`.
5. Remover card de Debugger mobile.
6. Remover testes adicionados do ExecutionGraph.

Como o grafo e observacional e persistido dentro da TaskRun, o rollback nao exige migracao de dados destrutiva. Runs antigas sem graph continuam validas porque o campo e opcional.

## Limitacoes

- O scheduler ainda nao executa multiplos nos em paralelo.
- O executor atual ainda percorre `run.plan.steps`; o DAG e a fonte observavel e de readiness, nao o executor paralelo final.
- Blocos H-L devem reutilizar `ExecutionGraph` em vez de criar novos formatos de missao.

## Proximo Bloco

Bloco H pode iniciar agora, porque o smoke endpoint do Bloco G e a validacao de backend vivo foram concluidos.
