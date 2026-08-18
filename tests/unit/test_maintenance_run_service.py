from aipinho.repositories.maintenance.maintenance_run_repository import MaintenanceRunRepository
from aipinho.schemas.maintenance.contracts import MaintenanceRequest
from aipinho.services.maintenance.maintenance_run_service import MaintenanceRunService

def test_run_roundtrip_is_confined_to_repository(tmp_path):
    service = MaintenanceRunService(MaintenanceRunRepository(tmp_path / "runs"))
    run = service.create(MaintenanceRequest())
    assert service.get(run.run_id) == run
    assert len(service.list()) == 1
