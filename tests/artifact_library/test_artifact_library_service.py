from __future__ import annotations

import base64
import io
import zipfile
from pathlib import Path

from fastapi.testclient import TestClient

from aipinho.api.routers import artifact_status_router
from aipinho.main import app
from aipinho.schemas.agents.tool_gateway import ArtifactUploadRequest
from aipinho.schemas.artifacts.artifact_library import ArtifactBundleRequest, ArtifactContextUseRequest, ArtifactPreviewRequest, ArtifactQuery
from aipinho.services.agents.agent_tool_gateway_service import AgentToolGatewayService
from aipinho.services.agents.agent_tool_invocation_store import AgentToolInvocationStore
from aipinho.services.artifacts.artifact_library_service import ArtifactLibraryService


def _env(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("AIPINHO_TOOL_GATEWAY_ROOT", str(tmp_path / "tool_gateway"))
    monkeypatch.setenv("AIPINHO_AGENT_KERNEL_ROOT", str(tmp_path / "agent_kernel"))
    monkeypatch.setenv("AIPINHO_ARTIFACT_LIBRARY_ROOT", str(tmp_path / "artifact_library"))


def _service(tmp_path: Path) -> tuple[ArtifactLibraryService, AgentToolGatewayService]:
    store = AgentToolInvocationStore(root=tmp_path / "tool_gateway")
    gateway = AgentToolGatewayService(store=store)
    service = ArtifactLibraryService(tool_store=store, gateway=gateway, index_path=tmp_path / "artifact_library" / "ARTIFACT_INDEX.json")
    return service, gateway


def _upload(gateway: AgentToolGatewayService, *, filename: str, content: bytes | str, content_type: str = "text/plain", metadata: dict[str, object] | None = None):
    if isinstance(content, bytes):
        payload = base64.b64encode(content).decode("ascii")
        encoding = "base64"
    else:
        payload = content
        encoding = "text"
    return gateway.upload_artifact(
        agent_id="aipinho",
        session_id="session_test",
        request=ArtifactUploadRequest(
            filename=filename,
            content_type=content_type,
            content=payload,
            encoding=encoding,
            origin="test",
            metadata_sanitized=metadata or {},
        ),
    )


def test_artifact_library_index_created_and_query_by_session(tmp_path: Path, monkeypatch) -> None:
    _env(tmp_path, monkeypatch)
    service, gateway = _service(tmp_path)
    artifact = _upload(gateway, filename="ready.md", content="# Ready\n", content_type="text/markdown", metadata={"evidence_refs": ["test:evidence"]})

    result = service.query(ArtifactQuery(session_id="session_test"))

    assert result.total == 1
    assert result.items[0].artifact_id == artifact.artifact_id
    assert result.items[0].status == "ready"
    assert result.items[0].download_endpoint == f"/api/v1/artifacts/{artifact.artifact_id}/download"
    assert "token" not in result.items[0].download_endpoint.lower()


def test_artifact_ready_requires_existing_file(tmp_path: Path, monkeypatch) -> None:
    _env(tmp_path, monkeypatch)
    service, gateway = _service(tmp_path)
    artifact = _upload(gateway, filename="missing.md", content="# Missing\n")
    path = gateway.store.artifact_content_path(artifact)
    path.unlink()

    record = service.get(artifact.artifact_id)

    assert record.status == "failed"
    assert record.error_reason == "artifact_file_missing"
    assert record.download_endpoint is None


def test_artifact_preview_markdown_sanitized(tmp_path: Path, monkeypatch) -> None:
    _env(tmp_path, monkeypatch)
    service, gateway = _service(tmp_path)
    artifact = _upload(gateway, filename="secret.md", content=Path("tests/fixtures/artifact_library/fake_secret_report.md").read_text(encoding="utf-8"), content_type="text/markdown")

    preview = service.preview(ArtifactPreviewRequest(artifact_id=artifact.artifact_id, preview_mode="markdown"))

    assert preview.preview_available is True
    assert "[REDACTED]" in (preview.content_preview or "")
    assert "should_not_leak" not in (preview.content_preview or "")


def test_artifact_preview_zip_listing_and_traversal_detection(tmp_path: Path, monkeypatch) -> None:
    _env(tmp_path, monkeypatch)
    service, gateway = _service(tmp_path)
    memory = io.BytesIO()
    with zipfile.ZipFile(memory, "w") as archive:
        archive.writestr("safe/report.txt", "ok")
        archive.writestr("../escape.txt", "bad")
    artifact = _upload(gateway, filename="unsafe.zip", content=memory.getvalue(), content_type="application/zip")

    preview = service.preview(ArtifactPreviewRequest(artifact_id=artifact.artifact_id, preview_mode="zip_listing"))

    assert any(entry["filename"] == "safe/report.txt" for entry in preview.zip_entries)
    assert any("zip_path_traversal" in error for error in preview.errors)
    assert preview.preview_available is False


def test_artifact_binary_preview_metadata_only(tmp_path: Path, monkeypatch) -> None:
    _env(tmp_path, monkeypatch)
    service, gateway = _service(tmp_path)
    artifact = _upload(gateway, filename="payload.bin", content=b"\x00\x01\x02", content_type="application/octet-stream")

    preview = service.preview(ArtifactPreviewRequest(artifact_id=artifact.artifact_id, preview_mode="text"))

    assert preview.preview_available is True
    assert preview.content_preview is None
    assert "binary_preview_metadata_only" in preview.warnings


def test_artifact_use_as_context_text_allowed_and_binary_denied(tmp_path: Path, monkeypatch) -> None:
    _env(tmp_path, monkeypatch)
    service, gateway = _service(tmp_path)
    text_artifact = _upload(gateway, filename="context.txt", content="context body")
    binary_artifact = _upload(gateway, filename="context.bin", content=b"\x00\x01", content_type="application/octet-stream")

    allowed = service.use_as_context(ArtifactContextUseRequest(artifact_id=text_artifact.artifact_id, session_id="session_test"))
    denied = service.use_as_context(ArtifactContextUseRequest(artifact_id=binary_artifact.artifact_id, session_id="session_test"))

    assert allowed.status == "allowed"
    assert "context body" in (allowed.context_preview or "")
    assert denied.status == "blocked"
    assert denied.reason_code == "artifact_context_denied_type"


def test_artifact_bundle_created_with_manifest(tmp_path: Path, monkeypatch) -> None:
    _env(tmp_path, monkeypatch)
    service, gateway = _service(tmp_path)
    first = _upload(gateway, filename="one.txt", content="one")
    second = _upload(gateway, filename="two.txt", content="two")

    bundle = service.create_bundle(ArtifactBundleRequest(artifact_ids=[first.artifact_id, second.artifact_id], session_id="session_test", bundle_name="bundle.zip"))

    assert bundle.bundle_artifact.status == "ready"
    assert bundle.bundle_artifact.artifact_type == "zip"
    artifact, content = gateway.read_artifact_bytes(bundle.bundle_artifact.artifact_id)
    with zipfile.ZipFile(io.BytesIO(content)) as archive:
        assert "BUNDLE_MANIFEST.json" in archive.namelist()


def test_artifact_cleanup_preview_preserves_evidence(tmp_path: Path, monkeypatch) -> None:
    _env(tmp_path, monkeypatch)
    service, gateway = _service(tmp_path)
    preserved = _upload(gateway, filename="preserved.txt", content="keep", metadata={"evidence_refs": ["run:123"]})
    missing = _upload(gateway, filename="missing.txt", content="remove")
    gateway.store.artifact_content_path(missing).unlink()

    preview = service.cleanup_preview()

    assert preserved.artifact_id in preview.preserved_artifacts
    assert any(item.artifact_id == missing.artifact_id for item in preview.candidate_artifacts)
    assert preview.requires_confirmation is True


def test_artifact_mobile_view_model_and_download_auth(tmp_path: Path, monkeypatch) -> None:
    _env(tmp_path, monkeypatch)
    gateway = AgentToolGatewayService()
    artifact = _upload(gateway, filename="mobile.txt", content="mobile")

    class AllowToken:
        def validate_authorization(self, authorization: str | None) -> bool:
            return bool(authorization and authorization.startswith("Bearer "))

    monkeypatch.setattr(artifact_status_router, "LocalTokenService", lambda: AllowToken())
    client = TestClient(app)

    mobile = client.get("/api/v1/mobile/view-model/artifact-library")
    denied = client.get(f"/api/v1/artifacts/{artifact.artifact_id}/download")
    allowed = client.get(f"/api/v1/artifacts/{artifact.artifact_id}/download", headers={"Authorization": "Bearer test-token"})

    assert mobile.status_code == 200
    assert mobile.json()["raw_default_visible"] is False
    assert denied.status_code == 401
    assert allowed.status_code == 200
    assert allowed.content == b"mobile"
