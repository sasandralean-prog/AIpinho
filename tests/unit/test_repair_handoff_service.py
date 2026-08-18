import inspect
from aipinho.services.maintenance.repair_handoff_service import RepairHandoffService

def test_handoff_service_has_no_execution_primitive():
    source = inspect.getsource(RepairHandoffService)
    assert "execution_performed=False" in source
    assert "subprocess" not in source
