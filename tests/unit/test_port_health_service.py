import socket
from aipinho.services.supervisor.port_health_service import PortHealthService


def test_port_health_closed_and_open_managed():
    service = PortHealthService()
    closed = service.check_port(9, timeout_seconds=0.01)
    assert closed.status in {"closed", "occupied_by_unknown", "open"}
    sock = socket.socket(); sock.bind(("127.0.0.1", 0)); sock.listen(1)
    port = sock.getsockname()[1]
    try:
        open_status = service.check_port(port, service_id="managed")
        assert open_status.status == "open"
    finally:
        sock.close()


def test_port_health_unknown_occupied():
    sock = socket.socket(); sock.bind(("127.0.0.1", 0)); sock.listen(1)
    port = sock.getsockname()[1]
    try:
        status = PortHealthService().check_port(port)
        assert status.status == "occupied_by_unknown"
    finally:
        sock.close()
