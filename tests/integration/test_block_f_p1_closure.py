from __future__ import annotations

import base64
import io
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import aipinho.services.runtime.task_run_guard as task_run_guard_module
import aipinho.services.runtime.task_runtime_service as task_runtime_module
from aipinho.schemas.agents.tool_gateway import ArtifactUploadRequest
from aipinho.schemas.artifacts.artifact_library import ArtifactBundleRequest, ArtifactPreviewRequest
from aipinho.schemas.tasks.task_contract_draft import TaskContractDraft, TaskDraftWorkspace
from aipinho.services.agents.agent_tool_gateway_service import AgentToolGatewayService
from aipinho.services.agents.agent_tool_invocation_store import AgentToolInvocationStore
from aipinho.services.approvals.approval_service import ApprovalService
from aipinho.services.approvals.approval_store import ApprovalStore
from aipinho.services.artifacts.artifact_library_service import ArtifactLibraryService
from aipinho.services.orchestration.task_contract_draft_service import TaskContractDraftService
from aipinho.services.orchestration.task_draft_store import TaskDraftStore
from aipinho.services.orchestration.task_preview_service import TaskPreviewService
from aipinho.services.orchestration.task_preview_store import TaskPreviewStore
from aipinho.services.runtime.task_run_store import TaskRunStore
from aipinho.services.runtime.task_runtime_service import TaskRuntimeService


def _allow_tmp_workspace_policy(monkeypatch) -> None:
    class FakeWorkspacePolicy:
        def load(self):
            return self

        def evaluate(self, workspace_path, requires_workspace=True):
            return SimpleNamespace(
                status="allowed",
                workspace_path=workspace_path,
                blocked=False,
                needs_clarification=False,
                reason="test_workspace_allowed",
            )

    class FakeWorkspaceRoleContracts:
        def load(self):
            return self

        def resolve(self, workspace_path, required=True):
            return SimpleNamespace(
                status="allowed",
                reason="workspace_allowed",
                contract=SimpleNamespace(role="target_mutable"),
            )

    class FakePermissionMatrix:
        def load(self):
            return self

        def decide(self, path, permission):
            return SimpleNamespace(status="allowed", reason_code="allowed")

    monkeypatch.setattr(task_runtime_module, "WorkspacePolicyService", lambda: FakeWorkspacePolicy())
    monkeypatch.setattr(task_run_guard_module, "WorkspacePolicyService", lambda: FakeWorkspacePolicy())
    monkeypatch.setattr(task_run_guard_module, "WorkspaceRoleContractService", lambda: FakeWorkspaceRoleContracts())
    monkeypatch.setattr(task_run_guard_module, "WorkspacePermissionMatrixService", lambda: FakePermissionMatrix())


