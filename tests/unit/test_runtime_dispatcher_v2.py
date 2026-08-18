from aipinho.schemas.semantic_runtime.isr import IntermediateSemanticRepresentation, ISREntity
from aipinho.services.runtime.runtime_contracts_v2_service import RuntimeContractsV2Service
from aipinho.services.runtime.runtime_dispatcher_v2_service import RuntimeDispatcherV2
from aipinho.services.semantic_runtime.contract_compiler import ContractCompiler


def _bundle(intent="repository_analysis"):
    isr = IntermediateSemanticRepresentation(
        intent=intent,
        scope="repository",
        entities=[ISREntity(entity_type="path", value=r"C:\Dev\AIpinho", confidence=0.95)],
        constraints={"read_only": intent == "repository_analysis"},
        expected_outputs=["report"],
        semantic_trace=[{"stage": "test", "status": "ready"}],
    )
    semantic = ContractCompiler().compile(isr)
    return RuntimeContractsV2Service().from_semantic_contracts(semantic)


def test_dispatch_routes_from_contracts_only():
    decision = RuntimeDispatcherV2().dispatch(_bundle())
    assert decision.status == "ready"
    assert decision.route is not None
    assert decision.route.operation_type == "project_analysis"
    assert "analyst" in decision.route.roles
    assert decision.trace[-1].stage == "route_resolved"


def test_dispatch_blocks_invalid_contract():
    bundle = _bundle()
    bundle.execution.safe_to_execute = True
    decision = RuntimeDispatcherV2().dispatch(bundle)
    assert decision.status == "blocked"
    assert "runtime_contract_compiler_must_not_enable_execution" in decision.blocked_reasons


def test_dispatch_permission_route_for_write_patch_requires_approval():
    decision = RuntimeDispatcherV2().dispatch(_bundle("write_patch"))
    assert decision.status == "ready"
    assert decision.route is not None
    assert set(decision.route.approvals_required) == {"apply_patch", "write_files"}
    assert "patch_planner" in decision.route.roles
