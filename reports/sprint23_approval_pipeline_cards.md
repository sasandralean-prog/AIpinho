# Sprint 23 — Approval/Pipeline Cards

## Estado atual

Os grants criados por chat retornam `ChatResponse.status=pending_approval`, `message_type=task_preview`, `next_actions` e `contract_preview.grant`. Isso permite que clientes que já renderizam previews/actions mostrem botões humanos de aprovação, negação e alteração de escopo sem criar endpoint novo neste patch.

## Payload principal

Campos relevantes:

- `operation_type=session_permission_grant`
- `policy.grant_id`
- `policy.workspace_id`
- `contract_preview.grant`
- `contract_preview.operation_contract`
- `next_actions[].type=approve_grant`
- `next_actions[].type=deny_grant`
- `next_actions[].type=change_scope`

## Comandos textuais equivalentes

- `APROVAR GRANT grant_xxx`
- `NEGAR GRANT grant_xxx`

Botão e texto devem chamar o mesmo backend lógico: `ChatApprovalCommandService` para decisão textual e `SessionGrantService` como store de estado.

## Limitação planejada

Ainda não foi criado um endpoint dedicado `/api/v1/grants/pending`. Se o Pipeline precisar listar grants fora da timeline de chat, criar router fino em sprint posterior usando `SessionGrantService.list_grants(status="pending")`.
