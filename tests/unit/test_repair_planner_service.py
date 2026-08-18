from aipinho.schemas.maintenance.contracts import RepairProposalRequest
from aipinho.services.maintenance.repair_planner_service import RepairPlannerService
from tests.maintenance_helpers import diagnosis_model

def test_planner_outputs_preview_steps_and_validation():
    request = RepairProposalRequest(diagnosis_run_id="run", repair_type="patch_plan_preview", summary="Preview", proposed_steps=["Inspect"], validation_checks=["unit"])
    plan = RepairPlannerService().plan(request, diagnosis_model())
    assert plan.steps[0].side_effect is False
    assert plan.validation.execution_performed is False
