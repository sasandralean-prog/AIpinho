# Memory Governance Model

## Principios

- Memoria nao e RAG bruto.
- Memoria nao armazena raw logs.
- Memoria nao armazena segredos.
- Memoria privada preserva autonomia de cada agente.
- Memoria compartilhada exige evidencia e validacao.
- Toda leitura/escrita relevante deve ser rastreavel por access log.

## Estados

- `candidate`: memoria proposta, ainda sem aceitacao.
- `validated`: memoria aceita para uso governado.
- `contradicted`: memoria conflita com outra no mesmo escopo.
- `stale`: memoria envelhecida ou marcada como desatualizada.
- `superseded`: memoria substituida por outra.
- `rejected`: candidato rejeitado.

## Politicas

As politicas ficam em `config/agents/memory_gateway_policy.yaml`.

Controles principais:

- `private_agent_memory_enabled`
- `shared_enabled`
- `auto_write_private`
- `auto_create_candidates`
- `auto_accept_shared_with_strong_evidence`
- `require_evidence_for_shared`
- `block_raw_access_by_default`
- `block_secret_storage`
- `enable_contradiction_detection`
- `enable_freshness`
- `max_context_records_per_run`
- `max_context_chars_per_run`
- `max_record_chars`

## Bloqueios

O gateway bloqueia:

- escrita de um agente em memoria privada de outro agente;
- conteudo com padrao de secret/API key/token;
- raw logs;
- chain-of-thought/raciocinio interno;
- memoria compartilhada sem evidencia quando a policy exigir;
- atualizacao de registro que introduza conteudo sensivel.

## Access Logs

Cada read/write/update/validate/reject/supersede gera `MemoryAccessLog` com:

- `memory_id` ou `candidate_id`;
- `agent_id`;
- `session_id` e `run_id`, quando presentes;
- `access_type`;
- `reason`;
- `metadata_sanitized`.

## Eventos

Eventos canonicos:

- `memory_search_started`
- `memory_search_completed`
- `memory_context_loaded`
- `memory_context_attached_to_delegation`
- `memory_candidate_created`
- `memory_candidate_accepted`
- `memory_candidate_rejected`
- `memory_written`
- `memory_updated`
- `memory_superseded`
- `memory_contradiction_detected`
- `memory_marked_stale`
- `memory_access_denied`
- `memory_validation_started`
- `memory_validation_passed`
- `memory_validation_failed`

## Uso em Runs e Delegacoes

`AgentRun` guarda as referencias usadas/escritas para que Speaker, Debugger e auditoria possam explicar de onde veio o contexto. Delegacoes recebem `memory_context_sanitized`, nunca raw, e apontam para `memory_refs`.

## Regra de Produto

Memoria deve aumentar continuidade operacional sem contaminar o raciocinio com lixo historico. Conhecimento reutilizavel entra como memoria curada; raw, stack traces extensos, segredo e detalhe specific-case ficam fora.
