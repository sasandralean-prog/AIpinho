from __future__ import annotations

from pathlib import Path
import re
from uuid import uuid4

from aipinho.schemas.events.contracts import utc_now_iso
from aipinho.schemas.sandbox import SandboxStatus, SandboxTask, SandboxWorkspace
from aipinho.services.sandbox.sandbox_paths import ensure_sandbox_dirs
from aipinho.services.sandbox.sandbox_policy_service import SandboxPolicyService
from aipinho.services.sandbox.sandbox_store_service import SandboxStoreService


class SandboxWorkspaceService:
    def __init__(self, *, store: SandboxStoreService | None = None, policy: SandboxPolicyService | None = None) -> None:
        self.store = store or SandboxStoreService()
        self.policy = policy or SandboxPolicyService()
        self.dirs = ensure_sandbox_dirs()
        self.ensure_default_workspace()

    def status(self) -> SandboxStatus:
        policy = self.policy.status()
        return SandboxStatus(
            status=policy["status"],
            root_path_sanitized=str(self.dirs["root"]),
            workspaces=len(self.store.list_workspaces()),
            tasks=len(self.store.list_tasks()),
            artifacts=len(self.store.list_artifact_exports()),
            policy_version=str(policy["version"]),
            warnings=[],
        )

    def health(self) -> dict[str, object]:
        status = self.status()
        return {"ok": status.status == "ok", **status.model_dump()}

    def ensure_default_workspace(self) -> SandboxWorkspace:
        existing = self.store.get_workspace("sandbox_ws_default")
        if existing is not None:
            Path(existing.root_path_sanitized).mkdir(parents=True, exist_ok=True)
            return existing
        workspace = SandboxWorkspace(
            sandbox_workspace_id="sandbox_ws_default",
            name="default",
            display_name="Default Sandbox",
            role="sandbox_mutable",
            root_path_sanitized=str(self.dirs["default"]),
            allowed_operations=["read", "write", "append", "modify", "mkdir", "list", "copy", "move", "delete_safe", "safe_shell", "artifact_export", "validation"],
            limits=self.policy.policy().get("limits", {}),
            evidence_refs=["sandbox_workspace:default"],
            metadata_sanitized={"created_by": "sandbox_workspace_service"},
        )
        Path(workspace.root_path_sanitized).mkdir(parents=True, exist_ok=True)
        return self.store.save_workspace(workspace)

    def create_workspace(self, name: str, role: str = "sandbox_mutable") -> SandboxWorkspace:
        safe = "".join(ch if ch.isalnum() or ch in {"-", "_"} else "_" for ch in name).strip("_") or "workspace"
        root = (self.dirs["projects"] / safe).resolve()
        root.mkdir(parents=True, exist_ok=True)
        allowed_operations = ["read", "list", "artifact_export", "validation"]
        if role != "sandbox_readonly":
            allowed_operations.extend(["write", "append", "modify", "mkdir", "copy", "move", "delete_safe", "safe_shell"])
        workspace = SandboxWorkspace(
            name=safe,
            display_name=name.strip() or safe,
            role=role,
            root_path_sanitized=str(root),
            allowed_operations=allowed_operations,
            evidence_refs=[f"sandbox_workspace:{safe}"],
        )
        self.store.append_trace(None, {"type": "sandbox_workspace_created", "workspace_id": workspace.sandbox_workspace_id, "name": safe})
        return self.store.save_workspace(workspace)

    def list_workspaces(self) -> list[SandboxWorkspace]:
        self.ensure_default_workspace()
        return self.store.list_workspaces()

    def get_workspace(self, workspace_id: str) -> SandboxWorkspace:
        workspace = self.store.get_workspace(workspace_id)
        if workspace is None:
            raise FileNotFoundError(workspace_id)
        return workspace

    def create_task(self, *, sandbox_workspace_id: str, title: str, created_by_agent_id: str | None = None) -> SandboxTask:
        self.get_workspace(sandbox_workspace_id)
        slug = re.sub(r"[^a-z0-9]+", "_", title.casefold()).strip("_")[:60] or "sandbox_task"
        timestamp = utc_now_iso().replace("-", "").replace(":", "").replace("+00:00", "").replace("T", "_")
        task_root = self.dirs["tasks"] / f"{slug}_{timestamp}_{uuid4().hex[:8]}"
        task_root.mkdir(parents=True, exist_ok=False)
        task = SandboxTask(
            sandbox_workspace_id=sandbox_workspace_id,
            title=title,
            slug=slug,
            user_goal=title,
            agent_id=created_by_agent_id,
            workspace_id=sandbox_workspace_id,
            task_root_sanitized=str(task_root),
            created_by_agent_id=created_by_agent_id,
            status="created",
            evidence_refs=["sandbox_task_created", f"sandbox_task_root:{task_root.name}"],
        )
        self.store.save_task(task)
        self.store.append_trace(task.sandbox_task_id, {"type": "sandbox_task_created", "task_id": task.sandbox_task_id, "title": title})
        return task

    def list_tasks(self) -> list[SandboxTask]:
        return self.store.list_tasks()

    def get_task(self, task_id: str) -> SandboxTask:
        task = self.store.get_task(task_id)
        if task is None:
            raise FileNotFoundError(task_id)
        return task

    def operation_root(self, workspace_id: str, task_id: str | None = None) -> Path:
        workspace = self.get_workspace(workspace_id)
        if not task_id:
            return Path(workspace.root_path_sanitized).resolve(strict=False)
        task = self.get_task(task_id)
        if task.sandbox_workspace_id != workspace_id:
            raise PermissionError("sandbox_task_workspace_mismatch")
        if not task.task_root_sanitized:
            raise PermissionError("sandbox_task_root_missing")
        return Path(task.task_root_sanitized).resolve(strict=False)

    def cancel_task(self, task_id: str) -> SandboxTask:
        task = self.get_task(task_id)
        updated = task.model_copy(update={"status": "cancelled", "updated_at": utc_now_iso()})
        self.store.save_task(updated)
        self.store.append_trace(task_id, {"type": "sandbox_task_cancelled", "task_id": task_id})
        return updated

    def update_task_status(
        self,
        task_id: str,
        status: str,
        *,
        evidence_refs: list[str] | None = None,
        completed: bool = False,
    ) -> SandboxTask:
        task = self.get_task(task_id)
        merged_evidence = list(task.evidence_refs)
        for evidence_ref in evidence_refs or []:
            if evidence_ref not in merged_evidence:
                merged_evidence.append(evidence_ref)
        now = utc_now_iso()
        updated = task.model_copy(
            update={
                "status": status,
                "updated_at": now,
                "completed_at": now if completed else task.completed_at,
                "evidence_refs": merged_evidence,
            }
        )
        return self.store.save_task(updated)
