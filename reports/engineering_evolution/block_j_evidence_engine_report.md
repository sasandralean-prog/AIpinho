# AIpinho Engineering Evolution - Bloco J

Data: 2026-07-02

Veredito: BLOCK_J_EVIDENCE_ENGINE_READY

## Objetivo

Criar uma camada canonica de Evidence Engine para que decisoes importantes possam nascer de evidencia auditavel, seguindo o fluxo: Evidence -> Decision -> Execution -> Validation -> Evidence.

## Evidencias Consultadas

- `src/aipinho/schemas/reports/evidence.py`
- `src/aipinho/services/reports/evidence_index_service.py`
- `src/aipinho/services/validation/evidence_compliance_validator.py`
- `src/aipinho/services/runtime/task_runtime_service.py`
- `reports/engineering_evolution/block_g_execution_graph_report.md`
- `reports/engineering_evolution/block_h_operational_memory_report.md`
- `reports/engineering_evolution/block_i_multi_worker_runtime_report.md`

## Arquitetura Implementada

Novos contratos runtime:

- `EvidenceItem`
- `EvidenceIndex`
- `EvidenceScore`
- `EvidenceReasoning`
- `EvidenceBackedDecision`
- `DecisionAudit`

Novos servicos:

- `EvidenceCollector`
- `EvidenceIndexService`
- `EvidenceScoreService`
- `EvidenceReasoner`
- `DecisionBuilder`
- `DecisionAuditService`
- `EvidenceEngineService`

## Integracao

- `EvidenceCollector` coleta evidencia de `TaskRun`, `TaskRunPlan`, `ExecutionGraph`, `ExecutionNode`, `OperationalMemory` e `PolicySnapshot`.
- `TaskRuntimeService.build_evidence_decision()` cria decisoes auditaveis a partir de uma run existente.
- Decisoes sem evidencias obrigatorias ficam `blocked`.
- Auditoria falha quando faltam evidencias requeridas.

## Arquivos Alterados

- `src/aipinho/schemas/runtime/evidence_engine.py`
- `src/aipinho/services/runtime/evidence_engine_service.py`
- `src/aipinho/services/runtime/task_runtime_service.py`
- `tests/unit/test_evidence_engine_service.py`

## Testes Executados

Comando:

```powershell
python -m py_compile C:\Dev\AIpinho\src\aipinho\schemas\runtime\evidence_engine.py C:\Dev\AIpinho\src\aipinho\services\runtime\evidence_engine_service.py C:\Dev\AIpinho\src\aipinho\services\runtime\task_runtime_service.py C:\Dev\AIpinho\tests\unit\test_evidence_engine_service.py
python -m pytest tests/unit/test_evidence_engine_service.py tests/unit/test_worker_registry_service.py tests/unit/test_task_runtime_service.py tests/unit/test_hotfix_policy_kernel_approval_gate.py tests/governance/test_g21_readonly_analysis_intent.py tests/governance/test_lifecycle_core.py tests/governance/test_g24_preview_quality_gate.py -q
python -c "from aipinho.app_factory import create_app; app=create_app(); print(app.title); print(len(app.routes))"
```

Resultado:

```text
56 passed
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
PID: 54116
Bind: 0.0.0.0:9088
Health: {"status":"ok","service":"AIpinho","version":"0.1.0","runtime":"local"}
```

Smoke criado:

```text
run_id: task_run_f574f22b316741b6a1ffc7a76f698e7a
decision_status: accepted
audit_status: passed
score: 1.0
evidence_count: 10
missing_required_evidence: []
```

## Regression Candidates

- Evidence Engine deve coletar TaskRun, TaskRunPlan, ExecutionGraph e OperationalMemory.
- Decisao com evidencias obrigatorias suficientes deve ser `accepted` e auditoria `passed`.
- Decisao sem evidencia requerida deve ser `blocked` e auditoria `failed`.
- Score nao pode mascarar missing evidence.
- `TaskRuntimeService` deve expor decisao auditavel para uma run.

## Rollback

Rollback seguro:

1. Remover `EvidenceEngineService` do `TaskRuntimeService`.
2. Remover `src/aipinho/services/runtime/evidence_engine_service.py`.
3. Remover `src/aipinho/schemas/runtime/evidence_engine.py`.
4. Remover testes de evidence engine.

Como o Bloco J e observacional/decisional e nao executa side effects, rollback nao exige migracao de TaskRun.

## Limitacoes

- O Evidence Engine ainda nao bloqueia todos os pontos de decisao do sistema; ele oferece o caminho canonico para os proximos blocos conectarem.
- Ainda nao ha endpoint publico dedicado para Evidence Engine.
- Bloco K deve usar Evidence Engine para alimentar runtime continuo e evitar loops sem evidencia.

## Proximo Bloco

Bloco K pode iniciar agora, porque o Bloco J tem contratos, servicos, integracao runtime, testes, smoke vivo e rollback documentado.
