# AIpinho Engineering Evolution - Tool Governance Closure

Data: 2026-07-02

Veredito: TOOL_GOVERNANCE_CLOSURE_READY

## Objetivo

Fechar a exigencia transversal do Engineering Evolution Program:

```text
Intent -> Planner -> Contract -> Capability -> Policy -> Approval -> Tool Router -> Execution -> Validation -> Artifacts -> Report
```

A correcao foi implementada como trilha auditavel derivada do `TaskRun`, sem alterar o comportamento de runtime, sem bypass de approval/policy e sem criar regra especifica para Fire Test, projeto, path ou prompt.

## Arquivos Alterados

- `C:\Dev\AIpinho\src\aipinho\schemas\runtime\tool_governance.py`
- `C:\Dev\AIpinho\src\aipinho\services\runtime\tool_governance_service.py`
- `C:\Dev\AIpinho\src\aipinho\services\runtime\task_runtime_service.py`
- `C:\Dev\AIpinho\tests\unit\test_tool_governance_service.py`
- `C:\Dev\AIpinho\reports\engineering_evolution\engineering_evolution_g_l_consolidated_report.md`
- `C:\Dev\AIpinho\reports\engineering_evolution\engineering_evolution_g_l_consolidated_report.json`

## Implementacao

Foi criado `ToolGovernanceService`, que materializa uma `ToolGovernanceTrail` e uma `ToolGovernanceAudit` para cada `TaskRun`.

Estagios auditados:

- intent
- planner
- contract
- capability
- policy
- approval
- tool_router
- execution
- validation
- artifacts
- report

O servico usa evidencias existentes:

- `intent_map`
- `TaskRunPlan`
- `contract_type`
- `runtime_profile`
- `requested_actions`
- `capabilities_required`
- `policy_snapshot`
- `approval_id`
- `ExecutionGraph`
- `worker_route`
- `TaskRunResult`
- `validation`
- `completion`
- `outputs`

## Regras De Auditoria

- Approval pode ser `not_required` quando a policy nao exige approval para as actions do run.
- Validation, artifacts e report podem ficar `pending` enquanto a task ainda nao chegou a estado terminal.
- Runs bloqueadas marcam `execution` ou `validation` como `blocked`.
- Se a policy exige approval e nao ha `approval_id`, o stage `approval` fica `blocked`.
- Uma trilha so passa se nao houver estagios obrigatorios ausentes ou bloqueados.

## Smoke Vivo

Comando executado via Python local:

```text
TaskRun criado: task_run_942abbc0de34425b80710ba6ec41faaf
ToolGovernanceTrail: ready
ToolGovernanceAudit: passed
```

Checkpoints:

```text
intent:present
planner:present
contract:present
capability:present
policy:present
approval:not_required
tool_router:present
execution:present
validation:pending
artifacts:pending
report:pending
```

## Testes

Novos testes:

- `test_tool_governance_trail_tracks_canonical_stage_order`
- `test_tool_governance_fails_when_policy_is_missing`
- `test_tool_governance_blocks_when_approval_required_but_not_linked`
- `test_tool_governance_uses_execution_graph_worker_routes`
- `test_task_runtime_service_exposes_tool_governance_trail`

Suite focada final:

```text
69 passed in 70.29s
```

Comando:

```powershell
python -m pytest tests/unit/test_tool_governance_service.py tests/unit/test_engineering_autopilot_service.py tests/unit/test_continuous_runtime_service.py tests/unit/test_evidence_engine_service.py tests/unit/test_worker_registry_service.py tests/unit/test_task_runtime_service.py tests/unit/test_hotfix_policy_kernel_approval_gate.py tests/governance/test_g21_readonly_analysis_intent.py tests/governance/test_lifecycle_core.py tests/governance/test_g24_preview_quality_gate.py -q
```

## Limites Restantes

- O fechamento atual e um contrato/servico interno; ainda nao foi adicionada rota publica dedicada.
- A trilha audita o fluxo; ela ainda nao bloqueia automaticamente todas as decisoes de ferramenta.
- A exposicao em Mobile/Launcher/Debugger pode ser adicionada em sprint proprio sem duplicar logica.

## Hardcode Check

- Sem regra por path.
- Sem regra por projeto.
- Sem regra por filename.
- Sem rota especifica de teste.
- Sem fallback silencioso.
- Sem bypass de approval/policy.

## Rollback

Rollback seguro:

1. Remover `tool_governance.py`.
2. Remover `tool_governance_service.py`.
3. Remover import, inicializacao e metodo `build_tool_governance_trail` em `task_runtime_service.py`.
4. Remover `test_tool_governance_service.py`.
5. Reexecutar a suite focada anterior.

## Conclusao

TOOL_GOVERNANCE_CLOSURE_READY

O runtime agora possui uma trilha canonica auditavel para provar que uma execucao de ferramenta passou por intent, planner, contract, capability, policy, approval, router, execution, validation, artifacts e report, respeitando estados `not_required` e `pending` quando aplicaveis.
