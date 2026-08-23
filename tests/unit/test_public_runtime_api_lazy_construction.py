from __future__ import annotations

from aipinho.schemas.public_runtime_api import PublicRuntimeRequest
from aipinho.services import public_runtime_api_service as service
from aipinho.services.public_runtime_api_service import PublicRuntimeAPI


class _NoopTelemetry:
    def record(self, request) -> None:
        return None


def test_public_runtime_api_constructor_does_not_construct_execution_bridge(monkeypatch):
    def fail_bridge():
        raise AssertionError("execution bridge constructed eagerly")

    monkeypatch.setattr(service, "PublicRuntimeExecutionBridge", fail_bridge)

    PublicRuntimeAPI()


def test_version_contracts_modules_runtime_do_not_construct_execution_bridge(monkeypatch):
    def fail_bridge():
        raise AssertionError("execution bridge constructed for readonly GET")

    monkeypatch.setattr(service, "PublicRuntimeExecutionBridge", fail_bridge)
    api = PublicRuntimeAPI()

    version = api.version()
    contracts = api.contracts_view()
    modules = api.modules()
    runtime = api.runtime()

    assert version["api_version"] == "1.0"
    assert "app_version" in version
    assert contracts["mutates_runtime"] is False
    assert isinstance(contracts["contracts"], list)
    assert modules["gateway_required"] is True
    assert modules["kernel_required"] is True
    assert isinstance(modules["modules"], list)
    assert runtime["gateway_required"] is True
    assert runtime["kernel_required"] is True
    assert "status" in runtime


def test_execution_bridge_is_lazy_and_reused(monkeypatch):
    constructed: list[object] = []

    class FakeBridge:
        def __init__(self) -> None:
            constructed.append(self)

    monkeypatch.setattr(service, "PublicRuntimeExecutionBridge", FakeBridge)

    api = PublicRuntimeAPI()

    first = api.execution_bridge
    second = api.execution_bridge

    assert first is second
    assert constructed == [first]


def test_injected_execution_bridge_is_authoritative(monkeypatch):
    def fail_bridge():
        raise AssertionError("injected bridge was replaced")

    monkeypatch.setattr(service, "PublicRuntimeExecutionBridge", fail_bridge)
    injected = object()

    api = PublicRuntimeAPI(execution_bridge=injected)  # type: ignore[arg-type]

    assert api.execution_bridge is injected


def test_handle_constructs_execution_bridge_only_when_execution_path_is_used(monkeypatch):
    calls: list[tuple[PublicRuntimeRequest, dict[str, object], str]] = []

    class FakeBridge:
        def __init__(self) -> None:
            self.instance_id = len(calls)

        def execute(self, request: PublicRuntimeRequest, *, contract: dict[str, object], gateway_status: str) -> dict[str, object]:
            calls.append((request, contract, gateway_status))
            return {"status": gateway_status}

    monkeypatch.setattr(service, "PublicRuntimeExecutionBridge", FakeBridge)
    api = PublicRuntimeAPI(telemetry=_NoopTelemetry())  # type: ignore[arg-type]

    response = api.handle(
        PublicRuntimeRequest(
            operation="chat",
            client_id="lazy_test",
            client_type="rest",
            api_version="1.0",
            contract={"contract_type": "conversation"},
            payload={"message": "hello"},
        )
    )

    assert response.status == "accepted"
    assert len(calls) == 1
    request, contract, gateway_status = calls[0]
    assert request.operation == "chat"
    assert contract["contract_type"] == "conversation"
    assert gateway_status == "accepted"
    assert api.execution_bridge is api.execution_bridge
