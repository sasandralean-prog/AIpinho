from __future__ import annotations

from typing import Any

from aipinho.schemas.governance.lifecycle import (
    CanonicalExecutionPlan,
    CanonicalOperationContract,
    GovernanceLifecycleReasonCode,
    PreviewKind,
)


class CanonicalRuntimeService:
    """Builds the canonical execution plan before any approval/run can exist."""

    WRITE_OR_EXECUTE = {"write_files", "write_file", "create_file", "modify_file", "apply_patch", "project_generation", "create_directory", "run_command", "run_tests"}

    def build_plan(
        self,
        contract: CanonicalOperationContract,
        *,
        executable_plan_ref: str | None = None,
        plan_kind: str | None = None,
        expected_outputs: list[str] | None = None,
        target_paths: list[str] | None = None,
        plan_payload: dict[str, Any] | None = None,
    ) -> CanonicalExecutionPlan:
        actions = set(contract.requested_actions)
        outputs = list(dict.fromkeys(self.default_expected_outputs(contract) if expected_outputs is None else expected_outputs))
        readonly_artifact_execution = (
            bool(executable_plan_ref)
            and contract.runtime_profile == "readonly_analysis"
            and "artifact_result" in outputs
        )
        needs_execution_plan = (
            bool(actions.intersection(self.WRITE_OR_EXECUTE))
            or contract.runtime_profile in {"project_generation", "patch", "write_file"}
            or readonly_artifact_execution
        )
        targets = list(dict.fromkeys(target_paths or contract.target_paths))
        if not needs_execution_plan:
            return CanonicalExecutionPlan(
                preview_kind=PreviewKind.PLAN_ONLY,
                executable=False,
                expected_outputs=outputs,
                target_paths=targets,
                blocked_reason=GovernanceLifecycleReasonCode.READONLY_OR_PLANNING,
                trace=[{"stage": "canonical_runtime", "mode": "plan_only"}],
            )
        if executable_plan_ref:
            return CanonicalExecutionPlan(
                preview_kind=PreviewKind.EXECUTABLE,
                executable=True,
                executable_plan_ref=executable_plan_ref,
                plan_kind=plan_kind or "executable_plan",
                expected_outputs=outputs,
                target_paths=targets,
                trace=[{"stage": "canonical_runtime", "mode": "executable", "payload_keys": sorted((plan_payload or {}).keys())}],
            )
        return CanonicalExecutionPlan(
            preview_kind=PreviewKind.PLAN_ONLY,
            executable=False,
            expected_outputs=outputs,
            target_paths=targets,
            blocked_reason=GovernanceLifecycleReasonCode.MISSING_EXECUTABLE_PLAN,
            trace=[{"stage": "canonical_runtime", "mode": "missing_executable_plan"}],
        )

    def default_expected_outputs(self, contract: CanonicalOperationContract) -> list[str]:
        if contract.contract_type == "analysis_readonly" or contract.operation_type == "workspace_analysis_readonly":
            return ["project_analysis_report", "artifact_result", "validation_result"]
        if contract.runtime_profile == "project_generation" or contract.operation_type == "project_generation":
            return ["project_generation_result", "validation_result"]
        if contract.contract_type in {"patch_request", "patch_apply"} or contract.runtime_profile == "patch":
            return ["patch_result", "validation_result"]
        if any(action in {"create_file", "create_directory", "write_file", "write_files", "modify_file"} for action in contract.requested_actions):
            return ["filesystem_operation", "validation_result"]
        if any(action in {"run_command", "run_tests"} for action in contract.requested_actions):
            return ["command_result", "validation_result"]
        if "artifact_create" in contract.requested_actions:
            return ["artifact_result", "validation_result"]
        return []
