from aipinho.repositories.maintenance.maintenance_run_repository import MaintenanceRunRepository
from aipinho.repositories.maintenance.repair_proposal_repository import RepairProposalRepository
from aipinho.schemas.maintenance.contracts import MaintenanceRun, RepairProposalRequest
from aipinho.services.maintenance.maintenance_run_service import MaintenanceRunService
from aipinho.services.maintenance.repair_proposal_service import RepairProposalService
from tests.maintenance_helpers import NullEmitter, diagnosis_model

def test_proposal_requires_completed_diagnosis_and_never_executes(tmp_path):
    runs = MaintenanceRunService(MaintenanceRunRepository(tmp_path / "runs"))
    run = MaintenanceRun(request_id="req", mode="diagnose", status="completed")
    run.diagnosis = diagnosis_model(run.run_id)
    runs.save(run)
    service = RepairProposalService(runs, RepairProposalRepository(tmp_path / "proposals"), NullEmitter())
    proposal = service.propose(RepairProposalRequest(diagnosis_run_id=run.run_id, repair_type="patch_plan_preview", summary="Preview"))
    assert proposal.execution_performed is False
    assert proposal.evidence_refs
