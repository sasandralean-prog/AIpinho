from pathlib import Path
import yaml
from aipinho.services.supervisor.service_manifest_service import ServiceManifestService


def test_load_valid_manifest_has_four_services_and_monitor_not_restartable():
    manifest = ServiceManifestService().load()
    assert len(manifest.services) == 4
    assert manifest.services["core_backend"].port == 9088
    assert manifest.services["core_backend"].health_url.endswith("/api/v1/health")
    assert manifest.services["artifact_service"].health_url.endswith("/api/v1/health")
    assert manifest.services["monitor_supervisor"].port == 9099
    assert manifest.services["monitor_supervisor"].restartable is False
    assert manifest.services["monitor_supervisor"].health_url.endswith("/api/v1/health")
    assert ServiceManifestService().validate(manifest)["status"] == "ok"


def test_duplicate_port_is_degraded(tmp_path: Path):
    data = ServiceManifestService().load_raw()
    data["services"]["artifact_service"]["port"] = 9088
    path = tmp_path / "manifest.yaml"
    path.write_text(yaml.safe_dump(data), encoding="utf-8")
    status = ServiceManifestService(path).validate()
    assert status["status"] == "degraded"
    assert any("duplicate_port:9088" in item for item in status["warnings"])


def test_missing_command_profile_is_degraded(tmp_path: Path):
    data = ServiceManifestService().load_raw()
    data["services"]["core_backend"]["command_profile"] = "missing_profile"
    path = tmp_path / "manifest.yaml"
    path.write_text(yaml.safe_dump(data), encoding="utf-8")
    status = ServiceManifestService(path).validate()
    assert "missing_command_profile:core_backend:missing_profile" in status["warnings"]


def test_recursive_aggregate_health_url_is_degraded(tmp_path: Path):
    data = ServiceManifestService().load_raw()
    data["services"]["core_backend"]["health_url"] = "http://127.0.0.1:9088/api/v1/status"
    path = tmp_path / "manifest.yaml"
    path.write_text(yaml.safe_dump(data), encoding="utf-8")
    status = ServiceManifestService(path).validate()
    assert status["status"] == "degraded"
    assert "recursive_health_url:core_backend:/api/v1/status" in status["warnings"]
