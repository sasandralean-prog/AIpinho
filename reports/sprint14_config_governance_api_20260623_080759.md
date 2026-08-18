# Sprint 14 - Config Governance API

Data: 2026-06-23 08:07:59

## Veredito

READY_WITH_WARNINGS

O Sprint 14 foi implementado com API de governanca de configuracao protegida por token local para qualquer operacao mutavel. Leitura de status/effective policy fica disponivel para observabilidade; create/preview/approve/apply/cancel/rollback/reload exigem `Authorization: Bearer <local_token>`.

## Implementado

- Schemas:
  - `ConfigChangeRequest`
  - `ConfigChangePreview`
  - `ConfigApplyResult`
  - `ConfigBackup`
  - `ConfigChangeRecord`
- Service:
  - `ConfigGovernanceService`
- Router:
  - `config_governance_router`
- Fluxo:
  - create change
  - preview sanitizado com diff
  - approval request via ApprovalService
  - apply somente apos status approved
  - backup antes da escrita
  - reload/self-check
  - rollback por backup
  - falha de apply restaura backup

## Endpoints

- `GET /api/v1/config/effective-policy`
- `GET /api/v1/config/workspaces`
- `GET /api/v1/config/providers`
- `GET /api/v1/config/agents`
- `GET /api/v1/config/permissions`
- `POST /api/v1/config/changes`
- `GET /api/v1/config/changes`
- `GET /api/v1/config/changes/{change_id}`
- `POST /api/v1/config/changes/{change_id}/preview`
- `POST /api/v1/config/changes/{change_id}/approve`
- `POST /api/v1/config/changes/{change_id}/apply`
- `POST /api/v1/config/changes/{change_id}/cancel`
- `GET /api/v1/config/backups`
- `GET /api/v1/config/backups/{backup_id}`
- `POST /api/v1/config/rollback/{backup_id}`
- `POST /api/v1/config/reload`
- `GET /api/v1/config/health`

## Seguranca

- Mutacoes exigem token local.
- Segredos sao redigidos em diff/eventos.
- Apply exige change aprovado.
- Backup e criado antes de escrita.
- Reload/self-check falhos restauram backup.
- Missing provider opcional nao degrada o sistema.
- OpenAI disabled e tratado como estado configurado, nao como erro do sistema.

## Arquivos Alterados/Criados

- `src/aipinho/schemas/config_governance/config_change.py`
- `src/aipinho/schemas/config_governance/workspace_permission.py`
- `src/aipinho/schemas/config_governance/__init__.py`
- `src/aipinho/services/config_governance/config_governance_service.py`
- `src/aipinho/services/config_governance/workspace_permission_matrix_service.py`
- `src/aipinho/services/config_governance/__init__.py`
- `src/aipinho/api/routers/config_governance_router.py`
- `src/aipinho/api/routers/__init__.py`
- `tests/unit/test_config_governance_service.py`

## Validacoes

- `python -m py_compile` nos arquivos alterados: passou.
- `python -m pytest tests\unit\test_config_governance_service.py tests\unit\test_workspace_permission_matrix_service.py -q`: 17 passed.
- Import do app e listagem de rotas `/api/v1/config`: passou.
- Smoke read-only `ConfigGovernanceService.health()` e `effective_policy()`: passou.
- Smoke API com `TestClient`: `GET /api/v1/config/health` 200, `GET /api/v1/config/effective-policy` ok, `POST /api/v1/config/changes` sem token 401.

## Warnings

- A API mutavel foi protegida por token local. UIs precisam enviar bearer token para criar/aprovar/aplicar alteracoes de config.
- O apply real de config foi testado com `tmp_path`; nao foi aplicado contra configs reais neste sprint.
