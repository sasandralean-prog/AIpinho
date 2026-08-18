# HOTFIX P0 - Approval UX e Continuação de Tasks Governadas

Data: 2026-06-23 05:15:49

## Veredito

**HOTFIX_APPROVAL_UX_READY**

O fluxo de approval deixou de ser um beco sem saída. Tasks que entram em `waiting_input` com `approval_id` agora podem ser aprovadas/negadas por endpoints, botões de Pipeline já existentes ou comandos textuais explícitos no chat. A aprovação não executa side effect diretamente; ela libera a `TaskRun` para retomar pela fila governada, mantendo runtime guard, policies, capabilities e validação.

## Problemas Corrigidos

1. Approval aprovado não retomava task.
   - Causa: `ApprovalService.approve()` registrava decisão, mas não vinculava a decisão à fila/runtime.
   - Correção: criado `ApprovalTaskContinuationService` e vínculo `approval_id -> task_run`.

2. Approval não tinha contexto operacional suficiente.
   - Causa: `ApprovalRequest` não carregava `run_id`, `task_id`, workspace, operação, target paths e preview resumido.
   - Correção: schema enriquecido e `ApprovalService.create_approval_for_preview()` passou a preencher contexto.

3. Fila ignorava approval aprovado.
   - Causa: `TaskQueueService` tratava pending/rejected/cancelled, mas não `approved`.
   - Correção: approval aprovado remove `approval_required`, marca `auto_run_requested=True` e emite eventos de retomada.

4. API de approval não devolvia resultado de retomada.
   - Correção: endpoints `approve/reject/cancel` retornam `resume`.

5. Batch approval não tinha regra segura.
   - Correção: adicionados batch approve/deny com validação mesma task/workspace e exclusão de ações destrutivas.

6. Chat não aceitava approval textual rastreável.
   - Correção: criado `ChatApprovalCommandService`.
   - Comandos aceitos exigem `approval_id` ou `task_id/run_id` explícito.
   - Pedidos vagos como “pode aprovar isso” não viram approval.

7. Prompt para configurar policies/contratos/configs/workspaces precisava ser suportado sem “libera geral”.
   - Correção: criado `GovernedConfigurationChangeChatService` e rota `governed_configuration_change`.
   - O chat gera preview governado, com approval/validation obrigatórios.
   - Não há mutação direta de YAML/config pelo chat.

8. Contratos de eventos estavam incompletos.
   - Correção: adicionados eventos `approval_runtime_context_attached`, `approval_approved`, `approval_cancelled` e `task_resumed_after_approval` aos contratos/policies adequados.

## Arquivos Alterados

- `src/aipinho/schemas/approvals/approval_request.py`
- `src/aipinho/schemas/approvals/approval_decision.py`
- `src/aipinho/schemas/approvals/approval_state.py`
- `src/aipinho/schemas/approvals/approval_event.py`
- `src/aipinho/services/approvals/approval_policy.py`
- `src/aipinho/services/approvals/approval_service.py`
- `src/aipinho/services/approvals/approval_task_continuation_service.py`
- `src/aipinho/api/routers/approval_router.py`
- `src/aipinho/api/routers/task_runtime_router.py`
- `src/aipinho/services/runtime/task_runtime_service.py`
- `src/aipinho/services/runtime/task_queue_service.py`
- `src/aipinho/services/chat/chat_approval_command_service.py`
- `src/aipinho/services/chat/governed_configuration_change_chat_service.py`
- `src/aipinho/services/chat/chat_operation_router_service.py`
- `src/aipinho/api/routers/chat_router.py`
- `config/policies/approval_lifecycle_policy.yaml`
- `config/runtime/task_run_event_policy.yaml`
- `config/chat/chat_operation_routing_policy.yaml`
- `tests/unit/test_governed_approval_continuation.py`
- `tests/unit/test_chat_operation_router_service.py`
- `tests/integration/test_preview_approval_api.py`

## Endpoints/Contratos

Novos ou fortalecidos:

- `POST /api/v1/approvals/{approval_id}/approve`
- `POST /api/v1/approvals/{approval_id}/reject`
- `POST /api/v1/approvals/{approval_id}/deny`
- `POST /api/v1/approvals/{approval_id}/cancel`
- `POST /api/v1/approvals/batch/approve`
- `POST /api/v1/approvals/batch/deny`
- `POST /api/v1/approvals/batch/reject`
- `GET /api/v1/tasks/{task_id}/approvals`
- `POST /api/v1/tasks/{task_id}/approvals/approve-safe-batch`

## Configurabilidade por Prompt

Implementado como preview governado:

- policies;
- contracts;
- configs;
- workspaces.

Regra: prompt pode solicitar mudança, mas o resultado é `governed_configuration_change` com `task_preview`, `requires_preview=true`, `requires_approval=true`, `requires_validation=true` e `direct_mutation_allowed=false`.

Isso evita:

- hardcode;
- “libera geral”;
- mutação invisível de config;
- bypass de policy.

## Policies Relaxadas

Em `approval_lifecycle_policy.yaml`:

- `never_execute_on_approval: false`
- `resume_task_after_approval: true`
- `approved_side_effect_execution_enabled: true`
- `resume_after_approval: true`

Bloqueios mantidos:

- `git_commit`
- `git_push`
- `write_memory`
- ações destrutivas em batch seguro.

## Testes

Executados:

```text
python -m py_compile ...
python -m pytest tests\unit\test_governed_approval_continuation.py tests\unit\test_chat_operation_router_service.py -q
python -m pytest tests\unit\test_approval_preview_lifecycle.py tests\unit\test_approval_policy_service.py tests\unit\test_task_queue_service.py tests\unit\test_task_runtime_service.py -q
python -m pytest tests\integration\test_preview_approval_api.py tests\contract\test_preview_approval_contracts.py -q
python -m pytest tests\unit\test_governed_approval_continuation.py tests\unit\test_chat_operation_router_service.py tests\unit\test_approval_preview_lifecycle.py tests\unit\test_approval_policy_service.py tests\unit\test_task_queue_service.py tests\unit\test_task_runtime_service.py tests\integration\test_preview_approval_api.py tests\contract\test_preview_approval_contracts.py -q
```

Resultado final:

```text
91 passed in 33.80s
```

## Riscos Restantes

- Não foi rodado full pytest.
- UI mobile/launcher já possuía botões de approval; não foi feito QA visual nesta rodada.
- A continuação real ainda depende da fila/runtime e dos guards, como esperado.

## Critério de Aceite

- Approval pendente fica acionável.
- Aprovar retoma pela fila governada.
- Negar/cancelar não executa side effect.
- Batch approval é limitado e seguro.
- Chat aceita approval textual somente com alvo explícito.
- Prompt para policy/config/workspace vira preview governado.
- Sem hardcode por prompt específico, path específico ou usuário.
