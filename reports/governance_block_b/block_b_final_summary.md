# Bloco B Final - Canonical Governance Lifecycle Rewire

Status final: GOVERNANCE_BLOCK_B_CANONICAL_REWIRE_REQUIRES_PATCH

## Resumo

O lifecycle canonico agora e a primeira fonte de verdade para rotas publicas criticas. O fluxo `GovernanceLifecycleService -> CanonicalIntentRouter -> CanonicalPolicyService -> CanonicalRuntimeService -> CanonicalApprovalService -> SpeakerTruth` esta conectado aos endpoints principais de chat, chat persistente e Continue/OpenAI-compatible.

## Checkpoints

- G6: lifecycle core criado.
- G7: intent/router canonico reforcado e fechamento funcional aplicado.
- G8: policy/permission canonico conectado no lifecycle.
- G9: preview/approval canonicos conectados a `TaskDraft`, `TaskPreview` e `ApprovalRequest`.
- G10: completion/speaker truth canonico conectado.
- G11: rotas publicas criticas substituidas por `governance_lifecycle_router`.
- G12: recheck de rotas/configs/testes concluido.
- G13: quarentena parcial aplicada com manifest.

## Arquivos principais alterados nesta rodada

- `src/aipinho/services/governance/intent/canonical_intent_router.py`
- `src/aipinho/services/governance/lifecycle/canonical_public_chat_service.py`
- `src/aipinho/utils/diagnostics.py`
- `tests/governance/test_g7_functional_route_rewire.py`
- `tests/governance/test_g12_full_recheck.py`
- `tests/governance/test_canonical_lifecycle_trace.py`
- `tests/governance/test_no_legacy_operational_bypass.py`
- `tests/governance/test_legacy_import_forbidden.py`

## Quarentena

- Movido: `config/runtime/runtime_profiles.yaml`
- Destino: `quarantine/legacy/governance/2026-06-26/config/runtime/runtime_profiles.yaml`
- Substituto: `config/governance/runtime_profiles.yaml`

## Testes

```text
python -m py_compile C:\Dev\AIpinho\src\aipinho\utils\diagnostics.py C:\Dev\AIpinho\src\aipinho\services\governance\lifecycle\canonical_public_chat_service.py C:\Dev\AIpinho\src\aipinho\services\governance\intent\canonical_intent_router.py

python -m pytest tests\governance\test_lifecycle_core.py tests\governance\test_g11_canonical_public_routes.py tests\governance\test_g7_functional_route_rewire.py tests\governance\test_g12_full_recheck.py tests\governance\test_canonical_lifecycle_trace.py tests\governance\test_no_legacy_operational_bypass.py tests\governance\test_legacy_import_forbidden.py tests\integration\test_chat_api.py::test_post_chat_greeting_200 tests\integration\test_chat_api.py::test_chat_status_200 tests\integration\test_chat_runtime_parity_api.py::test_no_silent_message_after_persistent_chat_send -q
```

Resultado:

```text
25 passed in 71.14s
```

## Por que nao declarar READY total

Ainda existem routers e services legados montados para superficies residuais. Eles nao decidem mais as rotas criticas, mas ainda existem como compatibilidade e precisam de um bloco posterior para substituir endpoints secundarios e mover arquivos restantes para quarentena sem quebrar UX/API.

## Proxima recomendacao

Bloco C:

1. Mapear endpoints residuais de `chat_router.py` e `continue_integration_router.py`.
2. Migrar cada endpoint residual para rotas canonicas ou remover se duplicado.
3. Dobrar `ChatPermissionGrantService` e `ChatOperationRouterService` para adaptadores de sinal, nao decisores.
4. Rodar suite completa e entao mover routers/services legados para quarentena final.
