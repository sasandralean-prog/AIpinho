from aipinho.services.maintenance.maintenance_plane_service import MaintenancePlaneService

def test_status_is_supervised_and_never_autonomous():
    status = MaintenancePlaneService().status()
    assert status.enabled is True
    assert status.autonomous_apply is False
    assert status.direct_patch_apply_enabled is False
    assert status.invariant_count == 15
