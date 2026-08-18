# HOTFIX - Router Project Bootstrap

Generated: 2026-06-26T06:10:56Z

## Verdict
ROUTER_PROJECT_BOOTSTRAP_HOTFIX_READY

## Root Cause
- O router avaliava session_diagnostic por termos operacionais comuns como diagnostico, preview e approval sem exigir pedido explicito de diagnostico da sessao.
- A nova regra de project_bootstrap estava inicialmente capturando prompts read-only de relatorio/plano; a prioridade foi ajustada para preservar workspace_readonly_audit_report antes do bootstrap.
- O contrato de bootstrap interpretava "nao escreva arquivos agora" como proibicao absoluta de escrita, bloqueando preview/approval; agora esse fluxo cria contrato neutro de pre-approval e preserva escrita futura apenas apos approval.

## Changes
- Adicionada operacao configuravel project_bootstrap em config/chat/chat_operation_routing_policy.yaml.
- Adicionado alias project_bootstrap -> project_generation em config/chat/canonical_operation_map.yaml.
- Atualizado ChatOperationRouterService para priorizar bootstrap governado sobre session_diagnostic, mantendo diagnostico apenas quando explicito.
- Adicionado runtime profile project_bootstrap com outcomes pre-approval sem exigir patch_result antes da aprovacao.
- Atualizado ChatService para gerar pending approval de PROJECT_BOOTSTRAP_PENDING_APPROVAL com TaskDraft/TaskPreview/ApprovalRequest e sem escrita antes da aprovacao.
- Adicionadas regressoes para bootstrap, safety check como step interno, diagnostico explicito, outcomes pre-approval e no old approval reuse.

## Files Changed
- config/chat/canonical_operation_map.yaml
- config/chat/chat_operation_routing_policy.yaml
- config/runtime/profiles/project_bootstrap.yaml
- src/aipinho/services/chat/chat_operation_router_service.py
- src/aipinho/services/chat/chat_service.py
- tests/unit/test_chat_operation_router_service.py
- tests/unit/test_hotfix_approval_bootstrap_phase_resume.py

## Tests And Smokes
- `python -m pytest tests\unit\test_chat_operation_router_service.py tests\unit\test_hotfix_approval_bootstrap_phase_resume.py -q`: 70 passed in 19.03s
- `python -m py_compile src\aipinho\services\chat\chat_operation_router_service.py src\aipinho\services\chat\chat_service.py`: passed
- `router smoke: AIpinho - Iniciar Projeto...`: operation_type=project_generation, router_operation_type=project_bootstrap, requires_task=True
- `ChatService smoke for AIpinho Studio bootstrap`: pending_approval with approval_id, preview_id, task_id; workspace_empty=True; expected_outcomes pre-approval only

## Smoke Result
- status: pending_approval
- message: STATUS: PROJECT_BOOTSTRAP_PENDING_APPROVAL
- writes before approval: False
- expected outcomes: discovery_result, blueprint_result, task_preview_result, approval_request_result

## Remaining Risks
- Smoke foi feito por servi?o local/focado; backend em execu??o precisa ser reiniciado para carregar o patch.
- O prompt real completo do Studio deve ser reexecutado no chat ap?s restart para validar UX/persist?ncia de sess?o.
## Live Backend Smoke
- Backend 9088 reiniciado e health ok.
- POST /api/v1/chat com prompt AIpinho Studio retornou `pending_approval`, `project_generation`, `task_preview` e `STATUS: PROJECT_BOOTSTRAP_PENDING_APPROVAL`.
- Approvals de smoke foram negados em seguida para evitar pendencias fantasma.
