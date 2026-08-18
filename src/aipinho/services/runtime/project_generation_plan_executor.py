from __future__ import annotations

from pathlib import Path
from typing import Any

from aipinho.schemas.runtime.task_run import TaskRun
from aipinho.services.orchestration.task_draft_store import TaskDraftStore


class ProjectGenerationPlanExecutor:
    """Executes an approved project_generation_plan without prompt heuristics."""

    def __init__(self, draft_store: TaskDraftStore | None = None) -> None:
        self.draft_store = draft_store or TaskDraftStore()

    def execute(self, run: TaskRun) -> dict[str, Any] | None:
        plan = self._plan(run)
        if plan is None:
            return None
        workspace = self._workspace(run, plan)
        if workspace is None:
            return self._blocked("workspace_required", plan_kind="project_generation_plan")

        base = workspace.resolve(strict=False)
        created_directories: list[str] = []
        created_files: list[str] = []
        modified_files: list[str] = []

        for entry in self._list(plan.get("directories_to_create")):
            target = self._target(base, entry)
            if target is None:
                return self._blocked("invalid_directory_target", target=entry)
            if not self._is_within(base, target):
                return self._blocked("target_path_outside_workspace", target=str(target), workspace=str(base))
            target.mkdir(parents=True, exist_ok=True)
            created_directories.append(str(target))

        for key, default_overwrite in (("files_to_create", False), ("files_to_modify", True)):
            for entry in self._list(plan.get(key)):
                target = self._target(base, entry)
                if target is None:
                    return self._blocked("invalid_file_target", target=entry)
                if not self._is_within(base, target):
                    return self._blocked("target_path_outside_workspace", target=str(target), workspace=str(base))
                content = self._content(entry)
                if content is None:
                    return self._blocked("file_content_missing", target=str(target))
                if content == "[omitted_by_task_run_store]":
                    return self._blocked("file_content_omitted_by_sanitization", target=str(target))
                overwrite = bool(entry.get("overwrite", default_overwrite)) if isinstance(entry, dict) else default_overwrite
                if target.exists() and key == "files_to_create" and not overwrite:
                    return self._blocked("target_file_already_exists", target=str(target))
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(content, encoding=str(entry.get("encoding") or "utf-8") if isinstance(entry, dict) else "utf-8")
                if key == "files_to_create" and str(target) not in created_files:
                    created_files.append(str(target))
                if key == "files_to_modify" and str(target) not in modified_files:
                    modified_files.append(str(target))

        if not created_files and not modified_files and not created_directories:
            return self._blocked("project_generation_plan_empty")

        expected_outputs = [str(item) for item in self._list(plan.get("expected_outputs"))]
        validation_steps = [str(item) for item in self._list(plan.get("validation_steps"))]
        return {
            "status": "succeeded",
            "executor": "project_generation_plan_executor",
            "plan_kind": "project_generation_plan",
            "workspace": str(base),
            "created_directories": created_directories,
            "created_files": created_files,
            "modified_files": modified_files,
            "expected_outputs": expected_outputs,
            "validation_steps": validation_steps,
            "files_written": bool(created_files or modified_files),
            "directories_written": bool(created_directories),
        }

    def _plan(self, run: TaskRun) -> dict[str, Any] | None:
        intent = run.intent_map if isinstance(run.intent_map, dict) else {}
        plan = intent.get("project_generation_plan")
        if run.draft_id:
            draft = self.draft_store.get(run.draft_id)
            draft_intent = draft.intent_map if draft is not None and isinstance(draft.intent_map, dict) else {}
            draft_plan = draft_intent.get("project_generation_plan")
            if isinstance(draft_plan, dict):
                return draft_plan
        if isinstance(plan, dict) and self._plan_has_usable_content(plan):
            return plan
        return plan if isinstance(plan, dict) else None

    def _plan_has_usable_content(self, plan: dict[str, Any]) -> bool:
        entries = [*self._list(plan.get("files_to_create")), *self._list(plan.get("files_to_modify"))]
        if not entries:
            return True
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            value = entry.get("content") or entry.get("text") or entry.get("body")
            if value is not None and str(value) != "[omitted_by_task_run_store]":
                return True
            lines = entry.get("lines")
            if isinstance(lines, list) and lines:
                return True
        return False

    def _workspace(self, run: TaskRun, plan: dict[str, Any]) -> Path | None:
        raw = run.workspace or plan.get("target_workspace")
        if not isinstance(raw, str) or not raw.strip():
            return None
        return Path(raw.strip().strip('"`'))

    def _target(self, base: Path, entry: Any) -> Path | None:
        if isinstance(entry, str):
            raw = entry
        elif isinstance(entry, dict):
            raw = entry.get("target_path") or entry.get("path") or entry.get("relative_path")
        else:
            return None
        if not isinstance(raw, str) or not raw.strip():
            return None
        target = Path(raw.strip().strip('"`'))
        if not target.is_absolute():
            target = base / target
        return target.resolve(strict=False)

    def _content(self, entry: Any) -> str | None:
        if not isinstance(entry, dict):
            return None
        for key in ("content", "text", "body"):
            value = entry.get(key)
            if value is not None:
                return str(value)
        lines = entry.get("lines")
        if isinstance(lines, list):
            return "\n".join(str(line) for line in lines)
        return None

    def _list(self, value: Any) -> list[Any]:
        return value if isinstance(value, list) else []

    def _is_within(self, base: Path, target: Path) -> bool:
        try:
            target.relative_to(base)
            return True
        except ValueError:
            return False

    def _blocked(self, reason_code: str, **metadata: Any) -> dict[str, Any]:
        return {
            "status": "blocked",
            "executor": "project_generation_plan_executor",
            "reason_code": reason_code,
            **metadata,
        }
