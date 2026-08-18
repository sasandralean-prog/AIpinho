from aipinho.schemas.maintenance.contracts import MaintenanceConfigChangePreview, MaintenancePatchPreview, MaintenanceRollbackPlan, RepairHandoff, RepairApprovalRequest

def test_repair_contracts_default_to_non_execution():
    patch = MaintenancePatchPreview(proposal_id="proposal", summary="preview")
    config = MaintenanceConfigChangePreview(proposal_id="proposal", summary="preview")
    rollback = MaintenanceRollbackPlan(proposal_id="proposal")
    handoff = RepairHandoff(proposal_id="proposal", target_owner="policy_kernel", approval=RepairApprovalRequest(approval_required=True, reason="risk", requested_action="patch"))
    assert patch.apply_performed is False
    assert config.write_performed is False
    assert rollback.execution_performed is False
    assert handoff.execution_performed is False
