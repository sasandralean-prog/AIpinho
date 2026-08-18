# AIpinho Engineering Evolution - Bloco L

Data: 2026-07-02

Veredito: BLOCK_L_ENGINEERING_AUTOPILOT_READY

## Objetivo

Transformar o usuario em supervisor por meio de missoes governadas com lifecycle, checkpoint, review, resume, report, dashboard, approval e decision log.

## Arquitetura Implementada

Novos contratos:

- `EngineeringMission`
- `MissionLifecycle`
- `MissionCheckpoint`
- `MissionReview`
- `MissionResume`
- `MissionReport`
- `MissionDashboard`
- `MissionApproval`
- `DecisionLogEntry`

Novo servico:

- `EngineeringAutopilotService`

## Integracao

- `TaskRuntimeService.create_engineering_mission_from_run()` cria uma missao supervisionada a partir de uma `TaskRun`.
- A missao usa `ContinuousRuntimeService` para definir status e proxima acao.
- A missao grava `DecisionLogEntry` obrigatorio com reason, evidence, alternatives, chosen option, rejected options, impact, risk, rollback, worker, contracts, capabilities, validation e timestamp.
- Dashboard e report sao gerados automaticamente na missao.
- Missoes sao persistidas em `data/runtime/engineering_missions`.

## Arquivos Alterados

- `src/aipinho/schemas/runtime/engineering_autopilot.py`
- `src/aipinho/services/runtime/engineering_autopilot_service.py`
- `src/aipinho/services/runtime/task_runtime_service.py`
- `tests/conftest.py`
- `tests/unit/test_engineering_autopilot_service.py`

## Testes Executados

Comando:

```powershell
python -m py_compile C:\Dev\AIpinho\src\aipinho\schemas\runtime\engineering_autopilot.py C:\Dev\AIpinho\src\aipinho\services\runtime\engineering_autopilot_service.py C:\Dev\AIpinho\src\aipinho\services\runtime\task_runtime_service.py C:\Dev\AIpinho\tests\unit\test_engineering_autopilot_service.py
python -m pytest tests/unit/test_engineering_autopilot_service.py tests/unit/test_continuous_runtime_service.py tests/unit/test_evidence_engine_service.py tests/unit/test_worker_registry_service.py tests/unit/test_task_runtime_service.py tests/unit/test_hotfix_policy_kernel_approval_gate.py tests/governance/test_g21_readonly_analysis_intent.py tests/governance/test_lifecycle_core.py tests/governance/test_g24_preview_quality_gate.py -q
python -c "from aipinho.app_factory import create_app; app=create_app(); print(app.title); print(len(app.routes))"
```

Resultado:

```text
64 passed
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
PID: 53436
Bind: 0.0.0.0:9088
Health: {"status":"ok","service":"AIpinho","version":"0.1.0","runtime":"local"}
```

Smoke criado:

```text
run_id: task_run_780994238546439b9955b5742b46dae5
mission_id: engineering_mission_caa4f28f1c2e4b58b9c9698c59be3447
mission_status: running
stage: continuation
run_count: 1
decision_log: 2
reports: 1
dashboard_run_count: 1
dashboard_evidence_count: 3
```

## Regression Candidates

- Missao criada deve registrar decision log inicial.
- Missao anexada a run deve atualizar lifecycle, dashboard, reviews e reports.
- Decision log deve conter todos os campos obrigatorios.
- Missao bloqueada deve indicar `surface_block_reason`.
- Missao nao executa side effects fora do runtime governado.

## Rollback

Rollback seguro:

1. Remover `EngineeringAutopilotService` do `TaskRuntimeService`.
2. Remover `src/aipinho/services/runtime/engineering_autopilot_service.py`.
3. Remover `src/aipinho/schemas/runtime/engineering_autopilot.py`.
4. Remover testes de engineering autopilot.
5. Opcionalmente arquivar `data/runtime/engineering_missions`.

Como o Bloco L cria uma camada de missao supervisionada e nao altera executor/policy, rollback nao exige migracao destrutiva de TaskRun.

## Limitacoes

- Ainda nao ha endpoint publico especifico para missoes.
- A missao supervisiona e organiza; a automacao fisica continua dependendo do runtime governado existente.
- UI mobile/launcher dedicada para MissionDashboard fica como proximo passo.

## Fechamento

Com Blocos G-L, a AIpinho passa a ter base de Execution Graph, Operational Memory, Worker Registry, Evidence Engine, Continuous Runtime e Engineering Autopilot sem criar rotas ou regras especificas de workload.
