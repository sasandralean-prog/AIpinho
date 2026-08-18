from __future__ import annotations

import hashlib
import shutil
from pathlib import Path
from typing import Any

from aipinho.schemas.sandbox import SandboxFileOperation, SandboxFileRequest, SandboxPathResolution
from aipinho.services.events.event_core import redact_payload
from aipinho.services.sandbox.sandbox_paths import ensure_sandbox_dirs
from aipinho.services.sandbox.sandbox_policy_service import SandboxPolicyService
from aipinho.services.sandbox.sandbox_store_service import SandboxStoreService
from aipinho.services.sandbox.sandbox_workspace_service import SandboxWorkspaceService


class SandboxFileService:
    def __init__(self, *, store: SandboxStoreService | None = None, policy: SandboxPolicyService | None = None) -> None:
        self.store = store or SandboxStoreService()
        self.policy = policy or SandboxPolicyService()
        self.workspaces = SandboxWorkspaceService(store=self.store, policy=self.policy)

    def resolve(self, workspace_id: str, relative_path: str, operation: str, task_id: str | None = None) -> tuple[Path, SandboxPathResolution]:
        workspace = self.workspaces.get_workspace(workspace_id)
        if workspace.role == "sandbox_readonly" and operation not in {"read", "list", "validation", "artifact_export"}:
            raise PermissionError("source_readonly_write_denied")
        root = self.workspaces.operation_root(workspace_id, task_id)
        decision = self.policy.allow_path(workspace_root=root, relative_path=relative_path, operation=operation)
        candidate = (root / relative_path).resolve(strict=False)
        resolution = SandboxPathResolution(
            sandbox_workspace_id=workspace_id,
            relative_path=relative_path,
            absolute_path_sanitized=str(candidate),
            within_sandbox=decision.allowed,
            exists=candidate.exists(),
            is_symlink=candidate.exists() and candidate.is_symlink(),
            policy_decision=decision,
        )
        if not decision.allowed:
            raise PermissionError(decision.reason_code)
        return candidate, resolution

    def list_files(self, request: SandboxFileRequest) -> dict[str, Any]:
        path, _ = self.resolve(request.sandbox_workspace_id, request.relative_path or ".", "read", request.sandbox_task_id)
        entries = []
        base = path if path.is_dir() else path.parent
        operation_root = self.workspaces.operation_root(request.sandbox_workspace_id, request.sandbox_task_id)
        for child in sorted(base.iterdir()):
            entries.append({
                "name": child.name,
                "relative_path": str(child.relative_to(operation_root)),
                "is_dir": child.is_dir(),
                "size": child.stat().st_size if child.is_file() else 0,
            })
        return {"entries": entries, "count": len(entries)}

    def read_file(self, request: SandboxFileRequest) -> dict[str, Any]:
        path, _ = self.resolve(request.sandbox_workspace_id, request.relative_path, "read", request.sandbox_task_id)
        data = path.read_bytes()[: request.max_bytes]
        op = self._op(request, "read", "succeeded", "sandbox_allowed_low_risk", bytes_read=len(data), digest=hashlib.sha256(data).hexdigest())
        return {"operation": op.model_dump(), "content_sanitized": redact_payload(data.decode("utf-8", errors="replace")), "size": path.stat().st_size}

    def write_file(self, request: SandboxFileRequest, *, append: bool = False) -> SandboxFileOperation:
        path, _ = self.resolve(request.sandbox_workspace_id, request.relative_path, "write", request.sandbox_task_id)
        content_decision = self.policy.allow_content(request.content or "")
        if not content_decision.allowed:
            return self._op(request, "append" if append else "write", "blocked", content_decision.reason_code)
        if path.exists() and not (request.overwrite or append):
            return self._op(request, "write", "blocked", "sandbox_file_exists")
        path.parent.mkdir(parents=True, exist_ok=True)
        content = request.content or ""
        if append:
            with path.open("a", encoding="utf-8") as handle:
                handle.write(content)
        else:
            path.write_text(content, encoding="utf-8")
        data = path.read_bytes()
        return self._op(request, "append" if append else "write", "succeeded", "sandbox_allowed_low_risk", bytes_written=len(content.encode("utf-8")), digest=hashlib.sha256(data).hexdigest())

    def modify_file(self, request: SandboxFileRequest) -> SandboxFileOperation:
        path, _ = self.resolve(request.sandbox_workspace_id, request.relative_path, "write", request.sandbox_task_id)
        content_decision = self.policy.allow_content(request.content or "")
        if not content_decision.allowed:
            return self._op(request, "modify", "blocked", content_decision.reason_code)
        if request.expected_hash and path.exists() and hashlib.sha256(path.read_bytes()).hexdigest() != request.expected_hash:
            return self._op(request, "modify", "blocked", "sandbox_expected_hash_mismatch")
        path.parent.mkdir(parents=True, exist_ok=True)
        content = request.content or ""
        path.write_text(content, encoding="utf-8")
        data = path.read_bytes()
        return self._op(request, "modify", "succeeded", "sandbox_allowed_low_risk", bytes_written=len(content.encode("utf-8")), digest=hashlib.sha256(data).hexdigest())

    def mkdir(self, request: SandboxFileRequest) -> SandboxFileOperation:
        path, _ = self.resolve(request.sandbox_workspace_id, request.relative_path, "write", request.sandbox_task_id)
        path.mkdir(parents=True, exist_ok=True)
        return self._op(request, "mkdir", "succeeded", "sandbox_allowed_low_risk")

    def copy(self, request: SandboxFileRequest) -> SandboxFileOperation:
        if not request.destination_relative_path:
            return self._op(request, "copy", "blocked", "sandbox_destination_required")
        src, _ = self.resolve(request.sandbox_workspace_id, request.relative_path, "read", request.sandbox_task_id)
        dst, _ = self.resolve(request.sandbox_workspace_id, request.destination_relative_path, "write", request.sandbox_task_id)
        dst.parent.mkdir(parents=True, exist_ok=True)
        if src.is_dir():
            shutil.copytree(src, dst, dirs_exist_ok=request.overwrite)
        else:
            if dst.exists() and not request.overwrite:
                return self._op(request, "copy", "blocked", "sandbox_file_exists")
            shutil.copy2(src, dst)
        return self._op(request, "copy", "succeeded", "sandbox_allowed_low_risk")

    def move(self, request: SandboxFileRequest) -> SandboxFileOperation:
        if not request.destination_relative_path:
            return self._op(request, "move", "blocked", "sandbox_destination_required")
        src, _ = self.resolve(request.sandbox_workspace_id, request.relative_path, "write", request.sandbox_task_id)
        dst, _ = self.resolve(request.sandbox_workspace_id, request.destination_relative_path, "write", request.sandbox_task_id)
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(src), str(dst))
        return self._op(request, "move", "succeeded", "sandbox_allowed_low_risk")

    def delete_safe(self, request: SandboxFileRequest) -> SandboxFileOperation:
        path, _ = self.resolve(request.sandbox_workspace_id, request.relative_path, "delete-safe", request.sandbox_task_id)
        trash = ensure_sandbox_dirs()["trash"] / request.sandbox_workspace_id
        trash.mkdir(parents=True, exist_ok=True)
        target = trash / path.name
        counter = 0
        while target.exists():
            counter += 1
            target = trash / f"{path.stem}_{counter}{path.suffix}"
        shutil.move(str(path), str(target))
        return self._op(request, "delete-safe", "succeeded", "sandbox_allowed_low_risk", metadata={"moved_to_trash": str(target)})

    def _op(
        self,
        request: SandboxFileRequest,
        operation_type: str,
        status: str,
        reason_code: str,
        *,
        bytes_written: int = 0,
        bytes_read: int = 0,
        digest: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> SandboxFileOperation:
        op = SandboxFileOperation(
            sandbox_task_id=request.sandbox_task_id,
            sandbox_workspace_id=request.sandbox_workspace_id,
            operation_type=operation_type,
            relative_path=request.relative_path,
            absolute_path_sanitized=str(self.workspaces.operation_root(request.sandbox_workspace_id, request.sandbox_task_id) / request.relative_path),
            status=status,  # type: ignore[arg-type]
            reason_code=reason_code,
            bytes_written=bytes_written,
            bytes_read=bytes_read,
            hash=digest,
            evidence_refs=[f"sandbox_file:{operation_type}"],
            metadata_sanitized=metadata or {},
        )
        self.store.save_file_operation(op)
        self.store.append_trace(request.sandbox_task_id, {"type": f"sandbox_file_{operation_type}", "status": status, "reason_code": reason_code, "relative_path": request.relative_path})
        if request.sandbox_task_id and status == "succeeded":
            task = self.store.get_task(request.sandbox_task_id)
            if task is not None:
                field = "created_files" if operation_type in {"write", "mkdir", "copy"} else "modified_files"
                if operation_type in {"delete-safe"}:
                    field = "deleted_files"
                values = list(getattr(task, field))
                if request.relative_path not in values:
                    values.append(request.relative_path)
                evidence_ref = f"sandbox_file_operation:{op.operation_id}"
                evidence_refs = [*task.evidence_refs]
                if evidence_ref not in evidence_refs:
                    evidence_refs.append(evidence_ref)
                self.store.save_task(
                    task.model_copy(
                        update={
                            field: values,
                            "status": "running",
                            "updated_at": op.created_at,
                            "evidence_refs": evidence_refs,
                        }
                    )
                )
        return op
