# Hotfix P0 - Approval Bootstrap, Phase Resume e Report Idempotency

Data: 2026-06-25
Projeto: AIpinho / PinhoabacaxiAI
Workspace: C:\Dev\AIpinho
Veredito: APPROVAL_BOOTSTRAP_PHASE_RESUME_READY

## Resumo

O hotfix corrigiu tres falhas P0 no fluxo governado:

1. Policy `ask` agora cria `TaskContractDraft`, `TaskPreview` e `ApprovalRequest` antes de qualquer execucao.
2. Frases de permissao temporaria no chat persistente agora passam pelo `SessionGrant`, em vez de serem roteadas como alteracao permanente de config ou task de projeto.
3. Retomada a partir de relatorio/preflight existente agora cria preview de implementacao com approval, sem rerodar auditoria e sem tentar recriar o relatorio.
4. Operacoes de criacao/geracao de projeto no chat principal agora criam approval real quando a policy e `ask`, em vez de devolver apenas preview generico.

Nenhum arquivo de workspace do usuario foi escrito durante o hotfix. As mudancas sao genericas e nao dependem de LogForge, nome de app, sprint, path real ou frase exata.

## Causa raiz

### Approval Bootstrap Paradox

`GovernedWriteChatService` retornava `approval_required` quando a policy exigia approval, mas nao criava `ApprovalRequest`. O usuario via um bloqueio sem `approval_id`, portanto nao havia como aprovar.

### SessionGrant vs ConfigChangeRequest

O `ChatService` ja chamava `ChatPermissionGrantService`, mas o endpoint persistente `/api/v1/chat/sessions/{session_id}/send` nao chamava esse servico antes do roteamento normal. Assim, "dou permissao para esta tarefa" podia ser interpretado como pedido operacional.

### Phase Resume

O roteador normalizava `governed_project_rebuild` para `project_generation`, mas o handler persistente testava apenas `decision.operation_type == "governed_project_rebuild"`. Alem disso, retomada por relatorio caia no preview antigo de rebuild source->target, que podia bloquear com `source_workspace_not_found_in_session`.

### FileExistsError / report existente

O servico de auditoria read-only nao tinha uma politica explicita de idempotencia para relatorio ja existente. O caminho seguro e reutilizar o relatorio existente como evidencia ou criar outro fluxo governado, nao falhar automaticamente.

### Preview generico sem ApprovalRequest

`ChatService._specific_operation_preview_response()` tratava operacoes como `project_create`, `android_project_create`, `project_generation` e `governed_project_rebuild` com preview generico. Isso quebrava o bootstrap de approval para pedidos de implementacao, porque o usuario recebia uma previa sem `approval_id`.

## Arquivos alterados

- C:\Dev\AIpinho\src\aipinho\schemas\governed_write.py
- C:\Dev\AIpinho\src\aipinho\services\chat\governed_write_chat_service.py
- C:\Dev\AIpinho\src\aipinho\services\chat\chat_service.py
- C:\Dev\AIpinho\src\aipinho\api\routers\chat_router.py
- C:\Dev\AIpinho\src\aipinho\services\chat\chat_operation_router_service.py
- C:\Dev\AIpinho\src\aipinho\services\chat\chat_approval_command_service.py
- C:\Dev\AIpinho\src\aipinho\services\artifacts\workspace_readonly_audit_report_service.py
- C:\Dev\AIpinho\config\chat\chat_operation_routing_policy.yaml
- C:\Dev\AIpinho\config\artifacts\workspace_readonly_audit_policy.yaml
- C:\Dev\AIpinho\tests\unit\test_hotfix_approval_bootstrap_phase_resume.py

## Mudancas aplicadas

### Approval bootstrap

`GovernedWriteOutcome` ganhou `draft_id`, `preview_id` e `approval_id`.

`GovernedWriteChatService` agora cria:

- `TaskContractDraft`
- `TaskPreview`
- `ApprovalRequest`

quando a policy exige approval para escrita. A acao de approval e `write_files`, enquanto a operacao solicitada continua preservada como `create_file`, `modify_file` ou `create_directory`.

### Project generation approval preview

`ChatService` agora trata operacoes de geracao/criacao de projeto como fluxo governado de preview + approval:

- cria `OperationContract`;
- cria `TaskContractDraft`;
- cria `TaskPreview`;
- cria `ApprovalRequest`;
- retorna `PROJECT_GENERATION_PENDING_APPROVAL` com `approval_id`;
- nao executa escrita antes da aprovacao.

### Chat persistente e SessionGrant

`send_chat_session_message` agora chama `ChatPermissionGrantService` logo apos comandos explicitos de approval e antes de `ChatOperationRouterService`. Frases temporarias de permissao retornam `session_permission_grant` com `grant_id`.

### Phase resume

`chat_operation_routing_policy.yaml` ganhou a secao `phase_resume_implementation`, com termos configuraveis.

`ChatOperationRouterService` agora detecta relatorio citado como evidencia de fase anterior e produz metadata `phase_resume`:

- `completed_phase=preflight`
- `next_phase=implementation_plan`
- `evidence_report_path`
- `evidence_exists`

`chat_router` tem um handler de `phase_resume_implementation` que cria preview/approval sem executar escrita.

### Report idempotente

`WorkspaceReadonlyAuditReportService` agora usa politica idempotente configuravel quando o arquivo alvo ja existe:

- `read_existing`;
- `create_timestamped_copy`;
- `ask_before_overwrite`.

A configuracao atual usa `read_existing`, retornando `existing_report_reused` e impedindo falha automatica por arquivo preexistente.

