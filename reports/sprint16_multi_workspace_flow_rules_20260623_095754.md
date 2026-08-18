# Sprint 16 - Multi-Workspace Flow Rules

Timestamp: 20260623_095754
Responsavel: Codex A
Projeto: AIpinho

## Objetivo

Implementar regras e planos governados para fluxos entre workspaces, usando a Permission Matrix como fonte de verdade e mantendo side effects atras de policy, approval e validacao.

## Entregas

- Criado schema `WorkspaceFlowRule`, `WorkspaceFlowPlan`, `WorkspaceFlowStep` e `WorkspaceFlowPlanRequest`.
- Criado `WorkspaceFlowService` para planejar, aprovar, negar e executar fluxos governados.
- Criado router `/api/v1/workspace-flows`.
- Registradas 10 rotas oficiais no app factory.
- Criados testes unitarios cobrindo allow, ask, deny, move seguro, git_push, download staging e eventos.

## Endpoints

- `GET /api/v1/workspace-flows/rules`
- `POST /api/v1/workspace-flows/rules`
- `GET /api/v1/workspace-flows/rules/{flow_id}`
- `PATCH /api/v1/workspace-flows/rules/{flow_id}`
- `POST /api/v1/workspace-flows/plan`
- `GET /api/v1/workspace-flows/plans/{flow_plan_id}`
- `POST /api/v1/workspace-flows/plans/{flow_plan_id}/approve`
- `POST /api/v1/workspace-flows/plans/{flow_plan_id}/deny`
- `POST /api/v1/workspace-flows/plans/{flow_plan_id}/execute`
- `GET /api/v1/workspace-flows/plans/by-run/{run_id}`

## Regras implementadas

- Source e target passam pela `WorkspacePermissionMatrixService`.
- Permission `denied` bloqueia o plano com reason code claro.
- Permission `ask` cria `ApprovalRequest` e deixa o plano em `pending_approval`.
- `move_file` e executado como copy + validacao de destino + delete de origem.
- `delete_file` nao ocorre antes de validacao do destino.
- `git_push` exige approval especifico e nao executa sem autorizacao.
- `download_to_staging` nao trata URL como workspace local e fica preparado para executor externo governado.
- Eventos locais registram operation, source/target, approval_id e status.

## Arquivos criados/alterados

- `src/aipinho/schemas/workspace_flows/workspace_flow.py`
- `src/aipinho/schemas/workspace_flows/__init__.py`
- `src/aipinho/services/workspace_flows/workspace_flow_service.py`
- `src/aipinho/services/workspace_flows/__init__.py`
- `src/aipinho/api/routers/workspace_flow_router.py`
- `src/aipinho/api/routers/__init__.py`
- `tests/unit/test_workspace_flow_service.py`

## Validacoes

- `python -m py_compile ...`: passed
- `python -m pytest tests\unit\test_workspace_flow_service.py tests\unit\test_mobile_view_model_service.py -q`: 12 passed
- App factory route registration: `workspace_flow_routes=10`, `config_routes=27`

## Warnings

- `download_to_staging` e `git_push` estao planejados/governados, mas a execucao real depende de executor externo governado.
- Endpoints mutaveis exigem token local.
- `git status` nao estava disponivel no diretorio atual porque `C:\Dev\AIpinho` nao foi detectado como worktree Git neste contexto.

## Veredito

READY_WITH_WARNINGS
