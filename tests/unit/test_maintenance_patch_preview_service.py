import inspect
from aipinho.services.maintenance.maintenance_patch_preview_service import MaintenancePatchPreviewService

def test_patch_preview_delegates_without_apply():
    source = inspect.getsource(MaintenancePatchPreviewService)
    assert "patch_planning_pipeline" in source
    assert "apply_performed" not in source or "apply_performed=True" not in source
