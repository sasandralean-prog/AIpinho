from aipinho.schemas.maintenance.contracts import MaintenanceRequest
from aipinho.services.maintenance.maintenance_request_service import MaintenanceRequestService

def test_blocks_autocure_execution_actions():
    request = MaintenanceRequest(signals={"requested_actions": ["run_shell", "apply_patch"]})
    assert MaintenanceRequestService().validate(request) == ["autocure_action_blocked"]
