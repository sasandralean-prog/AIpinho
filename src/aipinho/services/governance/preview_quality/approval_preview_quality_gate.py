from __future__ import annotations

from pathlib import Path
from typing import Any

from aipinho.schemas.governance.lifecycle import (
    CanonicalExecutionPlan,
    CanonicalOperationContract,
    ContextGateDecision,
    GovernanceLifecycleReasonCode,
    PreviewQualityDecision,
)


class ApprovalPreviewQualityGate:
    """Rejects generic or unauditable write approvals."""

    WRITE_ACTIONS = {"write_files", "write_file", "create_file", "modify_file", "apply_patch", "project_generation", "create_directory"}

    def evaluate(
        self,
        *,
        contract: CanonicalOperationContract,
        plan: CanonicalExecutionPlan,
        context_gate: ContextGateDecision,
        plan_payload: dict[str, Any] | None = None,
        validation_plan: dict[str, Any] | list[Any] | None = None,
        rollback_plan: dict[str, Any] | list[Any] | None = None,
    ) -> PreviewQualityDecision:
        if not set(contract.requested_actions).intersection(self.WRITE_ACTIONS):
            return PreviewQualityDecision(status="not_required", can_create_approval=True)
        if not context_gate.can_create_write_approval:
            return PreviewQualityDecision(
                status=context_gate.reason_code.value,
                can_create_approval=False,
                reason_code=context_gate.reason_code,
                missing_requirements=list(context_gate.missing_requirements),
                trace=[{"stage": "preview_quality_gate", "mode": "blocked_by_context_gate"}],
            )
        payload = plan_payload or {}
        if not context_gate.context_ref:
            return self._reject(GovernanceLifecycleReasonCode.PREVIEW_REJECTED_NO_CONTEXT_REF, "context_ref")
        if not plan.target_paths:
            return self._reject(GovernanceLifecycleReasonCode.PREVIEW_REJECTED_NO_TARGET_FILES, "target_files")
        if not plan.executable_plan_ref:
            return self._reject(GovernanceLifecycleReasonCode.PREVIEW_REJECTED_NO_EXECUTABLE_PLAN, "executable_plan_ref")
        if not plan.expected_outputs:
            return self._reject(GovernanceLifecycleReasonCode.PREVIEW_REJECTED_NO_EXPECTED_OUTPUTS, "expected_outputs")
        if not validation_plan:
            return self._reject(GovernanceLifecycleReasonCode.PREVIEW_REJECTED_NO_VALIDATION_PLAN, "validation_plan")
        if not rollback_plan:
            return self._reject(GovernanceLifecycleReasonCode.PREVIEW_REJECTED_NO_ROLLBACK_PLAN, "rollback_plan")
        if plan.plan_kind == "project_generation_plan" and self._project_generation_plan_missing_file_content(payload.get("project_generation_plan")):
            return self._reject(GovernanceLifecycleReasonCode.PREVIEW_REJECTED_NO_EXECUTABLE_PLAN, "file_content")
        if plan.plan_kind == "patch_plan" and not self._patch_plan_has_concrete_operations(payload.get("patch_plan")):
            return self._reject(GovernanceLifecycleReasonCode.PREVIEW_REJECTED_NO_EXECUTABLE_PLAN, "concrete_patch_operations")
        if self._generic_write_action(contract, plan, payload):
            return self._reject(GovernanceLifecycleReasonCode.PREVIEW_REJECTED_GENERIC_WRITE_ACTION, "concrete_plan")
        return PreviewQualityDecision(
            status="ready",
            can_create_approval=True,
            trace=[{"stage": "preview_quality_gate", "mode": "ready", "plan_kind": plan.plan_kind}],
        )

    def _generic_write_action(
        self,
        contract: CanonicalOperationContract,
        plan: CanonicalExecutionPlan,
        payload: dict[str, Any],
    ) -> bool:
        if set(contract.requested_actions) != {"write_files"}:
            return False
        if plan.plan_kind in {"project_generation_plan", "concrete_file_operations", "patch_plan"}:
            return False
        return not any(payload.get(key) for key in ("project_generation_plan", "concrete_file_operations", "patch_plan"))

    def _project_generation_plan_missing_file_content(self, value: Any) -> bool:
        if not isinstance(value, dict):
            return False
        entries = [*self._list(value.get("files_to_create")), *self._list(value.get("files_to_modify"))]
        if not entries:
            return False
        for entry in entries:
            if not isinstance(entry, dict):
                return True
            content = entry.get("content") or entry.get("text") or entry.get("body")
            lines = entry.get("lines")
            if content is None and not (isinstance(lines, list) and lines):
                return True
        return False

    def _patch_plan_has_concrete_operations(self, value: Any) -> bool:
        if not isinstance(value, dict):
            return False
        entries = [
            *self._list(value.get("files_to_create")),
            *self._list(value.get("files_to_modify")),
            *self._list(value.get("patch_operations")),
            *self._list(value.get("operations")),
        ]
        if value.get("diff_ref"):
            return any(self._patch_target_is_file_like(entry) for entry in entries) or bool(entries)
        return any(self._concrete_patch_entry(entry) for entry in entries)

    def _concrete_patch_entry(self, entry: Any) -> bool:
        if not isinstance(entry, dict):
            return False
        if not self._patch_target_is_file_like(entry):
            return False
        return any(
            entry.get(key)
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

    def _patch_target_is_file_like(self, entry: Any) -> bool:
        if not isinstance(entry, dict):
            return False
        target = entry.get("path") or entry.get("target_path") or entry.get("file_path") or entry.get("relative_path")
        if not target:
            return False
        text = str(target).strip().strip('"`')
        if not text or text.endswith(("/", "\\")):
            return False
        try:
            path = Path(text)
            if path.exists() and path.is_dir():
                return False
        except (OSError, ValueError):
            return False
        return True

    def _list(self, value: Any) -> list[Any]:
        return value if isinstance(value, list) else []

    def _reject(self, reason_code: GovernanceLifecycleReasonCode, missing: str) -> PreviewQualityDecision:
        return PreviewQualityDecision(
            status=reason_code.value,
            can_create_approval=False,
            reason_code=reason_code,
            missing_requirements=[missing],
            trace=[{"stage": "preview_quality_gate", "mode": "rejected", "reason_code": reason_code.value}],
        )
