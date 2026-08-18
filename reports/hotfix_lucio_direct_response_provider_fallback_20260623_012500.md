# HOTFIX P0 - Lucio Direct Response Provider Fallback

Data: 2026-06-23

## Veredito

LUCIO_DIRECT_RESPONSE_FALLBACK_READY_WITH_WARNINGS

## Objetivo

Corrigir o fluxo de direct response do Lucio para tratar falhas de provider externo de forma segura, estruturada e util. Conversas simples de baixo risco podem receber fallback local seguro; perguntas nao triviais recebem `provider_unavailable` estruturado sem resposta inventada.

## Causa raiz

O roteamento do Lucio estava correto para conversa simples:

- route: `direct_response`
- route_type: `answer_directly`
- requires_local_execution: false
- requested_capabilities: []

Mas qualquer erro do provider OpenAI no caminho direto chamava `_fail(... status="failed")`, derrubando o run inteiro mesmo para saudacoes e fatos triviais. O erro ficava correto tecnicamente, mas inutil para uma conversa simples.

## Correcoes aplicadas

1. Novo service:
   - `C:\Dev\AIpinho\src\aipinho\services\lucio_agent\lucio_safe_fallback_service.py`

2. Classificador de fallback seguro:
   - `greeting`
   - `simple_social_reply`
   - `trivial_low_risk_fact`
   - `simple_help_request`
   - `nontrivial_requires_model`
   - `operational_request`

3. Fallback permitido apenas para:
   - saudacao simples;
   - fato trivial de baixo risco;
   - ajuda simples sem ferramenta.

4. Fallback proibido para:
   - pedido operacional;
   - decisao tecnica complexa;
   - fatos recentes;
   - resposta com fontes externas;
   - contexto juridico/medico/financeiro;
   - qualquer caso sem confianca local suficiente.

5. Metadata/debugger:
   - provider_error
   - fallback_used
   - fallback_type
   - fallback_category
   - fallback_reasons
   - model_invoked=false
   - provider_invocation_failed=true
   - local_execution_started=false
   - tool_invoked=false
   - final_status

6. Provider unavailable estruturado:
   - status visivel: `completed_with_warnings`
   - metadata.status: `provider_unavailable`
   - reason_code: erro do provider, por exemplo `openai_auth_error`
   - safe_to_retry=true

## Arquivos alterados

- `C:\Dev\AIpinho\src\aipinho\services\lucio_agent\lucio_safe_fallback_service.py`
- `C:\Dev\AIpinho\src\aipinho\services\lucio_agent\lucio_agent_service.py`
- `C:\Dev\AIpinho\tests\unit\test_lucio_agent_service.py`

## Testes adicionados/ajustados

- `test_lucio_simple_greeting_provider_auth_error_uses_safe_local_fallback`
- `test_lucio_trivial_fact_provider_auth_error_uses_safe_local_fallback`
- `test_lucio_nontrivial_question_provider_auth_error_returns_provider_unavailable`
- `test_lucio_operational_request_does_not_use_chat_fallback`
- Ajuste de `test_provider_internal_error_is_humanized_and_preserves_run` para o novo contrato estruturado.

## Validacoes executadas

1. Py compile:
   - `src\aipinho\services\lucio_agent\lucio_agent_service.py`
   - `src\aipinho\services\lucio_agent\lucio_safe_fallback_service.py`
   - `src\aipinho\services\lucio_agent\lucio_openai_client.py`
   - `src\aipinho\schemas\lucio_agent.py`

2. Testes unitarios:
   - `python -m pytest tests\unit\test_lucio_agent_service.py -q`
   - Resultado: `16 passed in 4.14s`

3. Testes integracao:
   - `python -m pytest tests\integration\test_lucio_agent_api.py tests\integration\test_multi_island_sprint10_11_routing.py -q`
   - Resultado: `6 passed in 11.40s`

## Smoke tests

### S1 - Saudacao simples com auth error

Prompt:
`Salve lucio tudo bem?`

Resultado:

- status: `completed_with_warnings`
- error_code: `openai_auth_error`
- fallback_used: true
- fallback_type: `local_safe_chat`
- fallback_category: `greeting`
- model_invoked: false
- local_execution_started: false
- tool_invoked: false
- secret_leaked: false

### S2 - Fato trivial com auth error

Prompt:
`Qual a cor do cavalo branco de Napoleao?`

Resultado:

- text: `Branco.`
- fallback_used: true
- fallback_category: `trivial_low_risk_fact`
- provider_error: `openai_auth_error`

### S3 - Pergunta nao trivial com auth error

Prompt:
`Explique profundamente a arquitetura de X com fontes recentes.`

Resultado:

- status: `completed_with_warnings`
- metadata.status: `provider_unavailable`
- fallback_used: false
- local_execution_started: false
- tool_invoked: false
- resposta nao inventa conteudo.

## Raw antes/depois

Antes:

- route: `direct_response`
- provider: `openai`
- status: `failed`
- error_code: `openai_auth_error`
- mensagem seca de erro tecnico.

Depois:

- route: `direct_response`
- provider_error registrado
- fallback local seguro quando permitido
- provider_unavailable estruturado quando fallback nao e permitido
- sem execucao local e sem delegacao para conversa simples.

## Riscos restantes

- Cobertura de fatos triviais e intencionalmente estreita para evitar falso conhecimento.
- Provider real ainda precisa credencial valida para respostas complexas.
- O fallback local nao substitui modelo nem web search.

## Proximos passos

- Expor melhor `provider_unavailable` no Debugger 2.0/Mobile se a UI ainda mostrar texto muito tecnico.
- Adicionar provider fallback real alternativo apenas se existir policy explicita para isso.

## Conclusao

O Lucio nao falha mais de forma seca em saudacao/fato trivial quando o provider recusa autenticacao. Ele tambem nao finge chamada real, nao usa ferramenta local para conversa simples e nao inventa resposta complexa quando o provider esta indisponivel.
