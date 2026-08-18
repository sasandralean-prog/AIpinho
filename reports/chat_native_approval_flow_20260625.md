# Chat-Native Approval Flow — 2026-06-25

## Veredito

CHAT_NATIVE_APPROVAL_READY_WITH_WARNINGS

## Objetivo

Implementar aprovação, negação e consulta de permissões por chat em Mobile/Launcher/API e VSCode/Continue, sem bypass de policy e sem execução direta fora do runtime governado.

## Causa raiz

A rota OpenAI-compatible do Continue tratava pedidos de escrita/shell com refusal genérico e não materializava um `ApprovalRequest`. O chat persistente já possuía um handler parcial de approval textual, mas ele não cobria `APROVAR` sem id, detalhes por chat, ambiguidade por sessão e não havia endpoint canônico `/api/v1/chat/approval-command`.

## Correções aplicadas

- Expandido `ChatApprovalCommandService` para parsing de `APROVAR`, `APROVAR ULTIMA`, `NEGAR`, `MOSTRAR PREVIEW/RISCOS/POLICY/DIFF/COMANDO/ARQUIVOS AFETADOS` e escopo textual.
- Adicionado endpoint `POST /api/v1/chat/approval-command`.
- Integrado o handler no `ChatService.respond()` e no chat persistente `/api/v1/chat/sessions/{session_id}/send`.
- Integrado o Continue `/v1/chat/completions` ao mesmo handler textual.
- Pedidos de escrita/shell no Continue agora criam draft, preview e `ApprovalRequest` real com `approval_id`, sem executar side effect.
- Adicionados eventos de approval chat-native ao schema `ApprovalEventType`.
- Mantido o guard de `refresh_policy()` antes de aprovar: o gate recusou remover essa proteção e a fixture de teste foi corrigida para usar preview/draft real.

## Arquivos alterados

- `src/aipinho/services/chat/chat_approval_command_service.py`
- `src/aipinho/api/routers/chat_router.py`
- `src/aipinho/services/chat/chat_service.py`
- `src/aipinho/api/routers/continue_integration_router.py`
- `src/aipinho/schemas/approvals/approval_event.py`
- `tests/unit/test_governed_approval_continuation.py`
- `tests/integration/test_continue_openai_compat_api.py`

## Comportamentos novos

- `APROVAR approval_xxx` aprova approval real e retoma task vinculada quando houver `run_id` válido.
- `NEGAR approval_xxx` rejeita approval real e reconcilia/cancela a task vinculada quando houver.
- `APROVAR` sem id só funciona quando há exatamente uma pending approval na sessão; múltiplas pendências retornam `approval_ambiguous_decision`.
- `MOSTRAR PREVIEW approval_xxx` retorna detalhes textuais do ApprovalRequest.
- Delete/move/git push exigem frase específica quando já existir approval com ação sensível.
- Continue transforma pedidos de escrita/shell em bloco `APPROVAL REQUIRED` com `approval_id`.
- Continue aceita `APROVAR approval_xxx`/`NEGAR approval_xxx` pela própria rota OpenAI-compatible.

## Limitações documentadas

- Mudança permanente de policy por chat ainda não aplica config; retorna preview/aviso para futuro `ConfigChangeRequest`.
- Read approval específico para leitura de workspace não foi expandido porque a policy atual não inclui `read_file/list_files` como approvable actions e o gate recusou expandir actions sensíveis nesta rodada.
- Approval criado pelo Continue para escrita/shell não executa a ação diretamente no mesmo response; ele registra decisão e preserva execução para runtime governado quando houver run vinculada.

## Testes executados

- `python -m py_compile` nos arquivos alterados: passou.
- `python -m pytest tests\unit\test_governed_approval_continuation.py -q`: 12 passed.
- `python -m pytest tests\integration\test_continue_openai_compat_api.py -q`: 33 passed.

## Segurança

- Não houve bypass de approval.
- Não houve write/shell direto pelo Continue.
- `refresh_policy()` antes de approve foi preservado.
- Approval textual exige `ApprovalRequest` real.
- Ambiguidade de múltiplas approvals não aprova automaticamente.

## Próximos passos

- Implementar `ConfigChangeRequest` completo para permission grant por chat.
- Formalizar read/list approvals se a policy permitir em sprint de governança.
- Ligar a execução pós-approval do Continue a uma TaskRun quando a ação vier de um preview executável, mantendo validation gate.
