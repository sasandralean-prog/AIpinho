from __future__ import annotations

from pathlib import Path

from aipinho.core.paths import PATHS
from aipinho.schemas.rag.retrieval_request import RetrievalRequest, RetrievalValidation
from aipinho.utils.yaml_loader import load_yaml_file


class RetrievalScopeService:
    def __init__(self, config: dict | None = None) -> None:
        self.config = config or load_yaml_file(PATHS.config_root / "rag" / "retrieval_scope_policy.yaml", critical=True, root=PATHS.config_root / "rag")

    def validate(self, request: RetrievalRequest) -> RetrievalValidation:
        reasons: list[str] = []
        warnings: list[str] = []
        canonical = self._canonical_context(request)
        if not request.scope or not request.scope.scope_type:
            reasons.append("scope_required")
        workspace = request.workspace or request.scope.workspace or canonical.get("workspace_path") or canonical.get("workspace")
        if any(source in request.sources for source in {"project_files"}) and not workspace:
            reasons.append("workspace_required")
        if any(source in request.sources for source in {"project_files"}) and canonical and not canonical.get("workspace_id"):
            reasons.append("workspace_context_missing_workspace_id")
        if workspace:
            workspace_path = Path(workspace)
            workspace_text = str(workspace_path)
            for forbidden in self.config.get("workspace", {}).get("forbidden_roots", []) or []:
                if workspace_text.lower().startswith(str(forbidden).lower()):
                    reasons.append("forbidden_root")
            allowed_roots = [str(root).lower() for root in canonical.get("allowed_roots", []) or []]
            if not allowed_roots:
                allowed_roots = [str(root).lower() for root in self.config.get("workspace", {}).get("allowed_roots", []) or []]
            if allowed_roots and not any(workspace_text.lower().startswith(root) for root in allowed_roots):
                reasons.append("outside_allowed_retrieval_workspace")
        if "curated_memory" in request.sources and not request.explicit:
            reasons.append("explicit_memory_scope_required")
        return RetrievalValidation(valid=not reasons, status="ok" if not reasons else "blocked", warnings=warnings, blocked_reasons=list(dict.fromkeys(reasons)))

    def _canonical_context(self, request: RetrievalRequest) -> dict:
        metadata = request.metadata if isinstance(request.metadata, dict) else {}
        retrieval = metadata.get("retrieval_context")
        workspace = metadata.get("workspace_context")
        payload = retrieval if isinstance(retrieval, dict) else {}
        if isinstance(workspace, dict):
            payload = {**workspace, **payload}
        scope = payload.get("retrieval_scope")
        if isinstance(scope, dict):
            payload.setdefault("workspace", scope.get("workspace"))
            payload.setdefault("workspace_path", scope.get("workspace"))
            payload.setdefault("workspace_id", scope.get("workspace_id"))
            payload.setdefault("allowed_roots", scope.get("allowed_roots"))
        return payload

    def status(self) -> dict[str, object]:
        return {"status": "ok", "service": "retrieval_scope", "require_scope": True, "allowed_roots": self.config.get("workspace", {}).get("allowed_roots", [])}
