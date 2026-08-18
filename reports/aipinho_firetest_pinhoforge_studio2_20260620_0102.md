# AIpinho Firetest PinhoForgeStudio2 - Supervisao Codex

## Resumo executivo

Veredito: `AIPINHO_FIRETEST_PINHOFORGE_BLOCKED`

O teste foi interrompido na Tarefa 1 porque a AIpinho nao conseguiu sair do preview para execucao governada real pelo chat canonico.

Codex nao implementou a tarefa no lugar da AIpinho. Codex apenas enviou prompts, observou respostas, consultou endpoints e verificou o filesystem.

## Ambiente

- Workspace AIpinho: `C:\Dev\AIpinho`
- Workspace alvo: `C:\Users\rafae\Documents\AIpinhoTestes\PinhoForgeStudio2`
- Backend: `http://127.0.0.1:9088`
- Health: `ok`
- Chat canonico usado: `POST /api/v1/chat`
- Sessao: `session_7d63e77b39f24c12a18fef8639d91c9c`

## Tarefa 1

### Prompt enviado

Criar `reports\aipinho_firetest_health.md` no workspace alvo, contendo titulo, timestamp, workspace alvo, lista curta de deteccoes e status `FIRETEST_HEALTH_READY`, depois validar existencia e tamanho maior que zero.

### Resposta 1 da AIpinho

- `operation_type`: `filesystem_write_file`
- `message_type`: `task_preview`
- `status`: `preview`
- `message`: criou preview operacional, nada executado.
- `policy.status`: `needs_approval_or_capability_check`
- `safe_to_preview`: `true`
- `safe_to_execute`: `false`
- `task_id`: `null`
- `run_id`: ausente
- `approval_id`: `null`

### Verificacao independente

- Arquivo esperado: `C:\Users\rafae\Documents\AIpinhoTestes\PinhoForgeStudio2\reports\aipinho_firetest_health.md`
- Resultado: `FILE_NOT_FOUND`

### Recuperacao 1 enviada

Codex pediu em alto nivel que a AIpinho reavaliasse policy/capability/workspace e continuasse pelo fluxo governado se seguro.

### Resposta 2 da AIpinho

- `intent_type`: `filesystem_write_request`
- `operation_type`: `project_generation`
- `status`: `preview`
- `policy.status`: `needs_approval`
- `approval_required_for`: `write_files`
- `safe_to_preview`: `true`
- `safe_to_execute`: `false`
- `task_id`: `null`
- `run_id`: ausente
- `approval_id`: `null`
- Problema: approval necessario foi informado, mas nenhum approval acionavel foi criado ou exposto.

### Recuperacao 2 enviada

Codex pediu em alto nivel que a AIpinho criasse ou expusesse a solicitacao de approval necessaria, ou explicasse com reason_code por que nao conseguiria criar approval.

### Resposta 3 da AIpinho

- `status`: `blocked`
- `message`: bloqueio por citacoes/retrieval/memoria curada.
- `warnings`: `context_citations_required`, `citation_bypass_blocked`
- Problema: desvio para bloqueio de contexto/RAG nao relacionado a uma tarefa simples de escrita governada.

## Estado interno observado

### Task runtime

Endpoint: `GET /api/v1/task-runtime/status`

- `status`: `ok`
- `enabled`: `true`
- `mode`: `governed_controlled`
- `write_enabled`: `true`
- `patch_enabled`: `true`
- `shell_enabled`: `true`
- `allowed_actions` inclui `write_files`, `apply_patch`, `run_command`, `run_tests`, `web_request`, `artifact_generate`

### Queue

Endpoint: `GET /api/v1/task-runtime/queue`

- `active_count`: `0`
- `pending_count`: `0`
- `requires_decision_count`: `0`
- Nenhuma task visivel foi criada.

### Approval policy

Endpoint: `GET /api/v1/policy/approvals`

- `write_files` exige approval.
- O chat reconheceu a necessidade, mas nao criou `approval_id`.

## Classificacao da tarefa

Tarefa 1: `FAIL_EXECUTION` + `FAIL_ROUTING`

Motivos:

- Intent inicial correta, mas execucao nao iniciou.
- Nenhum `task_id`, `run_id` ou `approval_id` foi criado.
- Approval necessario nao virou acao acionavel.
- Retry final contaminou o fluxo com bloqueio de citation/RAG nao relacionado.
- Arquivo alegado nunca existiu.

## Bugs encontrados

### Bug 1 - Chat canonico para em preview

Pedidos operacionais de escrita em workspace permitido continuam retornando preview em vez de criar task/run/approval acionavel.

### Bug 2 - Approval nao materializado

Policy retorna `needs_approval` para `write_files`, mas o chat nao cria nem expoe `approval_id`.

### Bug 3 - Operation drift

O primeiro prompt foi `filesystem_write_file`; na recuperacao a resposta reportou `operation_type=project_generation`, apesar de a tarefa ser escrita simples de relatorio.

### Bug 4 - Context/RAG contamination

Ao pedir recuperacao do fluxo de approval, a AIpinho bloqueou por `context_citations_required`, sem relacao com a tarefa.

### Bug 5 - Mobile/session mismatch observado

O endpoint mobile view-model consultado para a sessao retornou conteudo de outra sessao `chat_caf6342e0c754d2592e2a8f9c33530e7`, indicando possivel divergencia de session id ou fallback de view-model.

## Comandos e endpoints usados

- `POST /api/v1/chat`
- `GET /api/v1/health`
- `GET /api/v1/models/status`
- `GET /api/v1/task-runtime/status`
- `GET /api/v1/task-runtime/queue`
- `GET /api/v1/policy/approvals`
- `GET /openapi.json`
- Verificacao filesystem via PowerShell `Test-Path`

## Arquivos gerados por Codex para auditoria

- `C:\Dev\AIpinho\data\runtime\firetest_pinhoforge_task1_response.json`
- `C:\Dev\AIpinho\data\runtime\firetest_pinhoforge_task1_recovery_response.json`
- `C:\Dev\AIpinho\data\runtime\firetest_pinhoforge_task1_approval_recovery_response.json`
- `C:\Dev\AIpinho\data\runtime\firetest_pinhoforge_task1_observation.json`

## Veredito final

`AIPINHO_FIRETEST_PINHOFORGE_BLOCKED`

Nao avancar para as Tarefas 2-7 enquanto a Tarefa 1 nao conseguir:

1. criar task/run ou approval acionavel;
2. executar escrita governada em target permitido;
3. validar arquivo no filesystem;
4. responder com evidencia real;
5. evitar contamination de contexto/RAG em recuperacao de approval.

## Recomendacao de proximo hotfix

Criar um hotfix focado no caminho:

`Chat canonical -> policy needs_approval -> approval materialization -> task/run from approved preview -> governed write_files -> validation -> speaker truth`

Invariantes sugeridas:

- `needs_approval` deve sempre produzir `approval_id` ou reason_code especifico.
- `task_preview` com `requires_task=true` nao pode encerrar sem `preview_id`, `task_id`, `approval_id` ou safe action acionavel.
- Recovery prompts sobre approval nao podem ser reclassificados como RAG/citation block.
- Mobile view-model deve resolver exatamente a sessao solicitada.
