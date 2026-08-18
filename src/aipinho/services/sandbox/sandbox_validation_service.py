from __future__ import annotations

import io
import zipfile
from pathlib import Path

from aipinho.schemas.sandbox import SandboxValidationResult
from aipinho.services.agents.agent_tool_gateway_service import AgentToolGatewayService
from aipinho.services.sandbox.sandbox_store_service import SandboxStoreService
from aipinho.services.sandbox.sandbox_workspace_service import SandboxWorkspaceService


class SandboxValidationService:
    def __init__(
        self,
        *,
        store: SandboxStoreService | None = None,
        tool_gateway: AgentToolGatewayService | None = None,
    ) -> None:
        self.store = store or SandboxStoreService()
        self.workspaces = SandboxWorkspaceService(store=self.store)
        self.tool_gateway = tool_gateway or AgentToolGatewayService()

    def validate(
        self,
        *,
        sandbox_workspace_id: str,
        sandbox_task_id: str | None = None,
        relative_paths: list[str] | None = None,
        artifact_ids: list[str] | None = None,
    ) -> SandboxValidationResult:
        workspace = self.workspaces.get_workspace(sandbox_workspace_id)
        root = self.workspaces.operation_root(sandbox_workspace_id, sandbox_task_id)
        checks: list[dict[str, object]] = []
        errors: list[str] = []
        checked_files: list[str] = []
        checked_artifacts: list[str] = []
        for relative_path in relative_paths or []:
            candidate = (root / relative_path).resolve(strict=False)
            exists = candidate.exists()
            checks.append({"type": "file_exists", "relative_path": relative_path, "status": "passed" if exists else "failed"})
            checked_files.append(relative_path)
            if not exists:
                errors.append(f"missing_file:{relative_path}")
        for artifact_id in artifact_ids or []:
            try:
                artifact, content = self.tool_gateway.read_artifact_bytes(artifact_id)
                integrity = True
                if artifact.content_type == "application/zip" or artifact.filename.casefold().endswith(".zip"):
                    with zipfile.ZipFile(io.BytesIO(content)) as archive:
                        integrity = archive.testzip() is None
                checks.append({"type": "artifact_integrity", "artifact_id": artifact_id, "status": "passed" if integrity else "failed"})
                checked_artifacts.append(artifact_id)
                if not integrity:
                    errors.append(f"invalid_artifact:{artifact_id}")
            except Exception:
                checks.append({"type": "artifact_integrity", "artifact_id": artifact_id, "status": "failed"})
                errors.append(f"missing_or_invalid_artifact:{artifact_id}")
        result = SandboxValidationResult(
            sandbox_task_id=sandbox_task_id,
            validation_type="sandbox_files_and_artifacts",
            status="passed" if not errors else "failed",
            checks=checks,
            checked_files=checked_files,
            checked_artifacts=checked_artifacts,
            errors=errors,
            evidence_refs=[f"sandbox_validation:{sandbox_task_id or 'standalone'}"],
        )
        self.store.append_trace(sandbox_task_id, {"type": "sandbox_validation_finished", "validation_id": result.validation_id, "status": result.status})
        if sandbox_task_id:
            task = self.store.get_task(sandbox_task_id)
            if task is not None:
                validations = [*task.validation_ids, result.validation_id]
                evidence_ref = f"sandbox_validation:{result.validation_id}"
                evidence_refs = [*task.evidence_refs]
                if evidence_ref not in evidence_refs:
                    evidence_refs.append(evidence_ref)
                self.store.save_task(
                    task.model_copy(
                        update={
                            "validation_ids": validations,
                            "status": "running" if result.status == "passed" else "failed",
                            "evidence_refs": evidence_refs,
                        }
                    )
                )
        return result
