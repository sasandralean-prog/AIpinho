# G25 - Behavioral Regression Suite

Checkpoint: G25_BEHAVIORAL_REGRESSION_READY

Foram adicionadas regressoes comportamentais permanentes para os bugs do Bloco D.

Cobertura adicionada:

- Read-only analysis nao cria approval/task/write.
- Fix request roda discovery primeiro.
- Approval nao e criado sem prompt/context, target files, executable plan, expected outputs ou validation plan.
- Perguntas de capacidade usam fonte canonica.
- Conversa generica nao pode negar runtime governado.
- Preview generico write_files e rejeitado.
- Direct chat, persistent chat e Continue produzem lifecycle equivalente para prompts read-only.
- Speaker Truth nao declara sucesso antes de completion/validation.

Evidencia:

- tests/governance/test_g20_context_discovery_gate.py
- tests/governance/test_g21_readonly_analysis_intent.py
- tests/governance/test_g22_fix_request_two_phase.py
- tests/governance/test_g23_capability_truth.py
- tests/governance/test_g24_preview_quality_gate.py
- tests/governance/test_g25_behavioral_regression.py
- tests/governance/test_g26_multichannel_firetest.py

Resultado:

- G20-G26: 15 passed in 52.60s.
- Matriz ampliada: 46 passed in 132.13s.

