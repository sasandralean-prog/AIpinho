from aipinho.services.supervisor.resource_monitor_service import ResourceMonitorService


def test_resource_snapshot_has_disk_and_no_model_runtime():
    snapshot = ResourceMonitorService().snapshot()
    assert snapshot.model_runtime_active is False
    assert snapshot.disk_percent is None or snapshot.disk_percent >= 0
