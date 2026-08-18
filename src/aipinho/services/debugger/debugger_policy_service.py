from __future__ import annotations

from aipinho.core.paths import PATHS
from aipinho.utils.yaml_loader import load_yaml_file


class DebuggerPolicyService:
    def __init__(self) -> None:
        self.path = PATHS.config_root / "debugger" / "debugger_v2_policy.yaml"
        self.config = load_yaml_file(self.path, critical=True, root=self.path.parent)

    def status(self) -> dict[str, object]:
        read_only = self.config.get("read_only", {}) if isinstance(self.config.get("read_only", {}), dict) else {}
        debugger = self.config.get("debugger", {}) if isinstance(self.config.get("debugger", {}), dict) else {}
        return {
            "status": "ok",
            "enabled": bool(debugger.get("enabled", True)),
            "mode": str(debugger.get("mode", "read_only_observability")),
            "sanitization_enabled": bool(debugger.get("require_sanitization", True)),
            "raw_prompt_visible_by_default": False,
            "raw_output_visible_by_default": False,
            "workspace_write_enabled": bool(read_only.get("workspace_write", False)),
            "patch_apply_enabled": bool(read_only.get("patch_apply", False)),
            "shell_enabled": bool(read_only.get("shell", False)),
            "git_enabled": bool(read_only.get("git", False)),
            "memory_mutation_enabled": bool(read_only.get("memory_mutation", False)),
            "rag_ingestion_execute_enabled": bool(read_only.get("rag_ingestion_execute", False)),
            "approval_mutation_enabled": bool(read_only.get("approval_mutation", False)),
        }
