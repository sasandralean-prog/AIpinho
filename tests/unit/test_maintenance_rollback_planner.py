import inspect
from aipinho.services.maintenance.maintenance_rollback_planner import MaintenanceRollbackPlanner

def test_rollback_is_plan_only():
    source = inspect.getsource(MaintenanceRollbackPlanner)
    assert "execution_performed=True" not in source
    assert "approved pre-change snapshot" in source
