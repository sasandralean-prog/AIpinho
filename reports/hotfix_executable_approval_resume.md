# HOTFIX P0 — Executable Approval Resume

Data: 2026-06-25

## Objetivo

Corrigir o fluxo em que um ApprovalRequest era aceito, mas a TaskRun bloqueava em `project_generation_plan_missing` porque o preview aprovado continha apenas permissão genérica de escrita, sem TaskDraft executável.

## Causa raiz

O sistema permitia criar approvals para previews de escrita sem `patch_plan`, `project_generation_plan` ou `concrete_file_operations`. Depois do approval, o runtime criava ou tentava retomar uma TaskRun sem plano executável, gerando bloqueio tardio e mensagens contraditórias de sucesso.

## Correções aplicadas

- Adicionado `ExecutablePlanService` para validar se um draft/preview pode virar approval executável.
- `ApprovalService.create_approval_for_preview()` agora bloqueia creation de ApprovalRequest quando não há plano executável.
- `TaskPreviewService` passa a propagar `executable_plan_ref`, `expected_outcomes` e warnings de plano ausente.
- `ApprovalRequest`, `TaskPreview` e `TaskContractDraft` receberam campos de plano/contrato necessários para rastreabilidade.
- `ApprovalTaskContinuationService` valida o draft aprovado antes de criar TaskRun; se faltar plano, marca `approved_but_no_executable_plan` e não cria run vazia.
- `ChatApprovalCommandService` agora entende aprovação natural mais ampla e `APROVAR task_run_xxx`, lista approvals com draft/preview/runtime/plan/block e não anuncia sucesso se o resume retornou blocked.
- `GovernedWriteChatService` cria `concrete_file_operations` para escrita de arquivo.
- O phase resume do chat persistente não cria approval falso; retorna `IMPLEMENTATION_PLAN_READY` até existir plano executável.
- O preview de project generation no chat agora inclui `project_generation_plan` consistente.
- `target_paths` de approval agora aceita somente paths reais; strings explicativas ficam fora.

## Arquivos alterados

- `src/aipinho/schemas/tasks/task_contract_draft.py`
- `src/aipinho/schemas/tasks/task_preview.py`
- `src/aipinho/schemas/approvals/approval_request.py`
- `src/aipinho/schemas/approvals/approval_event.py`
- `src/aipinho/services/orchestration/executable_plan_service.py`
- `src/aipinho/services/orchestration/task_preview_service.py`
- `src/aipinho/services/approvals/approval_service.py`
- `src/aipinho/services/approvals/approval_task_continuation_service.py`
- `src/aipinho/services/chat/governed_write_chat_service.py`
- `src/aipinho/services/chat/chat_approval_command_service.py`
- `src/aipinho/services/chat/chat_service.py`
- `src/aipinho/api/routers/chat_router.py`
- `tests/unit/test_hotfix_executable_approval_resume.py`
- Ajustes de fixtures em testes existentes de approval lifecycle/continuation.

## Testes

Novo arquivo:

- `tests/unit/test_hotfix_executable_approval_resume.py`

Comando executado:

```powershell
python -m pytest tests\unit\test_approval_preview_lifecycle.py tests\unit\test_approval_service_expiry_listing.py tests\unit\test_governed_approval_continuation.py tests\unit\test_hotfix_approval_bootstrap_phase_resume.py tests\unit\test_hotfix_policy_kernel_approval_gate.py tests\unit\test_governed_write_chat_service.py tests\unit\test_hotfix_executable_approval_resume.py -q
```

Resultado:

```text
64 passed in 66.91s
```

Compilação:

```text
py_compile dos arquivos alterados: passed
```

## Veredito

EXECUTABLE_APPROVAL_RESUME_READY

Critérios cobertos:

- Approval não é criado sem plano executável.
- Approval aprovado valida draft e plano antes de TaskRun.
- Mensagem final não diz sucesso se TaskRun ficou blocked.
- `APROVAR task_run_xxx` e aprovação natural são tratados antes do roteador conversacional.
- Validation/expected outcomes ficam ligados ao contrato aprovado.
- `target_paths` não recebe strings explicativas.