def test_block_f_pipeline_queue_executes_approved_project_generation_plan(tmp_path: Path, monkeypatch) -> None:
    _allow_tmp_workspace_policy(monkeypatch)
    workspace = tmp_path / "PipelineWorkspace"
    draft_store = TaskDraftStore(root=tmp_path / "drafts")
    preview_service = TaskPreviewService(
        store=TaskPreviewStore(root=tmp_path / "previews"),
        draft_store=draft_store,
    )
    approvals = ApprovalService(
        store=ApprovalStore(root=tmp_path / "approvals"),
        preview_service=preview_service,
        draft_store=draft_store,
    )
    run_store = TaskRunStore(root=tmp_path / "runs")
    now = datetime.now(timezone.utc).isoformat()
    draft = TaskContractDraft(
        draft_id="draft_block_f_p1_pipeline",
        session_id="block_f_p1_pipeline",
        status="approval_required",
        intent_map={
            "risk": "medium",
            "target_path": str(workspace),
            "context_ref": "block_f_p1_pipeline_context",
            "validation_plan": {"checks": ["file_exists", "content_contains_expected_markers"]},
            "rollback_plan": {"strategy": "delete generated test file"},
            "project_generation_plan": {
                "target_workspace": str(workspace),
                "directories_to_create": [{"path": "reports"}],
                "files_to_create": [
                    {
                        "path": "reports/pipeline_certification.txt",
                        "content": "pipeline field certification",
                    }
                ],
                "validation_steps": ["file_exists", "content_contains_expected_markers"],
                "expected_outputs": ["reports/pipeline_certification.txt"],
            },
        },
        policy_decision={
            "decision_id": "policy_block_f_p1_pipeline",
            "status": "ask",
            "approval_required_for": ["write_files"],
        },
        contract_type="project_generation",
        operation_type="project_generation",
        runtime_profile="project_generation",
        capabilities_required=["write_workspace"],
        source_scope="block_f_p1_closure_test",
        requires_workspace=True,
        workspace=TaskDraftWorkspace(path=str(workspace), status="confirmed"),
        requested_actions=["write_files"],
        approval_required_for=["write_files"],
        executable_plan_ref="draft_block_f_p1_pipeline:project_generation_plan",
        expected_outcomes=["project_generation", "validation_result"],
        safe_to_preview=True,
        created_at=now,
        updated_at=now,
    )
    draft_store.save(draft)
    preview = preview_service.create_preview_from_draft(draft.draft_id)
    assert preview is not None
    approval = approvals.create_approval_for_preview(preview.preview_id, actions=["write_files"], reason="block_f_p1_pipeline")
    approvals.approve(approval.approval_id, reason="block_f_p1_pipeline")
    runtime = TaskRuntimeService(
        store=run_store,
        drafts=TaskContractDraftService(store=draft_store),
        previews=preview_service,
        approvals=approvals,
    )

    run = runtime.create_from_preview(preview.preview_id, {"approval_id": approval.approval_id, "start_immediately": True})
    result = runtime.process_queue()
    latest = runtime.get_run(run.run_id)

    assert result["status"] in {"completed", "queue_empty"}
    assert latest is not None
    assert latest.status == "completed"
    assert runtime.get_result(run.run_id).status == "completed"
    assert (workspace / "reports" / "pipeline_certification.txt").read_text(encoding="utf-8") == "pipeline field certification"


def test_block_f_artifact_zip_and_binary_are_registered(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("AIPINHO_TOOL_GATEWAY_ROOT", str(tmp_path / "tool_gateway"))
    monkeypatch.setenv("AIPINHO_ARTIFACT_LIBRARY_ROOT", str(tmp_path / "artifact_library"))
    store = AgentToolInvocationStore(root=tmp_path / "tool_gateway")
    gateway = AgentToolGatewayService(store=store)
    library = ArtifactLibraryService(
        tool_store=store,
        gateway=gateway,
        index_path=tmp_path / "artifact_library" / "ARTIFACT_INDEX.json",
    )
    report = gateway.upload_artifact(
        agent_id="aipinho",
        session_id="block_f_p1_artifacts",
        request=ArtifactUploadRequest(filename="report.txt", content_type="text/plain", content="ok", origin="block_f_p1"),
    )
    binary = gateway.upload_artifact(
        agent_id="aipinho",
        session_id="block_f_p1_artifacts",
        request=ArtifactUploadRequest(
            filename="payload.bin",
            content_type="application/octet-stream",
            content=base64.b64encode(b"\x00\x01").decode("ascii"),
            encoding="base64",
            origin="block_f_p1",
        ),
    )

    binary_preview = library.preview(ArtifactPreviewRequest(artifact_id=binary.artifact_id, preview_mode="text"))
    bundle = library.create_bundle(
        ArtifactBundleRequest(
            artifact_ids=[report.artifact_id, binary.artifact_id],
            session_id="block_f_p1_artifacts",
            bundle_name="block_f_p1_bundle.zip",
        )
    )
    artifact, content = gateway.read_artifact_bytes(bundle.bundle_artifact.artifact_id)

    assert binary_preview.preview_available is True
    assert "binary_preview_metadata_only" in binary_preview.warnings
    assert artifact.content_type == "application/zip"
    assert bundle.bundle_artifact.requires_token is True
    assert bundle.bundle_artifact.download_endpoint == f"/api/v1/artifacts/{bundle.bundle_artifact.artifact_id}/download"
    assert "token" not in bundle.bundle_artifact.download_endpoint.lower()
    with zipfile.ZipFile(io.BytesIO(content)) as archive:
        assert "BUNDLE_MANIFEST.json" in archive.namelist()
        assert "report.txt" in archive.namelist()
        assert "payload.bin" in archive.namelist()
