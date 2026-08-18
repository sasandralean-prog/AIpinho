import inspect
from aipinho.services.maintenance.maintenance_config_change_preview_service import MaintenanceConfigChangePreviewService

def test_config_preview_never_writes_target_config():
    source = inspect.getsource(MaintenanceConfigChangePreviewService)
    assert "write_performed=True" not in source
    assert "preview_only" in source
