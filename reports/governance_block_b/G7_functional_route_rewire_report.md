# G7-FIX - Functional Route Rewire

Status: G7_FUNCTIONAL_ROUTE_REWIRE_READY

## Objetivo

Fechar a pendencia do G7: as rotas publicas nao podem deixar classificadores legados decidirem a intencao final antes do lifecycle canonico.

## O que foi alterado

- `src/aipinho/services/governance/intent/canonical_intent_router.py`
  - ampliou precedencia e sinais para operacoes de projeto, escrita, patch, shell/build/test e readonly/planning.
  - manteve `session_diagnostic` apenas para diagnostico explicito de sessao.
- `src/aipinho/services/governance/lifecycle/canonical_public_chat_service.py`
  - substituiu o fluxo anterior, que chamava `ChatService.respond()` primeiro.
  - agora chama `GovernanceLifecycleService.evaluate()` primeiro.
  - rotas de workspace query usam `PermissionStatusResponseService`.
  - comandos de approval usam `ChatApprovalCommandService`.
  - side effects criam `TaskDraft -> TaskPreview -> ApprovalRequest` apenas quando ha plano executavel e alvo concreto.
  - conversa comum ainda pode usar `ChatService` como provedor de conteudo, mas somente depois da decisao canonica.

## Evidencia funcional

- Prompt operacional de criacao de pasta cria `pending_approval` com `approval_id`, `preview_id` e `task_draft_id`.
- Prompt readonly com negacoes explicitas nao chama permission grant nem chat legado.
- Query de workspaces aprovados nao cai como conversa generica.
- `ChatService.respond` foi monkeypatchado para falhar em testes G7; prompts operacionais/read-only/query continuaram funcionando.

## Testes

- `tests/governance/test_g7_functional_route_rewire.py`
- `tests/governance/test_no_legacy_operational_bypass.py`

Resultado:

```text
10 passed in 31.58s
25 passed in 71.14s
```

## Limitacao honesta

`ChatService` e routers legados ainda existem para endpoints residuais e conversa comum. Para rotas publicas criticas, eles nao sao mais a fonte de verdade operacional.
