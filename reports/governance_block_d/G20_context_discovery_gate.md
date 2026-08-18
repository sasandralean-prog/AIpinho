# G20 - Context & Discovery Gate

Checkpoint: G20_CONTEXT_DISCOVERY_GATE_READY

O ContextDiscoveryGate foi conectado ao GovernanceLifecycleService antes da criacao de ApprovalRequest para operacoes com side effect em policy ask.

Regras validadas:

- Approval de escrita sem prompt/contexto visivel retorna APPROVAL_NOT_CREATED_PROMPT_CONTEXT_MISSING.
- Approval de escrita sem executable_plan_ref retorna APPROVAL_NOT_CREATED_NO_EXECUTABLE_PLAN.
- Approval de escrita sem workspace resolvido retorna APPROVAL_NOT_CREATED_WORKSPACE_NOT_RESOLVED.
- Approval de escrita sem target files retorna APPROVAL_NOT_CREATED_NO_TARGET_FILES.
- Approval de escrita sem expected outputs retorna APPROVAL_NOT_CREATED_NO_EXPECTED_OUTPUTS.
- Approval de escrita sem validation plan retorna APPROVAL_NOT_CREATED_NO_VALIDATION_PLAN.
- Pedido diagnostico+correcao com escrita exige discovery_ref/analysis_ref antes de approval.

Evidencia:

- tests/governance/test_g20_context_discovery_gate.py
- Matriz ampliada: 46 passed in 132.13s.

