from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from aipinho.core.paths import PATHS
from aipinho.repositories.tools.tool_registry_repository import ToolRegistryRepository
from aipinho.schemas.tools.contracts_v2 import (
    ToolAvailabilityStatus,
    ToolContract,
    ToolInvocationPreview,
    ToolPermissionEnvelope,
)
from aipinho.utils.yaml_loader import load_yaml_file

SECRET_KEY = re.compile(r"(?:token|password|secret|api[_-]?key|credential)", re.IGNORECASE)
SECRET_VALUE = (
    re.compile(r"Bearer\s+[A-Za-z0-9._~+/-]+", re.IGNORECASE),
    re.compile(r"sk-[A-Za-z0-9_-]{8,}"),
    re.compile(r"ghp_[A-Za-z0-9_]{8,}"),
)
DIRECT_DANGEROUS = {
    "shell.powershell",
    "patch.apply",
    "browser.in_app",
    "browser.chrome",
    "computer.use",
    "multi_tool.parallel",
}


class ToolResultSanitizer:
    def sanitize(self, value: Any) -> Any:
        if isinstance(value, dict):
            result: dict[str, Any] = {}
            for key, item in value.items():
                result[str(key)] = "[REDACTED_SECRET]" if SECRET_KEY.search(str(key)) and item else self.sanitize(item)
            return result
        if isinstance(value, list):
            return [self.sanitize(item) for item in value]
        if isinstance(value, str):
            sanitized = value
            for pattern in SECRET_VALUE:
                sanitized = pattern.sub("[REDACTED_SECRET]", sanitized)
            return sanitized
        return value


class ToolContractLoader:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or PATHS.config_root / "tools" / "tool_registry.yaml"

    def load(self) -> dict[str, ToolContract]:
        data = load_yaml_file(self.path, root=PATHS.project_root)
        raw = data.get("governed_tools", {})
        return {tool_id: ToolContract(tool_id=tool_id, **entry) for tool_id, entry in raw.items()}


class ToolContractValidator:
    def validate(self, payload: ToolContract | dict[str, Any]) -> dict[str, Any]:
        try:
            contract = payload if isinstance(payload, ToolContract) else ToolContract(**payload)
        except Exception as exc:
            return {"status": "rejected", "valid": False, "reasons": [str(exc)]}
        reasons: list[str] = []
        if not contract.provider:
            reasons.append("provider_missing")
        if "direct_execution" in contract.allowed_call_modes:
            reasons.append("direct_execution_forbidden")
        return {"status": "accepted" if not reasons else "rejected", "valid": not reasons, "reasons": reasons, "tool_id": contract.tool_id}


class GovernedToolRegistryService:
    def __init__(self, loader: ToolContractLoader | None = None) -> None:
        self.loader = loader or ToolContractLoader()
        self.repository = ToolRegistryRepository()
        self._tools: dict[str, ToolContract] | None = None

    @property
    def tools(self) -> dict[str, ToolContract]:
        if self._tools is None:
            self._tools = self.loader.load()
            self.repository.save_registry([item.model_dump() for item in self._tools.values()])
        return self._tools

    def list_tools(self) -> list[ToolContract]:
        return sorted(self.tools.values(), key=lambda item: item.tool_id)

    def get(self, tool_id: str) -> ToolContract | None:
        return self.tools.get(tool_id)

    def status(self) -> dict[str, Any]:
        tools = self.list_tools()
        return {
            "status": "ok" if tools else "degraded",
            "enabled": True,
            "tools_loaded": len(tools),
            "available_tools": len([tool for tool in tools if tool.default_enabled]),
            "real_execution_enabled": False,
            "preview_enabled": True,
            "unknown_tool_blocked": True,
            "direct_shell_blocked": True,
            "direct_patch_apply_blocked": True,
            "external_network_blocked_by_default": True,
        }


