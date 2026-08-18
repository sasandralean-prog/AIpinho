# HOTFIX P0 - PermissionGrant Overcapture + Product Planning Readonly + Workspace Registry Query

Generated: 2026-06-26T06:53:48Z

## Verdict
PERMISSION_GRANT_OVERCAPTURE_HOTFIX_READY

## Root Causes
- ChatPermissionGrantService aceitava termos amplos de permissao sem checar negacoes ou intent explicito read-only.
- Perguntas sobre workspaces aprovados caiam em conversa/permissao generica em vez de rota canonica estruturada.
- Criacao de pasta fora da sandbox podia ficar em preview generico sem ApprovalRequest util.

## Changes
- ChatPermissionGrantService agora exige concessao positiva clara e ignora prompts com planejamento read-only/negacoes de grant/escrita/approval/config change.
- ChatOperationRouterService ganhou product_planning_readonly e workspace_permission_list.
- PermissionStatusResponseService pode responder como workspace_permission_list mantendo a mesma fonte configurada.
- ChatService ganhou resposta final para product_planning_readonly sem task/approval/grant/shell/write.
- filesystem_create_directory agora cria TaskDraft, TaskPreview e ApprovalRequest com plano executavel concreto quando policy exige ask.
- ExecutablePlanService, approval_lifecycle_policy, preview_policy e operation_contract_policy agora reconhecem create_directory como side effect governado aprovavel.

## Files Changed
- config/chat/chat_operation_routing_policy.yaml
- config/policies/approval_lifecycle_policy.yaml
- config/policies/operation_contract_policy.yaml
- config/policies/preview_policy.yaml
- src/aipinho/services/chat/chat_permission_grant_service.py
- src/aipinho/services/chat/chat_operation_router_service.py
- src/aipinho/services/chat/chat_service.py
- src/aipinho/services/chat/permission_status_response_service.py
- src/aipinho/services/orchestration/executable_plan_service.py
- tests/unit/test_chat_operation_router_service.py
- tests/unit/test_hotfix_approval_bootstrap_phase_resume.py

## Tests
- `python -m pytest tests\unit\test_chat_operation_router_service.py tests\unit\test_hotfix_approval_bootstrap_phase_resume.py -q`: 76 passed in 20.24s
- `python -m py_compile changed python services`: passed

## HTTP Smokes
- AIpinho - Fase 0A... product_planning_readonly: {'status': 'ok', 'operation_type': 'product_planning_readonly', 'message_type': 'assistant_final_answer', 'task_id': None, 'approval_id': None, 'first_line': 'PRODUCT_PLANNING_READONLY_READY'}
- Liste os workspaces aprovados para escrita.: {'status': 'ok', 'operation_type': 'workspace_permission_list', 'message_type': 'assistant_final_answer', 'first_line': 'Permissoes atuais da AIpinho:'}
- Crie uma pasta chamada AIpinhoStudioMobile dentro de C:\Users\rafae\Documents\AIpinhoTestes.: {'status': 'pending_approval', 'operation_type': 'filesystem_create_directory', 'message_type': 'task_preview', 'approval_id': 'approval_4ebb1718488a49ed94e02d8518911d58', 'first_line': 'DIRECTORY_CREATION_PENDING_APPROVAL', 'folder_created_before_approval': False, 'cleanup': 'approval denied after smoke'}

## Remaining Risks
- Execucao pos-approval de create_directory deve ser validada em fluxo dedicado; este hotfix certificou criacao de preview/approval e ausencia de escrita antes do approval.
- A resposta textual de product planning e propositalmente generica; um sprint futuro pode conectar LLM real readonly para enriquecer o plano sem side effects.