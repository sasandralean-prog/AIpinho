from __future__ import annotations

from pathlib import Path

import yaml
from fastapi.testclient import TestClient

from aipinho.main import app
from aipinho.services.config_governance.workspace_permission_matrix_service import WorkspacePermissionMatrixService
from aipinho.services.models.capability_router_service import CapabilityRouterService
from aipinho.services.rag.workspace_index_service import WorkspaceIndexService

client = TestClient(app)


def _registry(tmp_path: Path, role: str = "target_mutable") -> tuple[Path, WorkspacePermissionMatrixService]:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    registry = tmp_path / "workspace_registry.yaml"
    registry.write_text(
        yaml.safe_dump(
            {
                "schema_version": 1,
                "workspaces": [
                    {
                        "workspace_id": "workspace_test",
                        "root_path": str(workspace),
                        "role": role,
                        "permissions": {},
                    }
                ],
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    return workspace, WorkspacePermissionMatrixService(registry).load()


def test_workspace_index_preview_respects_policy(tmp_path):
    workspace, matrix = _registry(tmp_path, "target_mutable")
    service = WorkspaceIndexService(store_dir=tmp_path / "indexes", permission_matrix=matrix, capability_router=CapabilityRouterService(matrix=matrix))

    result = service.preview(workspace_id="workspace_test")

    assert result["status"] == "previewed"
    assert result["index_request"]["workspace_path"] == str(workspace)


def test_workspace_index_requires_approval_when_read_policy_ask(tmp_path):
    _workspace, matrix = _registry(tmp_path, "protected")
    service = WorkspaceIndexService(store_dir=tmp_path / "indexes", permission_matrix=matrix, capability_router=CapabilityRouterService(matrix=matrix))

    result = service.preview(workspace_id="workspace_test")

    assert result["status"] == "pending_approval"
    assert result["approval_id"].startswith("approval_")


def test_workspace_index_does_not_index_secrets_and_falls_back_keyword(tmp_path):
    workspace, matrix = _registry(tmp_path, "target_mutable")
    (workspace / "src").mkdir()
    (workspace / "src" / "main.py").write_text("def main():\n    return 'visible keyword'\n", encoding="utf-8")
    (workspace / ".env").write_text("SECRET_TOKEN=abc", encoding="utf-8")
    service = WorkspaceIndexService(store_dir=tmp_path / "indexes", permission_matrix=matrix, capability_router=CapabilityRouterService(matrix=matrix))

    result = service.start(workspace_id="workspace_test")
    record = result["record"]

    assert result["status"] == "indexed"
    assert any(item["relative_path"] == "src/main.py" for item in record["indexed_files"])
    assert any(item["reason"] == "secret_or_credential_name" for item in record["skipped_files"])
    assert record["capabilities_used"]["fallback"] == "keyword_index"
    assert record["capabilities_used"]["embeddings_used"] is False
    assert record["capabilities_used"]["reranker_used"] is False


def test_workspace_search_returns_paths_and_records_capabilities(tmp_path):
    workspace, matrix = _registry(tmp_path, "target_mutable")
    (workspace / "app.txt").write_text("Tela principal do app fica aqui.", encoding="utf-8")
    service = WorkspaceIndexService(store_dir=tmp_path / "indexes", permission_matrix=matrix, capability_router=CapabilityRouterService(matrix=matrix))

    result = service.search(workspace_id="workspace_test", query="principal", limit=5)

    assert result["status"] == "ok"
    assert result["results"]
    assert result["capabilities_used"]["fallback"] == "keyword_search"
    assert result["capabilities_used"]["embeddings_used"] is False
    assert result["capabilities_used"]["reranker_used"] is False


def test_ocr_and_vision_missing_or_disabled_are_structured():
    health = client.get("/api/v1/capabilities/health").json()
    by_id = {item["capability_id"]: item for item in health["capabilities"]}

    assert by_id["ocr"]["health_status"] in {"disabled", "missing", "unverified", "ok"}
    assert by_id["vision"]["health_status"] in {"disabled", "missing", "unverified", "ok"}

    ocr = client.post("/api/v1/vision/ocr", json={"prompt": "sem imagem"})
    vision = client.post("/api/v1/vision/analyze", json={"prompt": "sem imagem"})

    assert ocr.status_code == 200
    assert vision.status_code == 200
    assert ocr.json()["status"] in {"blocked", "degraded", "completed", "rejected"}
    assert vision.json()["status"] in {"blocked", "degraded", "completed", "rejected"}


def test_project_analysis_readonly_does_not_write_or_run_shell(tmp_path):
    workspace = tmp_path / "project"
    workspace.mkdir()
    (workspace / "README.md").write_text("# Projeto\nFuncionalidade principal.", encoding="utf-8")

    response = client.post(
        "/api/v1/project-analysis/start",
        json={
            "workspace_ref": str(workspace),
            "objective": "analise readonly",
            "readonly": True,
            "allow_write": False,
            "allow_shell": False,
            "max_files": 5,
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["write_enabled"] is False
    assert data["shell_enabled"] is False
    assert data["readonly"] is True
    assert "route_decision" in data


def test_workspace_index_api_unknown_workspace_is_structured():
    response = client.post("/api/v1/workspaces/unknown/index/preview", json={"source_channel": "test"})

    assert response.status_code == 200
    assert response.json()["status"] == "blocked"
    assert response.json()["reason_code"] == "workspace_not_registered"