class ToolAvailabilityService:
    def __init__(self, registry: GovernedToolRegistryService | None = None) -> None:
        self.registry = registry or GovernedToolRegistryService()

    def status(self, tool_id: str) -> ToolAvailabilityStatus:
        tool = self.registry.get(tool_id)
        if tool is None:
            return ToolAvailabilityStatus(tool_id=tool_id, available=False, reason="unknown_tool")
        if not tool.default_enabled:
            return ToolAvailabilityStatus(tool_id=tool_id, available=False, reason="disabled_by_default")
        return ToolAvailabilityStatus(tool_id=tool_id, available=True, reason="contract_available_for_preview")


class ToolPermissionService:
    def __init__(self, registry: GovernedToolRegistryService | None = None) -> None:
        self.registry = registry or GovernedToolRegistryService()

    def preview(
        self,
        *,
        skill_id: str,
        requested_tools: list[str],
        contract_allowed_tools: list[str],
        contract_forbidden_tools: list[str],
        granted_capabilities: list[str],
        approval_id: str | None = None,
    ) -> ToolPermissionEnvelope:
        allowed: list[str] = []
        denied: list[str] = []
        reasons: dict[str, str] = {}
        approvals: list[str] = []
        granted = set(granted_capabilities)
        for tool_id in requested_tools:
            tool = self.registry.get(tool_id)
            reason: str | None = None
            if tool is None:
                reason = "unknown_tool"
            elif tool_id not in contract_allowed_tools:
                reason = "tool_not_declared_in_allowed_tools"
            elif tool_id in contract_forbidden_tools:
                reason = "tool_declared_forbidden"
            elif tool_id in DIRECT_DANGEROUS:
                reason = "direct_dangerous_tool_blocked"
            elif tool.external_network and not tool.default_enabled:
                reason = "external_network_blocked_by_default"
            elif not set(tool.capabilities).issubset(granted):
                reason = "missing_tool_capability"
            elif not tool.default_enabled:
                reason = "tool_disabled_by_default"
            if reason:
                denied.append(tool_id)
                reasons[tool_id] = reason
                continue
            allowed.append(tool_id)
            if tool and tool.requires_approval and not approval_id:
                approvals.append(tool_id)
        return ToolPermissionEnvelope(
            skill_id=skill_id,
            allowed_tools=allowed,
            denied_tools=denied,
            granted_capabilities=sorted(granted),
            approval_required_for=approvals,
            reasons=reasons,
            direct_execution_allowed=False,
        )


class ToolInvocationPreviewService:
    def __init__(self, registry: GovernedToolRegistryService | None = None) -> None:
        self.registry = registry or GovernedToolRegistryService()
        self.repository = ToolRegistryRepository()
        self.sanitizer = ToolResultSanitizer()

    def preview(
        self,
        *,
        tool_id: str,
        input_data: dict[str, Any],
        skill_id: str | None = None,
        call_mode: str = "preview_only",
        permission_envelope: ToolPermissionEnvelope | None = None,
    ) -> ToolInvocationPreview:
        tool = self.registry.get(tool_id)
        blocked: list[str] = []
        if tool is None:
            blocked.append("unknown_tool")
        else:
            if call_mode != "preview_only":
                blocked.append("direct_execution_forbidden")
            if tool_id in DIRECT_DANGEROUS:
                blocked.append("direct_dangerous_tool_blocked")
            if not tool.default_enabled:
                blocked.append("tool_disabled_by_default")
            if permission_envelope and tool_id not in permission_envelope.allowed_tools:
                blocked.append(permission_envelope.reasons.get(tool_id, "tool_permission_denied"))
        preview = ToolInvocationPreview(
            status="blocked" if blocked else "preview",
            tool_id=tool_id,
            skill_id=skill_id,
            call_mode="preview_only",
            sanitized_input=self.sanitizer.sanitize(input_data),
            blocked_reasons=list(dict.fromkeys(blocked)),
            approval_required=bool(tool and tool.requires_approval),
            executed=False,
        )
        self.repository.save_invocation_preview(preview.model_dump())
        return preview
