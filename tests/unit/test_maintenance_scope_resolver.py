from aipinho.schemas.maintenance.contracts import MaintenanceRequest, MaintenanceScope
from aipinho.services.maintenance.maintenance_scope_resolver import MaintenanceScopeResolver

def test_scope_is_preserved_without_inference():
    scope = MaintenanceScope(task_id="task_unit", event_id="event_unit")
    assert MaintenanceScopeResolver().resolve(MaintenanceRequest(scope=scope)) == scope
