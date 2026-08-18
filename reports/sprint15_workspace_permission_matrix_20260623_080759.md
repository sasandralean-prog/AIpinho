# Sprint 15 - Workspace Registry e Permission Matrix

Data: 2026-06-23 08:07:59

## Veredito

READY_WITH_WARNINGS

O Sprint 15 foi implementado como uma matriz de permissoes configuravel sobre `config/workspaces/workspace_registry.yaml`, mantendo compatibilidade com entradas antigas do registry. O runtime guard agora consulta a matriz para decisoes por permissao e path.

## Implementado

- Roles suportados:
  - `source_readonly`
  - `target_mutable`
  - `external_inbox`
  - `artifact_output`
  - `system_mutable`
  - `protected`
  - `temp_staging`
  - `forbidden`
- Permissoes suportadas:
  - `read_file`
  - `list_files`
  - `create_file`
  - `modify_file`
  - `apply_patch`
  - `artifact_create`
  - `copy_from`
  - `copy_to`
  - `move_from`
  - `move_to`
  - `delete_file`
  - `shell_readonly`
  - `shell_build`
  - `shell_test`
  - `script_execution`
  - `network_download`
  - `git_commit`
  - `git_push`
- Valores:
  - `allowed`
  - `ask`
  - `denied`
- Decisao:
  - longest-path match
  - deny override por papel mais restritivo em mesmo nivel
  - disabled workspace nega
  - unregistered workspace nega
  - side effects ficam `ask` ou `denied` por default

## Runtime

`TaskRunGuard` agora consulta `WorkspacePermissionMatrixService` para cada `requested_action` com workspace definido.

Reason codes emitidos:

- `workspace_not_registered`
- `workspace_disabled`
- `permission_allowed`
- `permission_requires_approval`
- `permission_denied`

Quando a permissao esta em `ask`, a task exige approval pendente; se o approval ja estiver aprovado, o gate nao mantem o bloqueio da matriz.

## Endpoints

- `GET /api/v1/config/workspaces`
- `GET /api/v1/config/workspaces/{workspace_id}`
- `POST /api/v1/config/workspaces`
- `PATCH /api/v1/config/workspaces/{workspace_id}`
- `POST /api/v1/config/workspaces/{workspace_id}/enable`
- `POST /api/v1/config/workspaces/{workspace_id}/disable`
- `GET /api/v1/config/workspace-roles`
- `GET /api/v1/config/permission-matrix`
- `POST /api/v1/config/workspaces/{workspace_id}/permissions`
- `POST /api/v1/config/workspaces/preview`
- `GET /api/v1/config/effective-policy`

## Arquivos Alterados/Criados

- `src/aipinho/schemas/config_governance/workspace_permission.py`
- `src/aipinho/services/config_governance/workspace_permission_matrix_service.py`
- `src/aipinho/schemas/policy/workspace_role_contract.py`
- `src/aipinho/services/policy_kernel/workspace_role_contract_service.py`
- `src/aipinho/services/runtime/task_run_guard.py`
- `src/aipinho/api/routers/config_governance_router.py`
- `tests/unit/test_workspace_permission_matrix_service.py`

## Validacoes

- `python -m py_compile` nos arquivos alterados: passou.
- `python -m pytest tests\unit\test_config_governance_service.py tests\unit\test_workspace_permission_matrix_service.py -q`: 17 passed.
- App import/listagem de rotas: passou.
- Effective policy real retornou `longest_path_then_deny_override`.
- Smoke API confirmou leitura liberada e mutacao sem token bloqueada com 401.

## Warnings

- Defaults foram deliberadamente conservadores para evitar liberação silenciosa de write/shell.
- Mudancas mutaveis no registry via API exigem token local e approval/apply pelo fluxo de config governance.
- A matriz entrou no `TaskRunGuard`; outros services especificos podem continuar usando guards proprios ate migrarem para a matriz.
