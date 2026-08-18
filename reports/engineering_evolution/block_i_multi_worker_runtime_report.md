# AIpinho Engineering Evolution - Bloco I

Data: 2026-07-02

Veredito: BLOCK_I_MULTI_WORKER_RUNTIME_READY

## Objetivo

Substituir o roteamento monolitico/hardcoded de steps por workers especializados com contratos proprios, roteamento dinamico e comunicacao via contratos.

## Evidencias Consultadas

- `reports/engineering_evolution/block_g_execution_graph_report.md`
- `reports/engineering_evolution/block_h_operational_memory_report.md`
- `src/aipinho/services/runtime/execution_graph_service.py`
- `src/aipinho/schemas/runtime/execution_graph.py`

## Arquitetura Implementada

Novos contratos:

- `WorkerContract`
- `WorkerRouteDecision`
- `WorkerRegistrySnapshot`

Novo servico:

- `WorkerRegistryService`

Nova config:

- `config/runtime/worker_registry.yaml`

Workers registrados:

- `ArchitectWorker`
- `PlannerWorker`
- `ResearchWorker`
- `ReviewerWorker`
- `ImplementationWorker`
- `ValidationWorker`
- `SecurityWorker`
- `DocumentationWorker`
- `ReportingWorker`

## Integracao

- `ExecutionGraphService` agora usa `WorkerRegistryService`.
- Cada `ExecutionNode` recebe `worker` vindo do contrato.
- Cada node guarda `worker_route` em `validation_gate`, com `decision_id`, `matched_by`, `reason`, `capabilities` e `output_contracts`.
- O roteamento por `action`, `keyword` e `default_worker` substitui o bloco antigo de `if` fixo dentro do grafo.

## Arquivos Alterados

- `config/runtime/worker_registry.yaml`
- `src/aipinho/schemas/runtime/worker_contract.py`
- `src/aipinho/services/runtime/worker_registry_service.py`
- `src/aipinho/services/runtime/execution_graph_service.py`
- `tests/unit/test_worker_registry_service.py`
- `tests/unit/test_task_runtime_service.py`

## Testes Executados

Comando:

```powershell
python -m py_compile C:\Dev\AIpinho\src\aipinho\schemas\runtime\worker_contract.py C:\Dev\AIpinho\src\aipinho\services\runtime\worker_registry_service.py C:\Dev\AIpinho\src\aipinho\services\runtime\execution_graph_service.py C:\Dev\AIpinho\tests\unit\test_worker_registry_service.py C:\Dev\AIpinho\tests\unit\test_task_runtime_service.py
python -m pytest tests/unit/test_worker_registry_service.py tests/unit/test_task_runtime_service.py tests/unit/test_hotfix_policy_kernel_approval_gate.py tests/governance/test_g21_readonly_analysis_intent.py tests/governance/test_lifecycle_core.py tests/governance/test_g24_preview_quality_gate.py -q
python -c "from aipinho.app_factory import create_app; app=create_app(); print(app.title); print(len(app.routes))"
```

Resultado:

```text
52 passed
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
PID: 50868
Bind: 0.0.0.0:9088
Health: {"status":"ok","service":"AIpinho","version":"0.1.0","runtime":"local"}
```

Smoke criado:

```text
run_id: task_run_80b4335361cf4672a9107308c52fd319
graph_id: exec_graph_3cdce531f1d14519ae4045eaa534e0e3
workers: ValidationWorker,PlannerWorker,PlannerWorker
route_decisions: 3
nodes: 3
```

## Regression Candidates

- Registry deve carregar 9 workers ativos.
- Todos os workers devem comunicar via contratos.
- Nenhum worker deve depender de implementacao interna de peers.
- `write_files` deve rotear para `ImplementationWorker`.
- `run_command` deve rotear para `SecurityWorker`.
- Steps desconhecidos devem cair no `default_worker`.
- Todo node do ExecutionGraph deve ter `worker_route`.

## Rollback

Rollback seguro:

1. Remover `WorkerRegistryService`.
2. Remover `WorkerContract` e `WorkerRouteDecision`.
3. Remover `config/runtime/worker_registry.yaml`.
4. Restaurar o roteamento interno anterior de `_worker_for_step` no `ExecutionGraphService`.
5. Remover testes de worker registry.

Como o Bloco I altera apenas roteamento e anotacao de nodes, o rollback nao exige migracao de TaskRun.

## Limitacoes

- Os workers ainda sao contratos e rotas de especializacao, nao processos paralelos independentes.
- A execucao fisica continua no loop supervisionado atual.
- Blocos seguintes devem transformar esses contratos em execucao concorrente/continua sem criar outro registry paralelo.

## Proximo Bloco

Bloco J pode iniciar agora, porque o Bloco I tem contratos, config, roteamento dinamico, testes, smoke vivo e rollback documentado.
