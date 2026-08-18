from __future__ import annotations

import re
from pathlib import Path
from typing import Any


WRITE_ACTIONS = {
    "write_files",
    "apply_patch",
    "create_file",
    "create_directory",
    "modify_file",
    "project_generation",
}


class ExecutablePlanService:
    """Validates whether a preview can become an executable approval."""

    def validate_draft(self, draft: Any | None) -> dict[str, Any]:
        if draft is None:
            return self._invalid("draft_missing")
        intent = getattr(draft, "intent_map", {}) if isinstance(getattr(draft, "intent_map", {}), dict) else {}
        contract_type = str(getattr(draft, "contract_type", "") or "")
        operation_type = str(getattr(draft, "operation_type", "") or "")
        runtime_profile = str(getattr(draft, "runtime_profile", "") or "")
        requested_actions = {str(item) for item in getattr(draft, "requested_actions", []) or []}
        approval_actions = {str(item) for item in getattr(draft, "approval_required_for", []) or []}

        requires_plan = bool(requested_actions.intersection(WRITE_ACTIONS) or approval_actions.intersection(WRITE_ACTIONS))
        requires_plan = requires_plan or contract_type in {"patch_request", "patch_apply", "filesystem_write", "project_generation"}
        requires_plan = requires_plan or runtime_profile in {"patch", "write_file", "project_generation"}
        if not requires_plan:
            return self._valid("no_write_execution_plan_required", "non_executable_or_readonly")

        quality = self._write_quality_reason(draft)
        if quality is not None:
            return self._invalid(quality)

        if contract_type in {"patch_request", "patch_apply"} or runtime_profile == "patch":
            executable_patch_plan = self._dict(intent.get("executable_patch_plan"))
            execution_preview = self._dict(intent.get("execution_preview"))
            if executable_patch_plan or execution_preview:
                if self._has_complete_executable_patch_plan(executable_patch_plan, execution_preview):
                    return self._valid(
                        str(
                            executable_patch_plan.get("executable_plan_id")
                            or draft.executable_plan_ref
                            or self._plan_ref(draft, "executable_patch_plan")
                        ),
                        "executable_patch_plan",
                    )
                return self._invalid(
                    self._execution_plan_gap_reason(executable_patch_plan, execution_preview),
                    plan_kind="executable_patch_plan",
                )
            patch_plan = self._dict(intent.get("patch_plan"))
            if self._has_concrete_patch_plan(patch_plan):
                return self._valid(self._plan_ref(draft, "patch_plan"), "patch_plan")
            return self._invalid("missing_patch_plan", plan_kind="patch_plan")

        if runtime_profile == "project_generation" or operation_type == "project_generation" or contract_type == "project_generation":
            plan = self._dict(intent.get("project_generation_plan"))
            if self._has_any_list(plan, ("files_to_create", "files_to_modify", "generation_steps", "validation_steps", "expected_outputs")):
                return self._valid(self._plan_ref(draft, "project_generation_plan"), "project_generation_plan")
            return self._invalid("missing_project_generation_plan", plan_kind="project_generation_plan")

        operations = intent.get("concrete_file_operations")
        if isinstance(operations, list) and any(self._concrete_operation(item) for item in operations):
            return self._valid(self._plan_ref(draft, "concrete_file_operations"), "concrete_file_operations")

        target_paths = intent.get("target_paths")
        if isinstance(target_paths, list) and any(self.is_real_path(str(item)) for item in target_paths):
            requested_operation = str(intent.get("requested_operation") or operation_type or "")
            if requested_operation in {"create_file", "create_directory", "modify_file", "filesystem_write_file", "filesystem_create_directory", "filesystem_modify_file"}:
                return self._valid(self._plan_ref(draft, "concrete_file_operations"), "concrete_file_operations")
        target_path = intent.get("target_path")
        requested_operation = str(intent.get("requested_operation") or operation_type or "")
        if target_path and self.is_real_path(str(target_path)):
            if requested_operation in {"create_file", "create_directory", "modify_file", "filesystem_write_file", "filesystem_create_directory", "filesystem_modify_file"}:
                return self._valid(self._plan_ref(draft, "concrete_file_operations"), "concrete_file_operations")

        return self._invalid("missing_executable_plan")

    def _write_quality_reason(self, draft: Any) -> str | None:
        intent = getattr(draft, "intent_map", {}) if isinstance(getattr(draft, "intent_map", {}), dict) else {}
        target_paths = self.real_target_paths(draft)
        expected = [str(item) for item in getattr(draft, "expected_outcomes", []) or [] if str(item).strip()]
        if not intent.get("context_ref"):
            return "PREVIEW_REJECTED_NO_CONTEXT_REF"
        if not target_paths:
            return "PREVIEW_REJECTED_NO_TARGET_FILES"
        if not expected:
            return "PREVIEW_REJECTED_NO_EXPECTED_OUTPUTS"
        if not intent.get("validation_plan"):
            return "PREVIEW_REJECTED_NO_VALIDATION_PLAN"
        if not intent.get("rollback_plan"):
            return "PREVIEW_REJECTED_NO_ROLLBACK_PLAN"
        if self._diagnostic_write(intent) and not intent.get("analysis_ref"):
            return "APPROVAL_NOT_CREATED_NO_ANALYSIS_REF"
        return None

    def expected_outcomes_for(self, draft: Any | None, validation: dict[str, Any] | None = None) -> list[str]:
        if draft is None:
            return []
        existing = [str(item) for item in getattr(draft, "expected_outcomes", []) or [] if str(item).strip()]
        if existing:
            return list(dict.fromkeys(existing))
        contract_type = str(getattr(draft, "contract_type", "") or "")
        runtime_profile = str(getattr(draft, "runtime_profile", "") or "")
        operation_type = str(getattr(draft, "operation_type", "") or "")
        if contract_type in {"patch_request", "patch_apply"} or runtime_profile == "patch":
            return ["patch_result", "validation_result"]
        if runtime_profile == "project_generation" or operation_type == "project_generation" or contract_type == "project_generation":
            return ["project_generation", "validation_result"]
        if runtime_profile == "write_file" or contract_type in {"filesystem_write", "file_modification"}:
            return ["filesystem_operation", "validation_result"]
        return []

    def real_target_paths(self, draft: Any | None, preview: Any | None = None) -> list[str]:
        candidates: list[str] = []
        if draft is not None:
            intent = getattr(draft, "intent_map", {}) if isinstance(getattr(draft, "intent_map", {}), dict) else {}
            for key in ("target_path", "output_path", "file_path", "path"):
                value = intent.get(key)
                if value:
                    candidates.append(str(value))
            target = intent.get("target")
            if isinstance(target, dict):
                for key in ("path", "file_path", "output_path"):
                    value = target.get(key)
                    if value:
                        candidates.append(str(value))
            for value in intent.get("target_paths", []) if isinstance(intent.get("target_paths"), list) else []:
                candidates.append(str(value))
            for key in ("execution_intent", "executable_patch_plan", "execution_preview"):
                payload = intent.get(key)
                if isinstance(payload, dict):
                    for nested_key in ("workspace", "target_file"):
                        value = payload.get(nested_key)
                        if value:
                            candidates.append(str(value))
                    for nested_key in ("target_files", "target_paths"):
                        values = payload.get(nested_key)
                        if isinstance(values, list):
                            candidates.extend(str(item) for item in values if item)
                    change_units = payload.get("change_units")
                    if isinstance(change_units, list):
                        for unit in change_units:
                            if isinstance(unit, dict) and unit.get("target_file"):
                                candidates.append(str(unit.get("target_file")))
            workspace_path = getattr(getattr(draft, "workspace", None), "path", None)
            if workspace_path:
                candidates.append(str(workspace_path))
        if preview is not None:
            for value in getattr(preview, "target_paths", []) or []:
                candidates.append(str(value))
        return list(dict.fromkeys(item for item in candidates if self.is_real_path(item)))

    def is_real_path(self, value: str) -> bool:
        text = str(value or "").strip().strip('"`')
        if not text:
            return False
        if re.search(r"^\w+:\s", text):
            return False
        if re.match(r"^[A-Za-z]:[\\/]", text):
            return True
        if text.startswith("\\\\"):
            return True
        try:
            path = Path(text)
            return path.is_absolute() or bool(path.parts and not any(part.endswith(":") for part in path.parts))
        except (OSError, ValueError):
            return False

    def _concrete_operation(self, item: Any) -> bool:
        if not isinstance(item, dict):
            return False
        action = str(item.get("action") or item.get("operation") or "")
        target = str(item.get("target_path") or item.get("path") or "")
        return action in {"create_file", "create_directory", "modify_file", "apply_patch", "write_files"} and self.is_real_path(target)

    def _has_concrete_patch_plan(self, patch_plan: dict[str, Any]) -> bool:
        entries = []
        for key in ("files_to_create", "files_to_modify", "patch_operations", "operations"):
            value = patch_plan.get(key)
            if isinstance(value, list):
                entries.extend(value)
        if patch_plan.get("diff_ref"):
            return bool(entries) and any(self._patch_target_is_file_like(item) for item in entries if isinstance(item, dict))
        return any(self._concrete_patch_entry(item) for item in entries)

    def _has_complete_executable_patch_plan(
        self,
        executable_patch_plan: dict[str, Any],
        execution_preview: dict[str, Any],
    ) -> bool:
        if str(executable_patch_plan.get("status") or "") != "complete":
            return False
        if str(execution_preview.get("status") or "") != "complete":
            return False
        target_paths = executable_patch_plan.get("target_paths")
        change_units = executable_patch_plan.get("change_units")
        rollback = executable_patch_plan.get("rollback_strategy")
        validation_steps = executable_patch_plan.get("validation_steps")
        if not isinstance(target_paths, list) or not any(self.is_real_path(str(item)) for item in target_paths):
            return False
        if not isinstance(change_units, list) or not change_units:
            return False
        if not all(isinstance(unit, dict) and unit.get("hunk_ids") for unit in change_units):
            return False
        if not isinstance(rollback, dict) or not str(rollback.get("strategy") or "").strip():
            return False
        if not isinstance(validation_steps, list) or not any(str(item).strip() for item in validation_steps):
            return False
        return True

    def _execution_plan_gap_reason(
        self,
        executable_patch_plan: dict[str, Any],
        execution_preview: dict[str, Any],
    ) -> str:
        for payload in (execution_preview, executable_patch_plan):
            diagnostics = payload.get("diagnostics")
            if isinstance(diagnostics, list):
                for item in diagnostics:
                    text = str(item).strip()
                    if text:
                        return text
        return "executable_patch_plan_incomplete"

    def _concrete_patch_entry(self, item: Any) -> bool:
        if not isinstance(item, dict):
            return False
        if not self._patch_target_is_file_like(item):
            return False
        return any(
            item.get(key)
            for key in (
                "content",
                "text",
                "body",
                "lines",
                "diff",
                "patch",
                "diff_ref",
                "hunks",
                "original",
                "replacement",
            )
        )

    def _patch_target_is_file_like(self, item: dict[str, Any]) -> bool:
        target = str(item.get("path") or item.get("target_path") or item.get("file_path") or item.get("relative_path") or "")
        if not self.is_real_path(target):
            return False
        try:
            path = Path(target)
            if path.exists() and path.is_dir():
                return False
        except (OSError, ValueError):
            return False
        return True

    def _diagnostic_write(self, intent: dict[str, Any]) -> bool:
        raw = f"{intent.get('prompt', '')} {intent.get('raw_prompt', '')}".casefold()
        if str(intent.get("intent")) in {"workspace_fix_request", "diagnostic_fix_request"}:
            return True
        return any(term in raw for term in ("analise e corrija", "diagnostique e corrija", "corrija os problemas"))

    def _has_any_list(self, payload: dict[str, Any], keys: tuple[str, ...]) -> bool:
        return any(isinstance(payload.get(key), list) and bool(payload.get(key)) for key in keys)

    def _dict(self, value: Any) -> dict[str, Any]:
        return value if isinstance(value, dict) else {}

    def _plan_ref(self, draft: Any, plan_kind: str) -> str:
        explicit = getattr(draft, "executable_plan_ref", None)
        if explicit:
            return str(explicit)
        return f"{getattr(draft, 'draft_id', 'draft')}:{plan_kind}"

    def _valid(self, ref: str, plan_kind: str) -> dict[str, Any]:
        return {"valid": True, "reason_code": "executable_plan_found", "executable_plan_ref": ref, "plan_kind": plan_kind}

    def _invalid(self, reason_code: str, *, plan_kind: str | None = None) -> dict[str, Any]:
        return {"valid": False, "reason_code": reason_code, "executable_plan_ref": None, "plan_kind": plan_kind}
