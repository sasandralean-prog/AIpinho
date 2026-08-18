# HOTFIX P0 — Policy Kernel Approval Gate

Data: 2026-06-25

## Veredito

POLICY_KERNEL_APPROVAL_GATE_READY

## Problema corrigido

O fluxo de escrita/patch estava convertendo ações `apply_patch` e `write_files` em bloqueio seco antes de criar `ApprovalRequest`. Isso quebrava o fluxo governado porque a AIpinho exigia aprovação, mas não criava o objeto que o usuário poderia aprovar.

Também havia uma mensagem contraditória: "Pedido bloqueado: permitido pela Policy Kernel".

## Causa raiz

1. `write_files` e `apply_patch` estavam presentes em `governed_tool_execution.denied_actions`, impedindo o bootstrap de approval.
2. Previews aprovados podiam gerar `TaskRun` sem `runtime_profile` válido ou sem `TaskRun` vinculado.
3. A continuação pós-approval não criava uma `TaskRun` quando o approval tinha apenas `preview_id`.
4. O runtime de escrita usava profile `governed`, que não existe como perfil executável.
5. O timeout global ignorava `max_duration_seconds` dos perfis, e uma escrita já executada podia virar blocked por timeout antes da validação final.
6. O `AgentSessionStore.add_event` recalculava `session_sequence` varrendo todos os arquivos de eventos a cada evento, causando atraso grande no Tool Gateway.

## Correções aplicadas

- `policy ask` para `write_files`/`apply_patch` agora cria approval em vez de bloquear seco.
- `ApprovalRequest` não exige aprovação prévia para ser criado.
- `ApprovalTaskContinuationService` cria uma `TaskRun` a partir de preview aprovado quando não existe run vinculada.
- Drafts de chat e resume usam `runtime_profile` real: `write_file` ou `project_generation`.
- `TaskRuntimeService` preserva `operation_type` e `runtime_profile` do draft.
- `TaskRunGuard` usa timeout configurável por perfil.
- `write_file.yaml` passou a permitir até 600s para fluxo governado de escrita.
- `AgentSessionStore` usa contador persistente por sessão para eventos, evitando varredura global.
- Speaker não gera mais a frase contraditória para blocked com denied actions.
- `sprint_file_sync` ficou com permissões `ask` para write/patch/artifact/shell governado.
- `aipinho_runtime` foi registrado como `system_mutable` para grants/approvals/tasks/events.

## Arquivos alterados

- `C:\Dev\AIpinho\config\policies\governed_tool_execution_policy.yaml`
- `C:\Dev\AIpinho\config\workspaces\workspace_registry.yaml`
- `C:\Dev\AIpinho\config\runtime\profiles\write_file.yaml`
- `C:\Dev\AIpinho\src\aipinho\services\speaker\speaker_service.py`
- `C:\Dev\AIpinho\src\aipinho\services\runtime\task_runtime_service.py`
- `C:\Dev\AIpinho\src\aipinho\services\approvals\approval_task_continuation_service.py`
- `C:\Dev\AIpinho\src\aipinho\services\chat\chat_service.py`
- `C:\Dev\AIpinho\src\aipinho\api\routers\chat_router.py`
- `C:\Dev\AIpinho\src\aipinho\services\chat\governed_write_chat_service.py`
- `C:\Dev\AIpinho\src\aipinho\services\runtime\task_run_guard.py`
- `C:\Dev\AIpinho\src\aipinho\services\agents\agent_session_store.py`
- `C:\Dev\AIpinho\tests\unit\test_effective_policy_builder.py`
- `C:\Dev\AIpinho\tests\unit\test_task_run_guard.py`
- `C:\Dev\AIpinho\tests\unit\test_hotfix_policy_kernel_approval_gate.py`

## Testes executados

- `python -m pytest tests\unit\test_hotfix_policy_kernel_approval_gate.py tests\unit\test_hotfix_approval_bootstrap_phase_resume.py tests\unit\test_effective_policy_builder.py tests\unit\test_approval_preview_lifecycle.py tests\unit\test_governed_tool_execution_service.py tests\unit\test_governed_approval_continuation.py tests\unit\test_task_run_guard.py tests\unit\test_agent_event_bus_timeline.py tests\unit\test_agent_tool_gateway_service.py -q`

Resultado: `70 passed in 27.73s`

- `python -m py_compile` nos módulos alterados.

Resultado: passed.

## Smoke real

Prompt:

`Crie um arquivo reports\kernel_policy_smoke_test.md com o texto teste no workspace "C:\Users\rafae\Documents\AIpinhoTestes\Sprint-File-Sync-main".`

Resultado antes do approval:

- `approval_id`: `approval_d74313e838204465b8a11812495b4753`
- arquivo não existia antes da aprovação.

Comando:

`APROVAR approval_d74313e838204465b8a11812495b4753`

Resultado pós-approval:

- arquivo criado: `C:\Users\rafae\Documents\AIpinhoTestes\Sprint-File-Sync-main\reports\kernel_policy_smoke_test.md`
- task run: `task_run_051e6307a9594002a18a6ff1110c3ec1`
- status final: `completed`
- steps finalizados: `validate_runtime`, `validate_workspace`, `execute_filesystem_operation`, `validate_filesystem_result`, `compose_final_result`

## Riscos residuais

- O fluxo ainda mantém execução síncrona no request de aprovação para alguns caminhos, o que pode segurar o HTTP enquanto a task roda. O backend não travou no smoke final, mas isso deve evoluir para resposta imediata + polling em sprint de UX/runtime.
- `write_file` agora permite 600s por perfil; isso é intencional e configurável, mas deve ser observado em fila concorrente.

## Conclusão

O bug P0 do approval bootstrap foi corrigido. A AIpinho agora cria `ApprovalRequest` para `policy=ask`, não executa antes da aprovação, retoma execução após aprovação textual e valida a escrita real no workspace governado.
