from __future__ import annotations

import hashlib
import re
from typing import Any
from uuid import uuid4

from aipinho.schemas.runtime.task_bootstrap import (
    TaskBootstrapRequest,
    TaskBootstrapResult,
    UniversalTask,
)
from aipinho.services.runtime.task_run_store import TaskRunStore


_SAFE_ID = re.compile(r"[^A-Za-z0-9_]+")


class TaskBootstrapRuntimeService:
    """Creates canonical task identity before any executable runtime action."""

    def __init__(self, *, store: TaskRunStore | None = None) -> None:
        self.store = store

    def bootstrap(self, request: TaskBootstrapRequest) -> TaskBootstrapResult:
        runtime_profile = request.runtime_profile or self._runtime_profile_from(request)
        task = UniversalTask(
            task_id=request.task_id or f"task_{uuid4().hex}",
            operation_id=request.operation_id or self._operation_id_from(request),
            task_run_id=request.task_run_id or f"task_run_{uuid4().hex}",
            runtime_profile=runtime_profile,
            workspace_id=request.workspace_id or self._workspace_id_from(request),
            project_id=request.project_id or self._project_id_from(request),
            session_id=request.session_id,
            workspace=request.workspace,
            operation_type=request.operation_type,
            contract_type=request.contract_type,
            current_sprint=self._first_text(request.intent_map, "current_sprint", "sprint_id", "sprint"),
            current_phase=self._first_text(request.intent_map, "current_phase", "phase_id", "phase"),
            parent_task_id=request.parent_task_id or self._first_text(request.intent_map, "parent_task_id", "parent_task"),
            source_channel=request.source_channel or str(request.intent_map.get("source_channel") or "runtime"),
            context={
                "requested_actions": list(request.requested_actions),
                "intent_type": request.intent_map.get("intent_type"),
                "operation_type": request.operation_type or request.intent_map.get("operation_type"),
                "requires_task": True,
                "bootstrap_invariant": "execution_requires_universal_task",
            },
        )
        return TaskBootstrapResult(universal_task=task)

    def lookup(self, task_id: str) -> dict[str, Any] | None:
        if self.store is None:
            return None
        run = self.store.get_run_by_task_id(task_id)
        if run is None:
            return None
        return {
            "task_id": run.task_id,
            "task_run_id": run.run_id,
            "operation_id": run.operation_id,
            "status": run.status,
            "runtime": run.runtime_profile,
            "workspace": run.workspace,
            "workspace_id": run.workspace_id,
            "project_id": run.project_id,
            "phase": run.current_phase,
            "parent_task_id": run.parent_task_id,
            "session_id": run.session_id,
            "created_at": run.created_at,
            "source": "task_run_store",
        }

    def _runtime_profile_from(self, request: TaskBootstrapRequest) -> str:
        return str(
            request.intent_map.get("runtime_profile")
            or request.operation_type
            or request.contract_type
            or "runtime"
        )

    def _operation_id_from(self, request: TaskBootstrapRequest) -> str:
        candidate = request.intent_map.get("operation_id")
        if isinstance(candidate, str) and candidate.startswith(("op_", "chatop_", "operation_")):
            return candidate
        return f"op_{uuid4().hex}"

    def _workspace_id_from(self, request: TaskBootstrapRequest) -> str | None:
        candidate = self._first_text(request.intent_map, "workspace_id", "resolved_workspace_id")
        if candidate:
            return candidate
        if not request.workspace:
            return None
        digest = hashlib.sha256(str(request.workspace).casefold().encode("utf-8")).hexdigest()[:12]
        name = _SAFE_ID.sub("_", str(request.workspace).rstrip("\\/").split("\\")[-1].split("/")[-1]).strip("_").lower()
        return f"workspace_{name or 'root'}_{digest}"

    def _project_id_from(self, request: TaskBootstrapRequest) -> str | None:
        candidate = self._first_text(request.intent_map, "project_id")
        if candidate:
            return candidate
        if not request.workspace:
            return None
        digest = hashlib.sha256(str(request.workspace).casefold().encode("utf-8")).hexdigest()[:10]
        name = _SAFE_ID.sub("_", str(request.workspace).rstrip("\\/").split("\\")[-1].split("/")[-1]).strip("_").lower()
        return f"project_{name or 'workspace'}_{digest}"

    def _first_text(self, values: dict[str, Any], *keys: str) -> str | None:
        for key in keys:
            value = values.get(key)
            if value is None:
                continue
            text = str(value).strip()
            if text:
                return text
        return None
