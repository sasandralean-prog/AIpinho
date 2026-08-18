from __future__ import annotations

from pathlib import Path
from typing import Any

from aipinho.core.paths import PATHS
from aipinho.schemas.tools.tool_call import ToolCall
from aipinho.schemas.tools.tool_definition import ToolDefinition
from aipinho.schemas.tools.tool_safety import ToolInputValidationResult
from aipinho.services.policy_kernel.workspace_policy_service import WorkspacePolicyService
from aipinho.services.tools.tool_trace_service import ToolTraceService
from aipinho.utils.yaml_loader import load_yaml_file


class ToolInputValidator:
    def __init__(self, config_path: Path | None = None, trace: ToolTraceService | None = None) -> None:
        self.config_path = config_path or PATHS.config_root / "policies" / "tool_dry_run_policy.yaml"
        self.config = load_yaml_file(self.config_path, critical=True, root=self.config_path.parent)
        self.trace = trace or ToolTraceService()
        self.workspace_policy = WorkspacePolicyService().load()

    def validate(self, tool: ToolDefinition, call: ToolCall) -> ToolInputValidationResult:
        schema = tool.input_schema or {}
        required = set(schema.get("required", []) or [])
        properties: dict[str, Any] = schema.get("properties", {}) if isinstance(schema.get("properties", {}), dict) else {}
        violations: list[str] = []
        warnings: list[str] = []
        trace = []

        if not isinstance(call.input, dict):
            violations.append("input_not_object")

        for field in sorted(required):
            if field not in call.input:
                violations.append(f"missing_required:{field}")

        for key, value in call.input.items():
            expected = properties.get(key, {}) if isinstance(properties, dict) else {}
            expected_type = expected.get("type") if isinstance(expected, dict) else None
            if key not in properties:
                warnings.append(f"unknown_input_field:{key}")
                continue
            if expected_type == "string" and not isinstance(value, str):
                violations.append(f"wrong_type:{key}:string")
            elif expected_type == "boolean" and not isinstance(value, bool):
                violations.append(f"wrong_type:{key}:boolean")
            elif expected_type == "object" and not isinstance(value, dict):
                violations.append(f"wrong_type:{key}:object")
            if key in {"path", "workspace"} and isinstance(value, str):
                workspace = self.workspace_policy.evaluate(workspace_path=value, requires_workspace=True)
                if workspace.blocked:
                    violations.append("forbidden_root")
                    trace.append(self.trace.item(
                        stage="tool_input_validation",
                        rule="forbidden_root",
                        decision="blocked",
                        reason="path_matches_protected_workspace",
                        severity="critical",
                        source="config/workspaces/protected_workspaces.yaml",
                        data={"field": key, "path": value},
                    ))

        if violations:
            trace.append(self.trace.item(
                stage="tool_input_validation",
                rule="input_schema",
                decision="invalid",
                reason="tool_input_failed_validation",
                severity="error",
                source="tool.input_schema",
                data={"violations": violations},
            ))
            return ToolInputValidationResult(status="invalid", input_valid=False, violations=violations, warnings=warnings, trace=trace)

        trace.append(self.trace.item(
            stage="tool_input_validation",
            rule="input_schema",
            decision="valid",
            reason="tool_input_validated_without_real_io",
            source="tool.input_schema",
            data={"warnings": warnings},
        ))
        return ToolInputValidationResult(status="valid", input_valid=True, violations=[], warnings=warnings, trace=trace)
