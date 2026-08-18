# Continue Governed Dev Relaxation - 2026-06-25

## Objetivo
Relaxar a rota OpenAI-compatible da AIpinho para o Continue/VS Code atuar como assistente de programacao governado, sem transformar o adapter em bypass de escrita, shell ou patch.

## Causa raiz
A rota `/v1/chat/completions` estava usando um detector lexical amplo demais. Palavras como `configurar`, `patch`, `terminal`, `arquivo` e verbos de programacao acionavam uma recusa generica de "conexao e conversa segura", mesmo quando o pedido era conversa, capacidade, explicacao ou analise de contexto ja anexado pelo Continue.

Tambem havia risco de o modelo externo `aipinho-local` ser repassado ao ChatService interno como `model_id`, causando erro `model_not_found`. Isso ja havia sido corrigido antes desta rodada e foi mantido nos testes.

## Alteracoes aplicadas
- Criado `config/integrations/continue_adapter_policy.json`.
- Atualizado `src/aipinho/api/routers/continue_integration_router.py`.
- Atualizado `tests/integration/test_continue_openai_compat_api.py`.
- Atualizado `docs/integrations/continue_vscode_aipinho.md`.

## Classifier
O adapter agora classifica a rota Continue em categorias semanticas:

- `conversation`
- `math_or_reasoning`
- `how_to_configure`
- `continue_context_analysis`
- `file_write_request`
- `shell_request`
- `dangerous_operation_request`
- `patch_preview_request`

Perguntas de capacidade e configuracao nao sao tratadas automaticamente como mutacao. Exemplo: "Voce consegue configurar personalidade e tom?" retorna orientacao de configuracao governada, nao refusal operacional.

## Context parser
A rota detecta referencias anexadas pelo Continue, incluindo:

- `@App.tsx` e outros arquivos;
- `@Terminal`;
- `@Git Diff`;
- `@rules/...`.

Quando o contexto ja veio anexado, a AIpinho reconhece que pode analisa-lo sem alegar falsa incapacidade de leitura. Leitura adicional do disco continua dependente da policy.

## Configuracao
Policy adicionada:

```json
{
  "mode": "governed_dev",
  "allow_conversation": true,
  "allow_reasoning": true,
  "allow_context_analysis": true,
  "allow_context_read": true,
  "allow_workspace_read": true,
  "allow_patch_preview": true,
  "allow_task_preview": true,
  "allow_direct_write": false,
  "allow_direct_shell": false,
  "file_write_policy": "ask",
  "shell_policy": "ask",
  "delete_policy": "ask_strong",
  "git_push_policy": "ask_strong"
}
```

Variaveis de ambiente `CONTINUE_*` podem sobrescrever a policy.

## Limites allowed / ask / denied
- Conversa: allowed.
- Matematica/raciocinio simples: allowed.
- Analise de contexto anexado: allowed.
- Leitura adicional de workspace: governada por policy.
- Patch preview: allowed quando policy habilita.
- Escrita real: ask/approval.
- Shell real: ask/approval.
- Delete/move/git push: ask_strong.
- Execucao direta `/v1/integrations/vscode/actions/execute`: continua bloqueada nesta fase.

## Testes executados
```text
python -m py_compile C:\Dev\AIpinho\src\aipinho\api\routers\continue_integration_router.py
python -m pytest C:\Dev\AIpinho\tests\integration\test_continue_openai_compat_api.py -q
```

Resultado:

```text
31 passed in 8.06s
```

## Cobertura nova relevante
- `continue_math_2_plus_2_responds_4`
- `continue_personality_question_is_not_operational_refusal`
- `continue_how_to_enable_features_returns_configuration_guidance`
- `continue_can_read_files_answer_is_capability_aware_not_false_incapable`
- `continue_agent_mode_answer_explains_context_vs_governed_tools`
- `continue_context_items_are_detected`
- `continue_app_tsx_context_can_be_analyzed_without_file_tool`
- `continue_terminal_context_can_be_summarized`
- `continue_git_diff_context_can_be_summarized`
- `continue_rules_context_does_not_trigger_refusal`
- `continue_write_request_creates_preview_or_approval_not_direct_write`
- `continue_shell_request_creates_preview_or_approval_not_direct_shell`
- `continue_delete_request_requires_strong_approval`
- `continue_streaming_never_returns_blank_for_simple_answer`
- `continue_policy_not_bypassed` coberto por testes de nao escrever/nao rodar shell.

## Smoke real
Backend 9088 foi reiniciado com elevacao porque o processo antigo `python (51860)` nao podia ser encerrado pelo usuario normal.

Smokes reais executados:

- Endpoint `POST /v1/chat/completions`, prompt `Voce consegue configurar personalidade e tom?`: retornou orientacao governada com `continue_intent=how_to_configure`.
- Endpoint `POST /v1/chat/completions`, prompt `Voce consegue ler arquivos?`: retornou resposta honesta sobre contexto anexado e leitura governada.
- Endpoint streaming com `curl.exe`, prompt `quanto e 2+2?`: retornou `chat.completion.chunk`, conteudo `2+2 = 4.`, `finish_reason=stop` e `data: [DONE]`.
- VS Code/Continue real, modo `Agent`, modelo `AIpinho Local`, prompt `ola`: renderizou `Ola! Como posso ajudar voce hoje?`.

## Riscos restantes
- A analise de contexto anexado nesta rodada e conservadora: reconhece e resume contexto recebido, mas a profundidade depende do ChatService/modelo quando for necessario raciocinio mais longo.
- Workspace read adicional ainda precisa ser conectado ao fluxo governado de leitura, quando a policy permitir.
- Patch preview via chat completions ainda retorna orientacao governada; execucao estruturada continua pelo endpoint de preview.

## Status por area
- CONVERSATION_READY: sim
- CONTEXT_ANALYSIS_READY: sim
- WORKSPACE_READ_READY: ask
- PATCH_PREVIEW_READY: sim
- FILE_WRITE_GOVERNED_READY: sim
- SHELL_GOVERNED_READY: sim
- POLICY_GOVERNANCE_READY: sim
- SPEAKER_TRUTH_READY: sim

## Veredito
CONTINUE_GOVERNED_DEV_READY

Motivo: conversa, matematica, configuracao, capacidade, streaming, contexto anexado e smoke real no Continue/VS Code estao cobertos. Escrita/shell permanecem governados por preview/approval, sem bypass.
