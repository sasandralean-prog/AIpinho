from aipinho.services.realtime.realtime_status_service import RealtimeStatusService
from aipinho.services.realtime.sync_heartbeat_service import SyncHeartbeatService
from aipinho.services.realtime.event_stream_service import EventStreamService


def test_realtime_status_heartbeat_and_event():
    assert RealtimeStatusService().status()["port"] == 9089
    assert SyncHeartbeatService().heartbeat()["status"] == "ok"
    assert "service_status_changed" in EventStreamService().status_event()
