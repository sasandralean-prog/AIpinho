from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from aipinho.core.paths import PATHS
from aipinho.schemas.runtime.task_run import TaskRun
from aipinho.schemas.runtime.task_run_request import TaskRunRequest
from aipinho.schemas.runtime.workspace_context import ExecutionContext, RetrievalContext, WorkspaceContext
from aipinho.services.config_governance.workspace_permission_matrix_service import WorkspacePermissionMatrixService
from aipinho.services.session.session_store import utc_now


class WorkspaceContextService:
    """Canonical workspace authority for runtime consumers."""

    def __init__(self, matrix: WorkspacePermissionMatrixService | None = None) -> None:
        self.matrix = matrix or WorkspacePermissionMatrixService().load()

    def from_request(self, request: TaskRunRequest, *, runtime_profile: str | None = None) -> WorkspaceContext:
        intent = request.intent_map if isinstance(request.intent_map, dict) else {}
        return self.resolve(
            workspace_id=request.workspace_id,
            workspace_path=request.workspace,
            project_id=request.project_id,
            runtime_profile=runtime_profile or request.runtime_profile,
            current_phase=str(request.intent_map.get("current_phase") or request.intent_map.get("phase") or "") or None,
            current_task=request.task_id,
            external_roots=self._list(intent.get("external_roots")),
            library_roots=self._list(intent.get("library_roots")),
            readonly_flags=self._dict(intent.get("readonly_flags")),
            workspace_ids=self._list(intent.get("workspace_ids")),
        )

    def from_run(self, run: TaskRun) -> WorkspaceContext:
        if run.workspace_context is not None:
            return run.workspace_context
        return self.resolve(
            workspace_id=run.workspace_id,
            workspace_path=run.workspace,
            project_id=run.project_id,
            runtime_profile=run.runtime_profile,
            current_phase=run.current_phase,
            current_task=run.task_id or run.run_id,
            external_roots=list(run.workspace_context.external_roots) if run.workspace_context else [],
            library_roots=list(run.workspace_context.library_roots) if run.workspace_context else [],
            readonly_flags=dict(run.workspace_context.readonly_flags) if run.workspace_context else {},
            workspace_ids=list(run.workspace_context.workspace_ids) if run.workspace_context else [],
        )

    def resolve(
        self,
        *,
        workspace_id: str | None = None,
        workspace_path: str | None = None,
        project_id: str | None = None,
        runtime_profile: str | None = None,
        current_phase: str | None = None,
        current_task: str | None = None,
        external_roots: list[str] | None = None,
        library_roots: list[str] | None = None,
        readonly_flags: dict[str, bool] | None = None,
        workspace_ids: list[str] | None = None,
    ) -> WorkspaceContext:
        entry = self._entry_for(workspace_id=workspace_id, workspace_path=workspace_path)
        warnings: list[str] = []
        path = workspace_path
        role = None
        resolved_workspace_id = workspace_id
        registered_root = None
        if entry is not None:
            resolved_workspace_id = str(entry.get("workspace_id") or resolved_workspace_id or "")
            registered_root = str(entry.get("root_path") or "") or None
            path = workspace_path or registered_root or path or ""
            role = str(entry.get("role") or "") or None
        elif workspace_path:
            decision = self.matrix.decide(path=workspace_path, permission="read_file")
            resolved_workspace_id = decision.workspace_id or workspace_id or self._synthetic_workspace_id(workspace_path)
            role = decision.workspace_role
            if decision.status == "denied":
                warnings.append(decision.reason_code)
        elif workspace_id:
            warnings.append("workspace_id_not_registered")

        project_root = str(Path(path).expanduser().resolve(strict=False)) if path else None
        allowed_root = str(Path(registered_root).expanduser().resolve(strict=False)) if registered_root else project_root
        external = [self._resolve_path(item) for item in (external_roots or []) if item]
        libraries = [self._resolve_path(item) for item in (library_roots or []) if item]
        allowed_roots = [item for item in [allowed_root, *external, *libraries] if item]
        resolved_workspace_ids = list(dict.fromkeys([item for item in [resolved_workspace_id, *(workspace_ids or [])] if item]))
        artifact_store = str((PATHS.project_root / "data" / "runtime" / "artifacts").resolve(strict=False))
        resolved_project_id = project_id or (f"project_{resolved_workspace_id}" if resolved_workspace_id else None)
        project_name = Path(project_root).name if project_root else None
        retrieval_scope = {
            "scope_type": "project" if project_root else "runtime",
            "workspace": project_root,
            "workspace_id": resolved_workspace_id,
            "project": resolved_project_id,
            "allowed_roots": allowed_roots,
            "source": "WorkspaceContextService",
        }
        return WorkspaceContext(
            workspace_id=resolved_workspace_id or None,
            workspace_path=project_root,
            workspace_role=role,
            project_id=resolved_project_id,
            project_name=project_name,
            project_root=project_root,
            external_roots=external,
            library_roots=libraries,
            readonly_flags=readonly_flags or {},
            workspace_ids=resolved_workspace_ids,
            artifact_store=artifact_store,
            retrieval_scope=retrieval_scope,
            allowed_roots=allowed_roots,
            runtime_profile=runtime_profile,
            current_phase=current_phase,
            current_task=current_task,
            warnings=list(dict.fromkeys(warnings)),
        )

    def _entry_for(self, *, workspace_id: str | None, workspace_path: str | None) -> dict[str, Any] | None:
        if workspace_id:
            entry = self.matrix.get_workspace(workspace_id)
            if entry is not None:
                return entry
        if workspace_path:
            selected = self.matrix._select_workspace(workspace_path)  # central registry selection; not a local heuristic.
            if selected is not None:
                entry, _root = selected
                return entry
        return None

    def _synthetic_workspace_id(self, workspace_path: str) -> str:
        digest = hashlib.sha256(str(workspace_path).casefold().encode("utf-8")).hexdigest()[:12]
        name = Path(workspace_path).name or "workspace"
        safe = "".join(ch.lower() if ch.isalnum() else "_" for ch in name).strip("_")
        return f"workspace_{safe or 'root'}_{digest}"

    def _resolve_path(self, value: str) -> str:
        return str(Path(str(value)).expanduser().resolve(strict=False))

    def _list(self, value: Any) -> list[str]:
        if value is None:
            return []
        if isinstance(value, str):
            return [value]
        if isinstance(value, list):
            return [str(item) for item in value if item]
        return []

    def _dict(self, value: Any) -> dict[str, bool]:
        if isinstance(value, dict):
            return {str(key): bool(item) for key, item in value.items()}
        return {}


