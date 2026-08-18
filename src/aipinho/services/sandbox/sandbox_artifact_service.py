from __future__ import annotations

import base64
import fnmatch
import hashlib
import json
import tempfile
import zipfile
from pathlib import Path

from aipinho.schemas.agents.tool_gateway import ArtifactUploadRequest
from aipinho.schemas.sandbox import SandboxArtifactExport, SandboxArtifactExportRequest
from aipinho.schemas.sandbox import SandboxValidationResult
from aipinho.schemas.events.contracts import utc_now_iso
from aipinho.services.agents.agent_tool_gateway_service import AgentToolGatewayService
from aipinho.services.sandbox.sandbox_file_service import SandboxFileService
from aipinho.services.sandbox.sandbox_policy_service import SandboxPolicyService
from aipinho.services.sandbox.sandbox_store_service import SandboxStoreService
from aipinho.services.sandbox.sandbox_workspace_service import SandboxWorkspaceService


class SandboxArtifactService:
    DEFAULT_EXCLUDE_GLOBS = [
        "__pycache__/*",
        "*/__pycache__/*",
        "*.pyc",
        "*/build/*",
        "build/*",
        "*/.gradle/*",
        ".gradle/*",
        "*/node_modules/*",
        "node_modules/*",
        "*/dist/*",
        "dist/*",
    ]

    def __init__(
        self,
        *,
        store: SandboxStoreService | None = None,
        policy: SandboxPolicyService | None = None,
        tool_gateway: AgentToolGatewayService | None = None,
    ) -> None:
        self.store = store or SandboxStoreService()
        self.policy = policy or SandboxPolicyService()
        self.workspaces = SandboxWorkspaceService(store=self.store, policy=self.policy)
        self.files = SandboxFileService(store=self.store, policy=self.policy)
        self.tool_gateway = tool_gateway or AgentToolGatewayService()

    def export_zip(self, request: SandboxArtifactExportRequest) -> SandboxArtifactExport:
        workspace = self.workspaces.get_workspace(request.sandbox_workspace_id)
        root = self.workspaces.operation_root(request.sandbox_workspace_id, request.sandbox_task_id)
        safe_filename = self._safe_filename(request.filename, default="sandbox_artifact.zip")
        if not safe_filename.endswith(".zip"):
            safe_filename += ".zip"
        with tempfile.NamedTemporaryFile(delete=False, suffix=".zip") as tmp:
            tmp_path = Path(tmp.name)
        try:
            manifest_files: list[dict[str, object]] = []
            with zipfile.ZipFile(tmp_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
                for rel in request.include_paths or ["."]:
                    base, _ = self.files.resolve(request.sandbox_workspace_id, rel, "read", request.sandbox_task_id)
                    if base.is_file():
                        self._write_file(root, base, archive, request.exclude_globs, manifest_files)
                    else:
                        for path in base.rglob("*"):
                            if path.is_file():
                                self._write_file(root, path, archive, request.exclude_globs, manifest_files)
                manifest = {
                    "sandbox_task_id": request.sandbox_task_id,
                    "sandbox_workspace_id": request.sandbox_workspace_id,
                    "source_directory_sanitized": str(root),
                    "files": manifest_files,
                    "validation_status": "pending",
                    "evidence_refs": [f"sandbox_workspace:{request.sandbox_workspace_id}"],
                }
                archive.writestr("sandbox_manifest.json", json.dumps(manifest, ensure_ascii=True, indent=2))
            size = tmp_path.stat().st_size
            decision = self.policy.allow_artifact(estimated_size=size)
            if not decision.allowed:
                export = SandboxArtifactExport(
                    sandbox_task_id=request.sandbox_task_id,
                    sandbox_workspace_id=request.sandbox_workspace_id,
                    filename=safe_filename,
                    size=size,
                    status="blocked",
                    reason_code=decision.reason_code,
                    evidence_refs=decision.evidence_refs,
                )
                return self.store.save_artifact_export(export)
            content_b64 = base64.b64encode(tmp_path.read_bytes()).decode("ascii")
            artifact = self.tool_gateway.upload_artifact(
                agent_id="sandbox",
                session_id=request.sandbox_task_id or "sandbox_session",
                request=ArtifactUploadRequest(
                    filename=safe_filename,
                    content_type="application/zip",
                    content=content_b64,
                    encoding="base64",
                    origin="sandbox_export",
                    metadata_sanitized={
                        "sandbox_workspace_id": request.sandbox_workspace_id,
                        "sandbox_task_id": request.sandbox_task_id,
                        "project_generation_id": request.project_generation_id,
                        "status": "ready",
                        "manifest_path": "sandbox_manifest.json",
                        "evidence_refs": [f"sandbox_task:{request.sandbox_task_id}"] if request.sandbox_task_id else [],
                    },
                ),
            )
            with zipfile.ZipFile(tmp_path, "r") as archive:
                bad_entry = archive.testzip()
            validation = SandboxValidationResult(
                sandbox_task_id=request.sandbox_task_id,
                validation_type="zip_integrity",
                status="passed" if bad_entry is None else "failed",
                checks=[{"type": "zip_integrity", "status": "passed" if bad_entry is None else "failed", "bad_entry": bad_entry}],
                checked_files=[str(item["relative_path"]) for item in manifest_files],
                checked_artifacts=[artifact.artifact_id],
                errors=[] if bad_entry is None else [f"invalid_zip_entry:{bad_entry}"],
                evidence_refs=[f"artifact:{artifact.artifact_id}"],
            )
            export = SandboxArtifactExport(
                    sandbox_task_id=request.sandbox_task_id,
                    sandbox_workspace_id=request.sandbox_workspace_id,
                    project_generation_id=request.project_generation_id,
                    source_directory_sanitized=str(root),
                artifact_id=artifact.artifact_id,
                filename=artifact.filename,
                size=artifact.size,
                status="ready" if validation.status == "passed" else "failed",
                reason_code="sandbox_artifact_export_allowed",
                download_endpoint=artifact.download_endpoint,
                requires_token=artifact.requires_token,
                manifest_path="sandbox_manifest.json",
                validation_id=validation.validation_id,
                evidence_refs=[f"artifact:{artifact.artifact_id}"],
            )
            self.store.append_trace(request.sandbox_task_id, {"type": "sandbox_artifact_exported", "artifact_id": artifact.artifact_id, "filename": artifact.filename})
            self.store.append_trace(request.sandbox_task_id, {"type": "sandbox_validation_finished", "validation_id": validation.validation_id, "status": validation.status})
            if request.sandbox_task_id:
                task = self.store.get_task(request.sandbox_task_id)
                if task is not None:
                    evidence_ref = f"sandbox_artifact_export:{export.artifact_export_id}"
                    evidence_refs = [*task.evidence_refs]
                    if evidence_ref not in evidence_refs:
                        evidence_refs.append(evidence_ref)
                    self.store.save_task(task.model_copy(update={
                        "artifact_ids": [*task.artifact_ids, artifact.artifact_id],
                        "validation_ids": [*task.validation_ids, validation.validation_id],
                        "status": "completed" if export.status == "ready" else "failed",
                        "updated_at": utc_now_iso(),
                        "completed_at": utc_now_iso() if export.status == "ready" else task.completed_at,
                        "evidence_refs": evidence_refs,
                    }))
            return self.store.save_artifact_export(export)
        finally:
            tmp_path.unlink(missing_ok=True)

    def list_exports(self) -> list[SandboxArtifactExport]:
        return self.store.list_artifact_exports()

    def get_export(self, export_id: str) -> SandboxArtifactExport:
        export = self.store.get_artifact_export(export_id)
        if export is None:
            raise FileNotFoundError(export_id)
        return export

    def _write_file(
        self,
        root: Path,
        path: Path,
        archive: zipfile.ZipFile,
        exclude_globs: list[str],
        manifest_files: list[dict[str, object]],
    ) -> None:
        rel = path.relative_to(root).as_posix()
        effective_excludes = [*self.DEFAULT_EXCLUDE_GLOBS, *exclude_globs]
        if any(fnmatch.fnmatch(rel, glob) for glob in effective_excludes):
            return
        archive.write(path, rel)
        data = path.read_bytes()
        manifest_files.append({"relative_path": rel, "size": len(data), "sha256": hashlib.sha256(data).hexdigest()})

    def _safe_filename(self, filename: str, *, default: str) -> str:
        safe = "".join(ch if ch.isalnum() or ch in {"-", "_", "."} else "_" for ch in Path(filename).name).strip("._")
        return safe or default
