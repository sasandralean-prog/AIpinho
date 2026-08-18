from aipinho.schemas.runtime.planner_v2 import ExecutionPlanSerializer
from aipinho.schemas.semantic_runtime.isr import IntermediateSemanticRepresentation, ISREntity
from aipinho.services.runtime.planner_v2_service import PlannerV2
from aipinho.services.runtime.runtime_contracts_v2_service import RuntimeContractsV2Service
from aipinho.services.semantic_runtime.contract_compiler import ContractCompiler


def _bundle(intent="repository_analysis"):
    isr = IntermediateSemanticRepresentation(
        intent=intent,
        scope="repository",
        entities=[ISREntity(entity_type="path", value=r"C:\Dev\AIpinho", confidence=0.95)],
        permissions_requested=["write_patch"] if intent == "write_patch" else [],
        expected_outputs=["report"],
        semantic_trace=[{"stage": "test", "status": "ready"}],
    )
    return RuntimeContractsV2Service().from_semantic_contracts(ContractCompiler().compile(isr))


def test_planner_v2_builds_plan_from_contract_bundle():
    plan = PlannerV2().plan(_bundle())
    assert plan.status == "planned"
    assert plan.stages[0].stage_type == "validate_contracts"
    assert plan.stages[-1].stage_type == "validation"
    assert "report" in plan.artifacts_expected


def test_planner_v2_adds_approval_dependency_for_patch():
    plan = PlannerV2().plan(_bundle("write_patch"))
    stage_types = [stage.stage_type for stage in plan.stages]
    assert "approval" in stage_types
    assert "write_patch" in plan.approvals_required
    execute = next(stage for stage in plan.stages if stage.stage_id == "stage_03_execute")
    assert "stage_02_wait_approval" in execute.depends_on


def test_execution_plan_serialization_roundtrip():
    plan = PlannerV2().plan(_bundle())
    payload = ExecutionPlanSerializer.to_json(plan)
    restored = ExecutionPlanSerializer.from_json(payload)
    assert restored.model_dump(mode="json") == plan.model_dump(mode="json")
