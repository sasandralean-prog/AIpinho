# G22 - Fix Request Two-Phase Lifecycle

Checkpoint: G22_FIX_REQUEST_TWO_PHASE_READY

Pedidos da classe "analise e corrija" foram separados em duas fases. A primeira resposta exige discovery/diagnostico read-only e nao cria approval de escrita imediatamente.

Fluxo implementado:

1. workspace_fix_request.
2. WORKSPACE_DISCOVERY_REQUIRED ou workspace_not_resolved.
3. Nenhum ApprovalRequest de escrita enquanto nao houver discovery_ref, analysis_ref, target_files e executable_plan_ref.
4. Approval de patch diagnostico sem analysis_ref e bloqueado antes da criacao do approval.

Evidencia:

- tests/governance/test_g22_fix_request_two_phase.py
- tests/governance/test_g25_behavioral_regression.py
- Matriz ampliada: 46 passed in 132.13s.

