from __future__ import annotations

import json
from pathlib import Path
from typing import TypeVar

from aipinho.schemas.common.base import AIpinhoModel
from aipinho.schemas.sandbox import (
    SandboxArtifactExport,
    SandboxCleanupPreview,
    SandboxFileOperation,
    SandboxShellCommand,
    SandboxTask,
    SandboxWorkspace,
)
from aipinho.services.sandbox.sandbox_paths import ensure_sandbox_dirs

T = TypeVar("T", bound=AIpinhoModel)


class SandboxStoreService:
    def __init__(self, *, data_root: Path | None = None) -> None:
        dirs = ensure_sandbox_dirs()
        self.root = data_root or dirs["data"]
        self.root.mkdir(parents=True, exist_ok=True)

    def save_workspace(self, workspace: SandboxWorkspace) -> SandboxWorkspace:
        self._save("workspaces", workspace.sandbox_workspace_id, workspace)
        return workspace

    def list_workspaces(self) -> list[SandboxWorkspace]:
        return self._list("workspaces", SandboxWorkspace)

    def get_workspace(self, workspace_id: str) -> SandboxWorkspace | None:
        return self._get("workspaces", workspace_id, SandboxWorkspace)

    def save_task(self, task: SandboxTask) -> SandboxTask:
        self._save("tasks", task.sandbox_task_id, task)
        return task

    def list_tasks(self) -> list[SandboxTask]:
        return self._list("tasks", SandboxTask)

    def get_task(self, task_id: str) -> SandboxTask | None:
        return self._get("tasks", task_id, SandboxTask)

    def append_trace(self, task_id: str | None, event: dict[str, object]) -> str:
        trace_id = str(event.get("event_id") or f"sandbox_trace_{len(self.list_trace(task_id)) + 1}")
        event = {**event, "event_id": trace_id}
        path = self._dir("traces") / f"{task_id or 'global'}.jsonl"
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event, ensure_ascii=False) + "\n")
        return trace_id

    def list_trace(self, task_id: str | None) -> list[dict[str, object]]:
        path = self._dir("traces") / f"{task_id or 'global'}.jsonl"
        if not path.exists():
            return []
        events = []
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        return events

    def save_file_operation(self, operation: SandboxFileOperation) -> SandboxFileOperation:
        self._save("file_operations", operation.operation_id, operation)
        return operation

    def save_shell_command(self, command: SandboxShellCommand) -> SandboxShellCommand:
        self._save("shell_commands", command.command_id, command)
        return command

    def save_artifact_export(self, export: SandboxArtifactExport) -> SandboxArtifactExport:
        self._save("artifact_exports", export.artifact_export_id, export)
        return export

    def list_artifact_exports(self) -> list[SandboxArtifactExport]:
        return self._list("artifact_exports", SandboxArtifactExport)

    def get_artifact_export(self, export_id: str) -> SandboxArtifactExport | None:
        return self._get("artifact_exports", export_id, SandboxArtifactExport)

    def save_cleanup_preview(self, preview: SandboxCleanupPreview) -> SandboxCleanupPreview:
        self._save("cleanup_previews", preview.cleanup_preview_id, preview)
        return preview

    def get_cleanup_preview(self, preview_id: str) -> SandboxCleanupPreview | None:
        return self._get("cleanup_previews", preview_id, SandboxCleanupPreview)

    def _dir(self, name: str) -> Path:
        path = self.root / name
        path.mkdir(parents=True, exist_ok=True)
        return path

    def _save(self, collection: str, item_id: str, model: AIpinhoModel) -> None:
        path = self._dir(collection) / f"{item_id}.json"
        path.write_text(json.dumps(model.model_dump(), ensure_ascii=False, indent=2), encoding="utf-8")

    def _get(self, collection: str, item_id: str, model_type: type[T]) -> T | None:
        path = self._dir(collection) / f"{item_id}.json"
        if not path.exists():
            return None
        return model_type(**json.loads(path.read_text(encoding="utf-8")))

    def _list(self, collection: str, model_type: type[T]) -> list[T]:
        items = []
        for path in sorted(self._dir(collection).glob("*.json")):
            try:
                items.append(model_type(**json.loads(path.read_text(encoding="utf-8"))))
            except Exception:
                continue
        return items
