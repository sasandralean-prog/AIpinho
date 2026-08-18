# HOTFIX P0 - Read-only intent / unapproved write

Data: 2026-06-25

## Veredito

READONLY_UNAPPROVED_WRITE_HOTFIX_READY

## Causa raiz

O chat possuia um caminho de escrita governada que podia ser acionado por nomes de arquivos presentes em perguntas. Como nao havia uma rota read-only especifica para consulta leve de metadados de workspace, uma pergunta numerada como `1. existe build.gradle?` podia ser interpretada como caminho de arquivo. Alem disso, o Tool Gateway estava com auto-approve de escrita ativo e o `GovernedWriteChatService` chamava o planner antes de exigir approval humano para escrita iniciada pelo chat.

## Arquivo indevidamente criado

Existe evidencia de arquivo criado antes deste hotfix:

- `C:\Users\rafae\Documents\AIpinhoTestes\Sprint-File-Sync-main\1. existe build.gradle`

Nao foi deletado automaticamente. Recomendacao: criar uma ApprovalRequest especifica de cleanup para `delete_file` desse path, ou apagar manualmente se o usuario preferir.

## Correcoes aplicadas

1. Negative constraints agora geram flags fortes no caminho de escrita:
   - `write_allowed=false`
   - `shell_allowed=false`
   - `report_file_allowed=false` quando aplicavel
   - `chat_only=true`
   - `readonly=true`

2. Criada rota read-only:
   - `workspace_metadata_query`
   - responde no chat;
   - nao cria task;
   - nao cria artifact;
   - nao escreve arquivo.

3. Negative constraints passam antes de escrita:
   - `Nao crie arquivo`
   - `Nao gere relatorio`
   - `Responda somente no chat`
   - `Apenas metadados`
   - `Read-only`

4. Approval guard reforcado:
   - `config/agents/tool_gateway_policy.yaml` agora tem `approval.require_human_approval_for_chat_workspace_write=true`.
   - Escrita de workspace iniciada pelo chat retorna `pending_approval` antes de gravar.

5. Filename safety:
   - perguntas numeradas nao sao aceitas como filename pelo planner.

6. Speaker truth/write success:
   - resposta "Conclui a escrita..." agora so acontece quando o outcome real do Tool Gateway for `succeeded`.
   - se approval for exigido, a mensagem diz explicitamente que nenhum arquivo foi escrito.

## Arquivos alterados

- `config/agents/tool_gateway_policy.yaml`
- `config/chat/canonical_operation_map.yaml`
- `config/chat/chat_operation_routing_policy.yaml`
- `src/aipinho/services/chat/chat_operation_router_service.py`
- `src/aipinho/services/chat/workspace_metadata_query_service.py`
- `src/aipinho/api/routers/chat_router.py`
- `src/aipinho/services/chat/chat_service.py`
- `src/aipinho/services/chat/governed_write_chat_service.py`
- `src/aipinho/services/agents/agent_local_action_planner.py`
- `tests/unit/test_chat_operation_router_service.py`
- `tests/unit/test_workspace_metadata_query_service.py`
- `tests/unit/test_governed_write_chat_service.py`

## Testes e validacoes

- `python -m py_compile ...`: passou.
- `python -m pytest tests\unit\test_chat_operation_router_service.py tests\unit\test_workspace_metadata_query_service.py -q`: 54 passed.
- `python -m pytest tests\unit\test_governed_write_chat_service.py -q`: 17 passed.
- `python -m pytest tests\integration\test_chat_runtime_parity_api.py -q -k "no_silent or saturation"`: 2 passed, 4 deselected.

## Smoke test

Prompt:

```text
Leia apenas metadados do workspace:
C:\Users\rafae\Documents\AIpinhoTestes\Sprint-File-Sync-main

Nao crie arquivo.
Nao gere relatorio.
Responda somente no chat:
1. existe build.gradle?
2. existe package.json?
3. quais arquivos de entrada parecem existir?
```

Resultado do roteador:

- `operation_type=workspace_metadata_query`
- `router_operation_type=workspace_metadata_query`
- `workspace_write=False`
- `read_only=True`
- `chat_only=True`
- `requested_files=["build.gradle", "package.json"]`

Resultado do ChatService:

- `status=ok`
- `operation_type=workspace_metadata_query`
- `message_type=assistant_final_answer`
- `workspace_write=False`
- `requires_task=False`
- `task_id=None`
- `approval_id=None`

Resultado HTTP persistente apos restart do backend 9088:

- endpoint: `POST /api/v1/chat/sessions/{session_id}/send`
- `status=ok`
- `operation_type=workspace_metadata_query`
- `message_type=assistant_final_answer`
- `workspace_write=false`
- `requires_task=false`
- `task_id=null`
- `approval_id=null`
- `artifact_count=0`
- resposta no chat confirmou: `Nao criei arquivo e nao gerei relatorio.`

## Risco residual

O backend vivo precisa ser reiniciado para carregar todas as alteracoes se ainda estiver rodando uma versao antiga. O arquivo indevido antigo permanece no workspace ate cleanup aprovado.
