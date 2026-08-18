from __future__ import annotations

from typing import Any

from aipinho.core.paths import PATHS
from aipinho.services.validation.validation_common import as_dict, collect_strings, finding
from aipinho.utils.yaml_loader import load_yaml_file

ACTION_KEYS = {
    "action",
    "action_id",
    "action_type",
    "actions",
    "executed_action",
    "executed_actions",
    "tool",
    "tool_id",
    "tool_name",
    "tools",
    "command",
    "command_id",
    "command_type",
    "capability",
    "capabilities",
    "side_effect",
    "side_effects",
}

STRUCTURAL_KEYS = {
    "event",
    "events",
    "trace",
    "audit",
    "audit_events",
    "result",
    "outputs",
    "final_output",
    "tool_calls",
    "dry_run",
}


class SideEffectValidator:
    def __init__(self) -> None:
        self.policy = load_yaml_file(PATHS.config_root / "validation" / "side_effect_validation_policy.yaml", critical=True, root=PATHS.config_root / "validation")
        self.blocked = set(self.policy.get("blocked_workspace_effects", []) or [])

    def validate(self, payload: Any) -> list:
        data = as_dict(payload)
        if self._is_governed_patch_apply(data):
            return []
        strings = [item.lower() for item in self._collect_operational_tokens(data)]
        findings = []
        checks = {
            "write_files": "workspace write action detected",
            "delete_files": "workspace delete action detected",
            "move_files": "workspace move action detected",
            "apply_patch": "patch action detected",
            "patch_apply": "patch action detected",
            "run_command": "shell command action detected",
            "shell": "shell action detected",
            "git_commit": "git write action detected",
            "git_push": "git write action detected",
            "memory_write": "memory write action detected",
            "write_memory": "memory write action detected",
            "rag_ingest": "RAG ingest action detected",
            "model_tool_calling": "model tool calling detected",
        }
        for token, message in checks.items():
            if any(token in item for item in strings):
                code = "side_effect_violation"
                if "patch" in token:
                    code = "patch_detected"
                elif token in {"run_command", "shell"}:
                    code = "shell_detected"
                findings.append(finding(code, "Side effect detected", message, severity="critical", validator="side_effect", evidence=[token], blocking=True))
        return list({item.code + item.message: item for item in findings}.values())

    def _is_governed_patch_apply(self, data: dict[str, Any]) -> bool:
        if data.get("side_effect_type") != "patch_apply":
            return False
        return bool(
            data.get("apply_run_id")
            and data.get("status") == "completed"
            and data.get("approval_scope") == "patch_apply"
            and data.get("quality_status") == "passed"
            and data.get("post_apply_validation_passed") is True
            and data.get("unexpected_writes") in ([], None)
        )

    def _collect_operational_tokens(self, value: Any, *, parent_key: str = "") -> list[str]:
        if isinstance(value, dict):
            tokens: list[str] = []
            for key, item in value.items():
                key_text = str(key).lower()
                if key_text in ACTION_KEYS or key_text.endswith("_action") or key_text.endswith("_tool"):
                    tokens.extend(collect_strings(item))
                elif key_text in STRUCTURAL_KEYS:
                    tokens.extend(self._collect_operational_tokens(item, parent_key=key_text))
            return tokens
        if isinstance(value, list):
            tokens: list[str] = []
            for item in value:
                tokens.extend(self._collect_operational_tokens(item, parent_key=parent_key))
            return tokens
        if parent_key in ACTION_KEYS:
            return collect_strings(value)
        return []

    def status(self) -> dict[str, object]:
        return {"status": "ok", "service": "side_effect_validator", "write_enabled": False, "patch_enabled": False, "shell_enabled": False}
