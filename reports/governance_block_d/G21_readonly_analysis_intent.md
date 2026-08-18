# G21 - Read-only Analysis Intent Hardening

Checkpoint: G21_READONLY_ANALYSIS_INTENT_READY

O CanonicalIntentRouter agora diferencia analise, auditoria, diagnostico, relatorio e plano de acao como workspace_analysis_readonly quando nao ha pedido operacional concreto de escrita.

Comportamento esperado validado:

- "analise os arquivos e crie um plano" nao cria write approval.
- "responda com relatorio do que mudar" nao vira project_generation nem patch_request.
- "diagnostique problemas de UX" fica read-only.
- Rotas publicas nao chamam ChatService generico para decidir essa classe.

Evidencia:

- tests/governance/test_g21_readonly_analysis_intent.py
- tests/governance/test_g25_behavioral_regression.py
- Matriz ampliada: 46 passed in 132.13s.

