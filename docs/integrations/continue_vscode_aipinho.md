# Integracao AIpinho com Continue / VS Code

## Objetivo
Conectar a AIpinho ao Continue do VS Code como modelo local usando endpoint OpenAI-compatible, sem depender de OpenAI pago.

## Versionamento
- Continue extension instalada: `continue.continue-2.0.0-win32-x64`
- Versao detectada: `2.0.0`

## Base URL recomendada
- `http://127.0.0.1:9088/v1`

## Modelos suportados
- `aipinho-local`
- `aipinho-agent`
- Modelos desconhecidos retornam erro estruturado `model_not_found`.

## Configuracao do Continue
O Continue pode usar `provider: openai` apontando para o adapter local da AIpinho.

Exemplo de `config.yaml`:

```yaml
name: PinhoLocalAI Config
version: 1.0.0
schema: v1

models:
  - name: AIpinho Local
    provider: openai
    model: aipinho-local
    apiBase: http://127.0.0.1:9088/v1
    apiKey: aipinho-local-token
    roles:
      - chat
      - edit
      - apply

context:
  - provider: code
  - provider: diff
  - provider: terminal
  - provider: problems
```

## Endpoints OpenAI-compatible
A AIpinho expoe:

- `GET /v1/models`
- `GET /v1/models/{model_id}`
- `POST /v1/chat/completions`

`POST /v1/chat/completions` aceita `stream=false` e `stream=true`.

Para `stream=true`, a AIpinho responde em `text/event-stream` com chunks `chat.completion.chunk` e finaliza com:

```text
data: [DONE]
```

## Como testar
1. Inicie o backend AIpinho local na porta `9088`.
2. Configure o Continue com `provider: openai` e `apiBase: http://127.0.0.1:9088/v1`.
3. Abra o chat do Continue e envie `Ola`.
4. Verifique se a resposta vem da AIpinho local.

## Seguranca e autenticacao
- Se `CONTINUE_API_TOKEN` estiver configurado, envie `Authorization: Bearer <token>`.
- Em desenvolvimento local, `aipinho-local-token` pode ser permitido por policy/env.
- Tokens nao devem ser colocados em logs, raw/debug ou reports.

## Modo governed_dev
A rota OpenAI-compatible opera como assistente de programacao governado.

Permitido diretamente pela resposta do Continue:

- conversa e raciocinio simples;
- perguntas sobre capacidade/configuracao;
- analise de contexto anexado pelo Continue, como `@App.tsx`, `@Terminal`, `@Git Diff` e `@rules/...`;
- sugestoes textuais e explicacoes de codigo.

Governado por preview/approval:

- criar, alterar, mover ou deletar arquivos;
- aplicar patch;
- rodar shell;
- executar build/testes;
- comandos git com side effect.

Flags principais:

```text
CONTINUE_MODE=governed_dev
CONTINUE_ALLOW_CONVERSATION=true
CONTINUE_ALLOW_REASONING=true
CONTINUE_ALLOW_CONTEXT_ANALYSIS=true
CONTINUE_ALLOW_CONTEXT_READ=true
CONTINUE_ALLOW_WORKSPACE_READ=true
CONTINUE_ALLOW_PATCH_PREVIEW=true
CONTINUE_ALLOW_TASK_PREVIEW=true
CONTINUE_ALLOW_DIRECT_WRITE=false
CONTINUE_ALLOW_DIRECT_SHELL=false
CONTINUE_FILE_WRITE_POLICY=ask
CONTINUE_SHELL_POLICY=ask
CONTINUE_DELETE_POLICY=ask_strong
CONTINUE_GIT_PUSH_POLICY=ask_strong
```

O streaming usa chunks OpenAI-compatible em `text/event-stream` e finaliza com `data: [DONE]`.

## Endpoints de governanca existentes
### `POST /api/v1/integrations/vscode/actions/preview`
Gera preview governado para revisao posterior.

Exemplo de payload minimo:

```json
{
  "workspace_path": "C:/Dev/AIpinho",
  "action_type": "modify_file",
  "target_paths": ["README.md"],
  "content": "Conteudo atualizado...",
  "reason": "Solicitacao do VS Code Continue",
  "source": "vscode_continue"
}
```

### `POST /api/v1/integrations/vscode/actions/execute`
Nesta fase, a execucao direta via Continue esta desabilitada e retorna `403 continue_connection_phase_no_write_or_shell`.

Exemplo de payload que sera bloqueado nesta fase:

```json
{
  "approval_id": "approval_<id>",
  "source": "vscode_continue"
}
```

## Proximos passos
- Reativar execucao de acoes do Continue somente via bridge governada com preview, policy, approval, apply e validation.
- Testar com uma sessao real do Continue no VS Code.