class RetrievalContextService:
    def from_workspace_context(
        self,
        workspace_context: WorkspaceContext,
        *,
        task_id: str | None = None,
        task_run_id: str | None = None,
        phase: str | None = None,
    ) -> RetrievalContext:
        blocked: list[str] = []
        if not workspace_context.workspace_id:
            blocked.append("workspace_context_missing_workspace_id")
        if not workspace_context.allowed_roots:
            blocked.append("workspace_context_missing_allowed_roots")
        return RetrievalContext(
            workspace_id=workspace_context.workspace_id,
            retrieval_scope=dict(workspace_context.retrieval_scope),
            allowed_roots=list(workspace_context.allowed_roots),
            artifact_scope=workspace_context.artifact_store,
            runtime_profile=workspace_context.runtime_profile,
            task_id=task_id,
            task_run_id=task_run_id,
            phase=phase or workspace_context.current_phase,
            valid=not blocked,
            blocked_reasons=blocked,
        )


class ExecutionContextService:
    def __init__(
        self,
        workspace_contexts: WorkspaceContextService | None = None,
        retrieval_contexts: RetrievalContextService | None = None,
    ) -> None:
        self.workspace_contexts = workspace_contexts or WorkspaceContextService()
        self.retrieval_contexts = retrieval_contexts or RetrievalContextService()

    def create_for_run(self, run: TaskRun) -> ExecutionContext:
        workspace_context = self.workspace_contexts.from_run(run)
        retrieval_context = self.retrieval_contexts.from_workspace_context(
            workspace_context,
            task_id=run.task_id,
            task_run_id=run.run_id,
            phase=run.current_phase,
        )
        return ExecutionContext(
            task_id=run.task_id,
            task_run_id=run.run_id,
            operation_id=run.operation_id,
            session_id=run.session_id,
            workspace_context=workspace_context,
            retrieval_context=retrieval_context,
            project_context={
                "project_id": workspace_context.project_id,
                "project_name": workspace_context.project_name,
                "project_root": workspace_context.project_root,
            },
            runtime_context={
                "runtime_profile": run.runtime_profile,
                "contract_type": run.contract_type,
                "operation_type": run.operation_type,
            },
            current_phase=run.current_phase,
            dependencies=[
                dependency.model_dump(mode="json")
                for dependency in (run.workflow.dependencies if run.workflow else [])
            ],
            runtime_profile=run.runtime_profile,
        )

    def record_phase(self, run: TaskRun, *, phase_id: str | None, status: str, event_id: str | None = None) -> ExecutionContext:
        context = run.execution_context or self.create_for_run(run)
        context.current_phase = phase_id or context.current_phase
        context.phase_history.append({"phase_id": phase_id, "status": status, "event_id": event_id, "at": utc_now()})
        context.updated_at = utc_now()
        return context

    def record_artifacts(self, run: TaskRun, artifacts: list[dict[str, Any]]) -> ExecutionContext:
        context = run.execution_context or self.create_for_run(run)
        context.artifacts.extend(artifacts)
        context.updated_at = utc_now()
        return context