### Status

Auditoria read-only agora usa `STATUS: WORKSPACE_READONLY_AUDIT_READY`, em vez de `STATUS: READY` generico.

### Approval commands

`ChatApprovalCommandService` agora reconhece:

- `LISTAR APPROVALS`
- `LISTAR APPROVALS PENDENTES`
- `MOSTRAR APPROVALS`
- `MOSTRAR APPROVALS PENDENTES`

As respostas listam `approval_id`, status, acao, workspace, arquivos/comando quando disponiveis e instrucao de aprovacao por chat. Sem pendencias, retorna `NENHUM_APPROVAL_PENDENTE`.

## Evidencias

### Smoke de phase resume

Entrada:

`Continue a partir do preflight e implemente o MVP LogForge.`

Resultado:

- status: `pending_approval`
- operation_type: `governed_project_rebuild`
- approval_id: `approval_a82408568565463d8155c571402c7587`
- preview_id: `preview_d23f78f8fec4485ebc31881df9426904`
- mensagem: `STATUS: IMPLEMENTATION_PLAN_READY`
- policy: `approval_required_for=["write_files"]`
- evidencia encontrada automaticamente em `reports\logforge_mobile_preflight.md`

### Smoke de SessionGrant

Entrada:

`dou permissao explicita para alterar arquivos durante esta tarefa em <workspace>`

Resultado:

- status: `pending_approval`
- operation_type: `session_permission_grant`
- grant_id: criado

Observacao: o approval e o grant criados pelo smoke manual foram encerrados depois da validacao com motivo `hotfix_smoke_cleanup`, para nao deixar pendencias artificiais no runtime.

## Testes executados

```powershell
$env:PYTHONPATH='C:\Dev\AIpinho\src'
python -m py_compile C:\Dev\AIpinho\src\aipinho\schemas\governed_write.py C:\Dev\AIpinho\src\aipinho\services\chat\governed_write_chat_service.py C:\Dev\AIpinho\src\aipinho\services\chat\chat_service.py C:\Dev\AIpinho\src\aipinho\services\chat\chat_approval_command_service.py C:\Dev\AIpinho\src\aipinho\services\chat\chat_operation_router_service.py C:\Dev\AIpinho\src\aipinho\api\routers\chat_router.py C:\Dev\AIpinho\src\aipinho\services\artifacts\workspace_readonly_audit_report_service.py
python -m pytest tests\unit\test_governed_write_chat_service.py -q
python -m pytest tests\unit\test_hotfix_approval_bootstrap_phase_resume.py -q
python -m pytest tests\unit\test_governed_write_chat_service.py tests\unit\test_hotfix_approval_bootstrap_phase_resume.py -q
python -m pytest tests\unit\test_chat_permission_grant_service.py tests\unit\test_approval_preview_lifecycle.py tests\unit\test_workspace_readonly_audit_report_service.py tests\unit\test_hotfix_approval_bootstrap_phase_resume.py -q
python -m pytest tests\unit\test_governed_write_chat_service.py tests\unit\test_chat_permission_grant_service.py tests\unit\test_approval_preview_lifecycle.py tests\unit\test_workspace_readonly_audit_report_service.py tests\unit\test_hotfix_approval_bootstrap_phase_resume.py -q
```

Resultados:

- `test_governed_write_chat_service.py`: 17 passed
- `test_hotfix_approval_bootstrap_phase_resume.py`: 10 passed
- suite combinada governed write + hotfix: 24 passed
- suite grant/approval/audit/hotfix: 23 passed
- suite focada final: 43 passed

## Testes novos

- `test_ask_policy_creates_approval_not_blocked`
- `test_permission_phrase_creates_session_grant_not_config_change`
- `test_continue_from_preflight_starts_implementation_plan`
- `test_phase_resume_persistent_chat_creates_pending_approval`
- `test_continue_from_preflight_without_explicit_report_path_uses_existing_report`
- `test_project_generation_policy_ask_creates_pending_approval`
- `test_implementation_request_does_not_route_to_workspace_readonly_audit_report`
- `test_preflight_existing_file_does_not_raise_file_exists`
- `test_list_pending_approvals_command_returns_visible_list`
- `test_list_approvals_no_pending_returns_none`

## Riscos restantes

- A aprovacao textual agora registra a decisao e deixa o runtime governado pronto para continuar, mas a execucao final ainda depende dos servicos de runtime/queue que ja existiam.
- O handler de phase resume cria preview/approval generico de implementacao. A qualidade do plano detalhado ainda depende da camada posterior de planner/executor.
- Nao foi executado um build real do app LogForge neste hotfix; o objetivo aqui foi destravar approval/resume/idempotencia.
- O backend vivo na porta 9088 pode precisar de restart elevado para carregar o patch se ainda estiver preso em PID antigo; tentativa anterior de stop encontrou `AccessDenied`.

## Confirmacoes

- Policy `ask` nao bloqueia antes de criar approval.
- Criar `ApprovalRequest` nao exige approval anterior.
- Preview nao executa escrita.
- SessionGrant temporario nao altera config permanente.
- Relatorio existente e reutilizado.
- `STATUS: READY` generico foi removido da auditoria read-only.
- Operacao de geracao de projeto no chat retorna `PROJECT_GENERATION_PENDING_APPROVAL` com `approval_id`.
- Comando `LISTAR APPROVALS PENDENTES` funciona.
- Nao houve hardcode para LogForge, path real ou prompt exato.
- Pendencias criadas por smoke foram encerradas apos validacao.
