# Sprint 23 — Chat-Native Permission Grants

## Resultado

Veredito: `SPRINT23_CHAT_NATIVE_GRANTS_READY_WITH_UX_BACKLOG`

O núcleo backend para grants temporários por chat foi implementado. A AIpinho agora consegue reconhecer pedidos naturais de permissão, criar um `SessionGrant` pendente, responder com instruções humanas para aprovação/negação e aceitar comandos textuais `APROVAR GRANT <grant_id>` / `NEGAR GRANT <grant_id>`.

## O que foi implementado

- Schema `SessionGrant` com status, escopo, ações, workspace, expiração e limite de usos.
- Store local auditável em `data/runtime/session_grants`.
- `ChatPermissionGrantService` para detectar pedidos naturais de permissão temporária.
- Separação entre grant temporário e pedido permanente de config.
- Pedidos permanentes retornam preview de `ConfigChangeRequest` esperado, sem mutar configuração automaticamente.
- `ChatApprovalCommandService` passou a aceitar comandos textuais para grants.
- `ChatService` chama o handler de grant antes do roteador operacional, evitando que pedido de permissão vire task por engano.

## Regras preservadas

- Grants não alteram `workspace_registry.yaml`.
- Grants não concedem `delete_file` por menção vaga a apagar/excluir; exigem frase explícita forte.
- Grants aprovados continuam limitados por `actions`, `paths_scope`, `command_scope`, expiração e uso.
- Pedido permanente exige fluxo de governança configurável: preview, approval, backup, apply e self-check.
- Nenhum fluxo executa escrita/shell como efeito colateral do chat.

## Arquivos alterados

- `src/aipinho/schemas/interaction/session_grant.py`
- `src/aipinho/services/chat/session_grant_service.py`
- `src/aipinho/services/chat/chat_permission_grant_service.py`
- `src/aipinho/services/chat/chat_approval_command_service.py`
- `src/aipinho/services/chat/chat_service.py`
- `tests/unit/test_session_grant_service.py`
- `tests/unit/test_chat_permission_grant_service.py`

## Testes

- `python -m py_compile ...` passou.
- `python -m pytest tests/unit/test_session_grant_service.py tests/unit/test_chat_permission_grant_service.py -q` passou.
- Resultado: `7 passed in 1.64s`.

## Backlog honesto

- A UX Mobile/Launcher ainda precisa transformar `next_actions` de grant em cards dedicados, se quiser UI visual além do comando textual.
- Pipeline ainda consome o grant como payload de chat/preview; um endpoint dedicado de listagem de grants pode ser adicionado em sprint posterior.
- A execução governada precisa consultar `SessionGrantService.is_effective()` no ponto de capability gap para usar grants aprovados como evidência de permissão temporária.

## Veredito

O Sprint 23 fecha o núcleo de concessão por chat, com validação unitária. O fechamento completo multicanal visual depende de wiring UX/pipeline adicional.
