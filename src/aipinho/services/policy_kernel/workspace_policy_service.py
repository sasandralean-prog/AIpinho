from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from aipinho.core.paths import PATHS
from aipinho.schemas.policy.policy_trace import PolicyTraceItem
from aipinho.schemas.policy.policy_violation import PolicyViolation
from aipinho.services.policy_kernel.policy_trace_service import PolicyTraceService
from aipinho.utils.yaml_loader import load_yaml_file


@dataclass(frozen=True)
class WorkspacePolicyResult:
    status: str
    workspace_path: str | None
    blocked: bool
    needs_clarification: bool
    reason: str
    violations: list[PolicyViolation]
    trace: list[PolicyTraceItem]


class WorkspacePolicyService:
    def __init__(self, config_path: Path | None = None, trace_service: PolicyTraceService | None = None) -> None:
        self.config_path = config_path or PATHS.config_root / "workspaces" / "protected_workspaces.yaml"
        self.trace_service = trace_service or PolicyTraceService()
        self._config: dict[str, object] | None = None

    def load(self) -> "WorkspacePolicyService":
        self._config = load_yaml_file(self.config_path, critical=True, root=self.config_path.parent)
        return self

    @property
    def config(self) -> dict[str, object]:
        if self._config is None:
            self.load()
        return self._config or {}

    def _normalize_path(self, value: str) -> str:
        return os.path.normcase(str(Path(value).expanduser().resolve(strict=False)))

    def _is_under(self, path: str, root: str) -> bool:
        normalized_path = self._normalize_path(path)
        normalized_root = self._normalize_path(root)
        return normalized_path == normalized_root or normalized_path.startswith(normalized_root + os.sep)

    def evaluate(self, *, workspace_path: str | None, requires_workspace: bool) -> WorkspacePolicyResult:
        trace: list[PolicyTraceItem] = []
        if not workspace_path:
            if requires_workspace:
                trace.append(self.trace_service.create(
                    stage="workspace_policy",
                    rule="workspace_required",
                    decision="needs_clarification",
                    reason="workspace_missing_for_workspace_required_intent",
                    severity="warning",
                    source="request.workspace",
                ))
                return WorkspacePolicyResult("needs_clarification", None, False, True, "workspace_missing", [], trace)
            trace.append(self.trace_service.create(
                stage="workspace_policy",
                rule="workspace_optional",
                decision="allowed",
                reason="workspace_not_required",
                source="request.intent.requires_workspace",
            ))
            return WorkspacePolicyResult("allowed", None, False, False, "workspace_not_required", [], trace)

        for protected in self.config.get("protected_roots", []) or []:
            if not isinstance(protected, dict):
                continue
            protected_path = str(protected.get("path", ""))
            if protected_path and self._is_under(workspace_path, protected_path):
                if not bool(protected.get("block_task", True)):
                    trace.append(self.trace_service.create(
                        stage="workspace_policy",
                        rule="protected_root_configured_allowed",
                        decision="allowed",
                        reason=str(protected.get("reason", "protected_root_allowed_by_policy")),
                        severity="info",
                        source=str(self.config_path),
                        input={"workspace_path": workspace_path, "protected_root": protected_path},
                    ))
                    continue
                violation = PolicyViolation(
                    code="forbidden_root",
                    reason="workspace_path_matches_protected_root",
                    severity="critical",
                    source=str(self.config_path),
                )
                trace.append(self.trace_service.create(
                    stage="workspace_policy",
                    rule="forbidden_root",
                    decision="denied",
                    reason="workspace_path_matches_protected_root",
                    severity="critical",
                    source=str(self.config_path),
                    input={"workspace_path": workspace_path, "protected_root": protected_path},
                ))
                return WorkspacePolicyResult("denied", workspace_path, True, False, "forbidden_root", [violation], trace)

        trace.append(self.trace_service.create(
            stage="workspace_policy",
            rule="workspace_allowed",
            decision="allowed",
            reason="workspace_not_protected",
            source=str(self.config_path),
            input={"workspace_path": workspace_path},
        ))
        return WorkspacePolicyResult("allowed", workspace_path, False, False, "workspace_allowed", [], trace)

    def status(self) -> dict[str, object]:
        try:
            protected = self.config.get("protected_roots", []) or []
            return {"status": "ok", "protected_roots": len(protected)}
        except Exception as exc:
            return {"status": "degraded", "error": str(exc)}
