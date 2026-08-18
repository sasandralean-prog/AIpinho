# G26 - Multichannel Governance Firetest

Checkpoint: G26_MULTICHANNEL_GOVERNANCE_FIRETEST_READY

Cenarios validados por testes automatizados:

1. Conversa simples pelo direct chat.
2. Pergunta de capacidade pelo direct chat.
3. Planejamento/read-only pelo direct chat.
4. Analise e corrija com discovery antes de approval.
5. Continue /v1/chat/completions com capability truth.
6. VSCode Continue action preview/execute no caminho canonico.
7. Persistent chat com lifecycle equivalente para prompt read-only.
8. Speaker Truth sem falso sucesso.

Evidencias de comportamento:

- Nenhum approval de escrita antes de discovery/context para fix request.
- Nenhum approval sem executable_plan_ref, target_files, expected_outputs e validation_plan.
- Pedido de relatorio/plano nao vira write_files.
- Capability truth nao e respondido pelo provider generico.
- Continue e persistent chat retornam GovernanceLifecycleSnapshot.

Resultado:

- Matriz ampliada: 46 passed in 132.13s.

Limite honesto:

- Approval por botao real de UI/mobile nao foi clicado neste sprint; a cobertura automatizada valida o service path e a rota canonica. QA visual/mobile fisico deve ficar para um firetest de campo.

