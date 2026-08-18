from __future__ import annotations

from pathlib import Path

from aipinho.core.paths import PATHS
from aipinho.utils.yaml_loader import load_yaml_file


class SandboxPolicyService:
    def __init__(self, config_path: Path | None = None) -> None:
        self.config_path = config_path or PATHS.config_root / "security" / "sandbox_policy.yaml"
        self.config = load_yaml_file(self.config_path, critical=True, root=self.config_path.parent)

    @property
    def sandbox(self) -> dict[str, object]:
        value = self.config.get("sandbox", {})
        return value if isinstance(value, dict) else {}

    @property
    def enforcement(self) -> dict[str, object]:
        value = self.config.get("enforcement", {})
        return value if isinstance(value, dict) else {}

    def readonly_enabled(self) -> bool:
        modes = {str(item) for item in self.sandbox.get("read_capable_modes", ["read_only"]) or []}
        return bool(self.sandbox.get("enabled", False)) and str(self.sandbox.get("mode")) in modes

    def allows_workspace_bound_read(self) -> bool:
        return (
            self.readonly_enabled()
            and str(self.sandbox.get("root_mode", "workspace_bound")) == "workspace_bound"
            and bool(self.enforcement.get("require_workspace", True))
        )

    def status(self) -> dict[str, object]:
        return {
            "status": "ok" if self.readonly_enabled() else "degraded",
            "mode": self.sandbox.get("mode"),
            "allow_write": bool(self.sandbox.get("allow_write", False)),
            "allow_shell": bool(self.sandbox.get("allow_shell", False)),
            "allow_network": bool(self.sandbox.get("allow_network", False)),
            "require_workspace": bool(self.enforcement.get("require_workspace", True)),
            "workspace_bound_read": self.allows_workspace_bound_read(),
        }
