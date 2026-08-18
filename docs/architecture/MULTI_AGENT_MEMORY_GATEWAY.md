# Multi-Agent Memory Gateway

## Objetivo

O Multi-Agent Memory Gateway separa memorias privadas de agentes, memoria compartilhada governada e memoria operacional por projeto sem expor raw logs ou segredos ao fluxo normal. Ele foi criado para servir AIpinho, Lucio, Codex e Gemini como agentes distintos, mantendo rastreabilidade por run, evento e access log.

## Fluxo Canonico

1. Um agente solicita leitura, escrita ou candidatura de memoria.
2. O `AgentMemoryPolicyService` avalia namespace, dono, escopo, evidencia, segredo e raw.
3. O `AgentMemoryGatewayService` aplica redaction, cria registro ou candidato, emite eventos e atualiza `AgentRun`.
4. O `AgentMemoryGatewayStore` persiste registros, candidatos e access logs.
5. Delegacoes carregam apenas contexto sanitizado por `memory_refs`.
6. Tool Gateway cria candidatos de memoria para artifacts como best-effort, sem bloquear a ferramenta.

## Namespaces

- `memory:aipinho`: memoria privada do AIpinho.
- `memory:lucio`: memoria privada do Lucio.
- `memory:codex`: memoria privada do Codex.
- `memory:gemini`: memoria privada do Gemini.
- `memory:shared`: fatos, decisoes e licoes aceitas para uso compartilhado.
- `memory:project`: contexto operacional por workspace/projeto.
- `memory:regression`: padroes de falha e regressao.
- `memory:user_preferences`: preferencias explicitas do usuario, sem segredos.
- `memory:security`: notas restritas de seguranca, sem raw.

## Regras de Acesso

- Memoria privada so pode ser escrita pelo agente dono.
- Memoria compartilhada exige evidencia e entra como candidate quando nao ha validacao explicita.
- Segredos, raw logs e raciocinio interno oculto sao bloqueados antes da redaction.
- Leitura retorna apenas conteudo sanitizado.
- Search e context load registram `MemoryAccessLog`.
- Update de registro passa por policy, redaction e access log.
- Supersession marca memoria anterior como `superseded` e `stale`.
- Contradicoes de titulo/escopo sao marcadas como `contradicted` para revisao.

## Integracoes

- `AgentRun` agora possui `memory_refs_used`, `memory_refs_written`, `memory_candidates_created` e `memory_warnings`.
- Delegation carrega `memory_refs` e `memory_context_sanitized` sem transferir raw.
- Tool Gateway cria `MemoryCandidate` para artifacts governados quando possivel.
- Event Bus reconhece eventos `memory_*` como eventos de timeline/debugger.

## Endpoints

- `GET /api/v1/agents/memory/status`
- `GET /api/v1/agents/memory/namespaces`
- `GET /api/v1/agents/memory/{namespace}/records`
- `POST /api/v1/agents/memory/{namespace}/records`
- `GET /api/v1/agents/memory/records/{memory_id}`
- `PATCH /api/v1/agents/memory/records/{memory_id}`
- `POST /api/v1/agents/memory/search`
- `POST /api/v1/agents/memory/candidates`
- `GET /api/v1/agents/memory/candidates`
- `POST /api/v1/agents/memory/candidates/{candidate_id}/accept`
- `POST /api/v1/agents/memory/candidates/{candidate_id}/reject`
- `POST /api/v1/agents/memory/records/{memory_id}/supersede`
- `GET /api/v1/agents/memory/agents/{agent_id}/context`
- `GET /api/v1/agents/memory/runs/{run_id}`

## Limites Atuais

- Busca e ranking sao textuais/tokenizados, nao semanticos.
- Memory candidate de artifact e best-effort e nao deve bloquear execucao de ferramenta.
- Shared memory nao e autoaceita por padrao; exige revisao/validacao.
- O RAG legado nao foi removido neste sprint; a memoria nova e uma camada governada paralela.
