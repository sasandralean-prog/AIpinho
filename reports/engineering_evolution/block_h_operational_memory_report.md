# AIpinho Engineering Evolution - Bloco H

Data: 2026-07-02

Veredito: BLOCK_H_OPERATIONAL_MEMORY_READY

## Objetivo

Separar memoria conversacional/curada de memoria operacional e registrar automaticamente decisoes, execucoes, falhas, recuperacoes, estrategias e aprendizados derivados de `TaskRun` e `ExecutionGraph`.

## Evidencias Consultadas

- `src/aipinho/schemas/memory/*`
- `src/aipinho/services/memory/*`
- `src/aipinho/services/runtime/task_runtime_service.py`
- `src/aipinho/services/runtime/supervised_execution_loop.py`
- `reports/engineering_evolution/block_g_execution_graph_report.md`

## Arquitetura Implementada

Novos contratos:

- `OperationalMemoryRecord`
- `OperationalMemoryEvidence`
- `OperationalMemorySnapshot`
- `DecisionMemory`
- `ExecutionMemory`
- `FailureMemory`
- `RecoveryMemory`
- `StrategyMemory`
- `LearningMemory`

Novo servico:

- `OperationalMemoryService`

Separacao de responsabilidades:

- Memoria curada/conversacional continua em `curated_memory`, `memory_candidate` e fluxos de approval existentes.
- Memoria operacional fica em `data/runtime/operational_memory`.
- A memoria operacional e observacional: ela registra o que o runtime decidiu/fez, sem virar approval automatico nem RAG global.

## Integracao

- `TaskRuntimeService.create_run()` captura snapshot operacional no evento `task_run_created`.
- `TaskRuntimeService.start()` captura snapshot operacional no evento `task_run_finished`.
- `TaskRuntimeService.process_queue()` captura snapshot operacional no evento `task_run_finished`.
- Cada snapshot e salvo por `run_id`, evitando mistura com chats ou memorias globais.

## Arquivos Alterados

- `src/aipinho/schemas/memory/operational_memory.py`
- `src/aipinho/services/memory/operational_memory_service.py`
- `src/aipinho/services/runtime/task_runtime_service.py`
- `tests/conftest.py`
- `tests/unit/test_task_runtime_service.py`

## Testes Executados

Comando:

```powershell
python -m py_compile C:\Dev\AIpinho\src\aipinho\schemas\memory\operational_memory.py C:\Dev\AIpinho\src\aipinho\services\memory\operational_memory_service.py C:\Dev\AIpinho\src\aipinho\services\runtime\task_runtime_service.py C:\Dev\AIpinho\tests\conftest.py C:\Dev\AIpinho\tests\unit\test_task_runtime_service.py
python -m pytest tests/unit/test_task_runtime_service.py tests/unit/test_hotfix_policy_kernel_approval_gate.py tests/governance/test_g21_readonly_analysis_intent.py tests/governance/test_lifecycle_core.py tests/governance/test_g24_preview_quality_gate.py -q
python -c "from aipinho.app_factory import create_app; app=create_app(); print(app.title); print(len(app.routes))"
```

Resultado:

```text
47 passed
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
PID: 46604
Bind: 0.0.0.0:9088
Health: {"status":"ok","service":"AIpinho","version":"0.1.0","runtime":"local"}
```

Smoke criado:

```text
run_id: task_run_154e3de1d73f48a1b6e02a8d1a9d072a
memory_path: C:\Dev\AIpinho\data\runtime\operational_memory\task_run_154e3de1d73f48a1b6e02a8d1a9d072a.json
records: 3
types: decision,strategy,execution
```

## Regression Candidates

- Toda `TaskRun` criada deve gerar memoria operacional minima: `decision`, `strategy`, `execution`.
- TaskRun finalizada deve gerar `learning`.
- TaskRun bloqueada/falha/cancelada deve gerar `failure` e `recovery`.
- Memoria operacional nao deve usar ids nem stores de memoria curada/conversacional.
- Memoria operacional deve citar evidencia de `task_run`, `task_run_plan` e `execution_graph` quando disponivel.

## Rollback

Rollback seguro:

1. Remover `OperationalMemoryService` do `TaskRuntimeService`.
2. Remover `src/aipinho/services/memory/operational_memory_service.py`.
3. Remover `src/aipinho/schemas/memory/operational_memory.py`.
4. Remover testes adicionados de operational memory.
5. Opcionalmente arquivar `data/runtime/operational_memory`.

Como a memoria operacional e observacional, o rollback nao exige migracao destrutiva de TaskRun nem altera os stores de memoria curada.

## Limitacoes

- A memoria operacional ainda nao participa da selecao de estrategia antes de planejar uma nova TaskRun.
- Nao ha endpoint publico especifico para consultar operational memory; o servico ja existe para uso interno e testes.
- O Bloco I deve consumir `ExecutionGraph` e pode passar a usar `OperationalMemory` para roteamento de workers sem criar um store paralelo.

## Proximo Bloco

Bloco I pode iniciar agora, porque o Bloco H tem contratos, integracao runtime, testes, smoke vivo e rollback documentado.
