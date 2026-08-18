# Bloco D - Behavioral Governance Firetest + Context Discovery Gate

Status final: GOVERNANCE_UNIFIED_SYSTEM_READY

## Checkpoints

- G20_CONTEXT_DISCOVERY_GATE_READY
- G21_READONLY_ANALYSIS_INTENT_READY
- G22_FIX_REQUEST_TWO_PHASE_READY
- G23_CAPABILITY_TRUTH_READY
- G24_APPROVAL_PREVIEW_QUALITY_GATE_READY
- G25_BEHAVIORAL_REGRESSION_READY
- G26_MULTICHANNEL_GOVERNANCE_FIRETEST_READY

## Arquivos criados

- src/aipinho/schemas/governance/context.py
- src/aipinho/schemas/governance/discovery.py
- src/aipinho/schemas/governance/capability_truth.py
- src/aipinho/services/governance/context/context_discovery_gate.py
- src/aipinho/services/governance/discovery/workspace_discovery_service.py
- src/aipinho/services/governance/capabilities/capability_truth_service.py
- src/aipinho/services/governance/preview_quality/approval_preview_quality_gate.py
- config/governance/context_discovery.yaml
- config/governance/preview_quality.yaml
- config/governance/capabilities.yaml
- tests/governance/test_g20_context_discovery_gate.py
- tests/governance/test_g21_readonly_analysis_intent.py
- tests/governance/test_g22_fix_request_two_phase.py
- tests/governance/test_g23_capability_truth.py
- tests/governance/test_g24_preview_quality_gate.py
- tests/governance/test_g25_behavioral_regression.py
- tests/governance/test_g26_multichannel_firetest.py
- reports/governance_block_d/*.md

## Arquivos alterados

- src/aipinho/schemas/governance/lifecycle.py
- src/aipinho/services/governance/lifecycle/governance_lifecycle_service.py
- src/aipinho/services/governance/lifecycle/canonical_public_chat_service.py
- src/aipinho/services/governance/lifecycle/public_route_lifecycle_service.py
- src/aipinho/services/governance/intent/canonical_intent_router.py
- src/aipinho/services/governance/policy/canonical_policy_service.py
- src/aipinho/services/governance/approval/canonical_approval_service.py
- src/aipinho/services/governance/runtime/canonical_runtime_service.py
- src/aipinho/services/orchestration/executable_plan_service.py
- src/aipinho/services/approvals/approval_service.py
- src/aipinho/api/routers/governance_lifecycle_router.py
- tests/governance/test_lifecycle_core.py

## Bypasses corrigidos

- Approval de escrita podia nascer com contexto insuficiente.
- Approval generico de write_files podia parecer executavel.
- Pedidos read-only de analise/plano podiam competir com intents operacionais.
- "Analise e corrija" podia pular discovery.
- Perguntas de capacidade podiam cair no ChatService generico.

## Evidencias

- G20-G26: 15 passed in 52.60s.
- Matriz ampliada B/C/D + integracao chat: 46 passed in 132.13s.
- py_compile nos arquivos principais: passed.

## Riscos remanescentes

- P1: QA visual/mobile real para approval button ainda deve ser executado em campo.
- P2: ChatService ainda existe como content provider para conversa comum, mas CapabilityTruthService intercepta perguntas operacionais de capacidade antes dele.
- P2: Discovery real de workspace permanece metadata/read-only inicial; analise profunda pode virar sprint separado com indexacao incremental.

## Proximo passo recomendado

Executar um firetest de campo com Mobile/Launcher reais, incluindo clique de approval por botao e uma task completa de discovery -> patch preview -> approval -> execution -> validation.

