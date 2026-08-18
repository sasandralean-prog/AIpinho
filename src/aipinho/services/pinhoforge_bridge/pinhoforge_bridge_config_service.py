from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from aipinho.core.paths import PATHS
from aipinho.utils.yaml_loader import load_yaml_file


@dataclass(frozen=True)
class PinhoForgeBridgeRuntimeConfig:
    enabled: bool
    provider_id: str
    transport: str
    manifest_path: Path | None
    execution_enabled: bool
    allowed_operations: tuple[str, ...]
    blocked_operations: tuple[str, ...]
    require_local_auth: bool
    token_configured: bool


def _as_bool(value: str | None, default: bool) -> bool:
    if value is None or value.strip() == "":
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


class PinhoForgeBridgeConfigService:
    def __init__(self, config_path: Path | None = None, *, root: Path | None = None) -> None:
        self.config_path = config_path or PATHS.config_root / "providers" / "pinhoforge_bridge.yaml"
        self.root = root or PATHS.project_root

    def policy(self) -> dict[str, Any]:
        if not self.config_path.exists():
            return {}
        return load_yaml_file(self.config_path, root=self.root)

    def runtime(self) -> PinhoForgeBridgeRuntimeConfig:
        policy = self.policy()
        runtime = dict(policy.get("runtime") or {})
        manifest_value = os.getenv("PINHOFORGE_BRIDGE_MANIFEST_PATH") or runtime.get("manifest_path")
        manifest_path = Path(str(manifest_value)).expanduser() if manifest_value else None
        allowed = tuple(str(item) for item in (runtime.get("allowed_operations") or ["handshake", "health", "manifest", "readiness"]))
        blocked = tuple(str(item) for item in (runtime.get("blocked_operations") or ["execute"]))
        return PinhoForgeBridgeRuntimeConfig(
            enabled=_as_bool(os.getenv("PINHOFORGE_BRIDGE_ENABLED"), bool(runtime.get("enabled", True))),
            provider_id=str(runtime.get("provider_id", "pinhoforge_studio")),
            transport=os.getenv("PINHOFORGE_BRIDGE_TRANSPORT") or str(runtime.get("transport", "local_manifest_file")),
            manifest_path=manifest_path,
            execution_enabled=_as_bool(os.getenv("PINHOFORGE_BRIDGE_EXECUTION_ENABLED"), bool(runtime.get("execution_enabled", False))),
            allowed_operations=allowed,
            blocked_operations=blocked,
            require_local_auth=_as_bool(os.getenv("PINHOFORGE_BRIDGE_REQUIRE_LOCAL_AUTH"), bool(runtime.get("require_local_auth", True))),
            token_configured=bool(os.getenv("PINHOFORGE_BRIDGE_TOKEN")),
        )
