from __future__ import annotations
from pathlib import PureWindowsPath
from typing import Any
from aipinho.core.paths import PATHS
from aipinho.services.validation.validation_common import as_dict, collect_strings, finding
from aipinho.utils.yaml_loader import load_yaml_file

class WorkspaceAccessValidator:
    def __init__(self) -> None:
        self.policy = load_yaml_file(PATHS.config_root / "validation" / "workspace_access_validation_policy.yaml", critical=True, root=PATHS.config_root / "validation")
        self.forbidden = [str(item).lower().rstrip("\\/") for item in self.policy.get("forbidden_roots", []) or []]

    def validate(self, payload: Any) -> list:
        data = as_dict(payload)
        findings = []
        strings = collect_strings(data)
        lowered = [item.lower().replace("/", "\\") for item in strings]
        for root in self.forbidden:
            if any(root in item for item in lowered):
                findings.append(finding("forbidden_root_access", "Forbidden root access", f"Forbidden root referenced: {root}", severity="critical", validator="workspace_access", evidence=[root], blocking=True))
        if any("..\\" in item or "../" in item for item in strings):
            findings.append(finding("path_traversal_signal", "Path traversal signal", "A path traversal marker was found in validation metadata.", severity="error", validator="workspace_access", evidence=[".."], blocking=True))
        snapshot = data.get("workspace_snapshot") if isinstance(data, dict) else None
        if isinstance(snapshot, dict):
            if snapshot.get("blocked") is True:
                findings.append(finding("workspace_blocked", "Workspace blocked", str(snapshot.get("reason") or "workspace snapshot says blocked"), severity="error", validator="workspace_access", blocking=True))
            if snapshot.get("needs_clarification") is True:
                findings.append(finding("workspace_needs_clarification", "Workspace needs clarification", "Workspace snapshot requires clarification.", severity="warning", validator="workspace_access"))
        return findings

    def status(self) -> dict[str, object]:
        return {"status": "ok", "service": "workspace_access_validator"}
