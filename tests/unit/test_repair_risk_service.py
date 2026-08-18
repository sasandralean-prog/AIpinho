from aipinho.schemas.maintenance.contracts import RepairProposalRequest
from aipinho.services.maintenance.repair_risk_service import RepairRiskService
from tests.maintenance_helpers import diagnosis_model

def test_high_findings_require_approval():
    request = RepairProposalRequest(diagnosis_run_id="run", repair_type="patch_plan_preview", summary="Preview")
    result = RepairRiskService().assess(request, diagnosis_model())
    assert result.level == "high"
    assert result.approval_required is True
