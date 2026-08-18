from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from aipinho.core.paths import PATHS
from aipinho.schemas.tools.tool_execution import ToolExecutionRequest
from aipinho.schemas.tools.tool_execution_result import ToolExecutionResult
from aipinho.services.security.content_safety_service import ContentSafetyService
from aipinho.services.security.path_guard_service import PathGuardService
from aipinho.utils.yaml_loader import load_yaml_file


class FilesystemReadService:
    def __init__(self, path_guard: PathGuardService | None = None, content_safety: ContentSafetyService | None = None, policy_path: Path | None = None) -> None:
        self.path_guard = path_guard or PathGuardService()
        self.content_safety = content_safety or ContentSafetyService()
        self.policy_path = policy_path or PATHS.config_root / "policies" / "read_only_execution_policy.yaml"
        self.policy = load_yaml_file(self.policy_path, critical=True, root=self.policy_path.parent)

    @property
    def limits(self) -> dict[str, object]:
        value = self.policy.get("limits", {})
        return value if isinstance(value, dict) else {}

    def inspect_path(self, request: ToolExecutionRequest, *, execution_id: str | None = None, action: str = "inspect_path", capability: str = "read_workspace") -> ToolExecutionResult:
        decision = self.path_guard.validate_read_target(str(request.input.get("workspace") or ""), str(request.input.get("path") or ""))
        if not decision.allowed:
            return self._blocked(request, decision, execution_id=execution_id, action=action, capability=capability)
        target = Path(decision.target_path or "")
        return ToolExecutionResult(execution_id=execution_id or f"exec_{uuid4().hex}", tool_id=request.tool_id, status="executed_readonly", action=action, capability=capability, workspace=decision.workspace, target_path=decision.target_path, content=None, metadata=self._metadata(target), warnings=list(decision.warnings), trace=list(decision.trace), side_effects=False, safe_to_execute=True)

    def list_directory(self, request: ToolExecutionRequest, *, execution_id: str | None = None, action: str = "list_directory", capability: str = "read_workspace") -> ToolExecutionResult:
        decision = self.path_guard.validate_read_target(str(request.input.get("workspace") or ""), str(request.input.get("path") or ""))
        if not decision.allowed:
            return self._blocked(request, decision, execution_id=execution_id, action=action, capability=capability)
        target = Path(decision.target_path or "")
        if not target.exists():
            return self._invalid(request, "target_not_found", decision, execution_id=execution_id, action=action, capability=capability)
        if not target.is_dir():
            return self._invalid(request, "target_not_directory", decision, execution_id=execution_id, action=action, capability=capability)
        limit = int(request.input.get("limit") or self.limits.get("max_directory_entries", 500) or 500)
        max_limit = int(self.limits.get("max_directory_entries", 500) or 500)
        limit = max(0, min(limit, max_limit))
        entries = []
        warnings: list[str] = []
        for index, child in enumerate(sorted(target.iterdir(), key=lambda item: item.name.lower())):
            if index >= limit:
                warnings.append("directory_entries_truncated")
                break
            blocked_reasons = []
            if not bool(self.limits.get("allow_hidden_files", False)) and child.name.startswith("."):
                blocked_reasons.append("hidden_file")
            if self.path_guard.is_secret_path(child):
                blocked_reasons.append("secret_file")
            if child.is_file() and self.path_guard.is_blocked_extension(child):
                blocked_reasons.append("blocked_extension")
            entries.append({"name": child.name, "kind": "directory" if child.is_dir() else ("file" if child.is_file() else "other"), "size": child.stat().st_size if child.exists() and child.is_file() else None, "extension": child.suffix.lower() or None, "blocked": bool(blocked_reasons), "blocked_reasons": blocked_reasons})
        return ToolExecutionResult(execution_id=execution_id or f"exec_{uuid4().hex}", tool_id=request.tool_id, status="executed_readonly", action=action, capability=capability, workspace=decision.workspace, target_path=decision.target_path, content=None, metadata={**self._metadata(target), "entries": entries, "entries_returned": len(entries)}, warnings=list(dict.fromkeys([*decision.warnings, *warnings])), trace=list(decision.trace), side_effects=False, safe_to_execute=True)

    def read_file(self, request: ToolExecutionRequest, *, execution_id: str | None = None, action: str = "read_files", capability: str = "read_workspace") -> ToolExecutionResult:
        decision = self.path_guard.validate_read_target(str(request.input.get("workspace") or ""), str(request.input.get("path") or ""))
        if not decision.allowed:
            return self._blocked(request, decision, execution_id=execution_id, action=action, capability=capability)
        target = Path(decision.target_path or "")
        if not target.exists():
            return self._invalid(request, "target_not_found", decision, execution_id=execution_id, action=action, capability=capability)
        if not target.is_file():
            return self._invalid(request, "target_not_file", decision, execution_id=execution_id, action=action, capability=capability)
        max_file_bytes = int(request.input.get("max_bytes") or self.limits.get("max_file_bytes", 200000) or 200000)
        max_file_bytes = min(max_file_bytes, int(self.limits.get("max_file_bytes", 200000) or 200000))
        sample = target.read_bytes()[: max_file_bytes + 1]
        if self.content_safety.is_binary_sample(sample[:4096]):
            return self._blocked_with_reason(request, "binary_file", decision, execution_id=execution_id, action=action, capability=capability)
        truncated = len(sample) > max_file_bytes
        data = sample[:max_file_bytes]
        text, content_warnings = self.content_safety.decode_text(data)
        safety = self.policy.get("safety", {}) if isinstance(self.policy.get("safety", {}), dict) else {}
        preview_limit = int(safety.get("include_content_preview_limit", 20000) or 20000)
        if request.include_content and len(text) > preview_limit:
            text = text[:preview_limit]
            truncated = True
        content = text if request.include_content else None
        metadata = self._metadata(target)
        metadata.update({"bytes_read": len(data), "is_binary": False, "extension": target.suffix.lower()})
        return ToolExecutionResult(execution_id=execution_id or f"exec_{uuid4().hex}", tool_id=request.tool_id, status="executed_readonly", action=action, capability=capability, workspace=decision.workspace, target_path=decision.target_path, content=content, content_truncated=truncated, metadata=metadata, warnings=list(dict.fromkeys([*decision.warnings, *content_warnings, *( ["content_truncated"] if truncated else [] )])), trace=list(decision.trace), side_effects=False, safe_to_execute=True)

    def _metadata(self, target: Path) -> dict[str, object]:
        exists = target.exists()
        kind = "missing"
        if exists and target.is_file():
            kind = "file"
        elif exists and target.is_dir():
            kind = "directory"
        elif exists:
            kind = "other"
        return {"exists": exists, "path_kind": kind, "size": target.stat().st_size if exists and target.is_file() else None, "extension": target.suffix.lower() or None}

    def _blocked(self, request: ToolExecutionRequest, decision, *, execution_id: str | None, action: str, capability: str) -> ToolExecutionResult:
        return ToolExecutionResult(execution_id=execution_id or f"exec_{uuid4().hex}", tool_id=request.tool_id, status="blocked", action=action, capability=capability, workspace=decision.workspace, target_path=decision.target_path, violations=list(decision.violations), warnings=list(decision.warnings), trace=list(decision.trace), side_effects=False, safe_to_execute=False)

    def _blocked_with_reason(self, request: ToolExecutionRequest, reason: str, decision, *, execution_id: str | None, action: str, capability: str) -> ToolExecutionResult:
        result = self._blocked(request, decision, execution_id=execution_id, action=action, capability=capability)
        result.violations = list(dict.fromkeys([*result.violations, reason]))
        return result

    def _invalid(self, request: ToolExecutionRequest, reason: str, decision, *, execution_id: str | None, action: str, capability: str) -> ToolExecutionResult:
        return ToolExecutionResult(execution_id=execution_id or f"exec_{uuid4().hex}", tool_id=request.tool_id, status="invalid", action=action, capability=capability, workspace=decision.workspace, target_path=decision.target_path, violations=[reason], warnings=list(decision.warnings), trace=list(decision.trace), side_effects=False, safe_to_execute=False)

    def status(self) -> dict[str, object]:
        return {"status": "ok", "service": "filesystem_read", "max_file_bytes": self.limits.get("max_file_bytes")}
