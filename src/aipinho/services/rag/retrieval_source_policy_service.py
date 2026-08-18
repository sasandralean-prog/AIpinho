from __future__ import annotations

from aipinho.schemas.rag.retrieval_request import RetrievalRequest, RetrievalSource, RetrievalSourcePolicy
from aipinho.services.rag.retrieval_source_registry import RetrievalSourceRegistry


class RetrievalSourcePolicyService:
    def __init__(self, registry: RetrievalSourceRegistry | None = None) -> None:
        self.registry = registry or RetrievalSourceRegistry()

    def validate_source(self, source_id: str, request: RetrievalRequest | None = None) -> RetrievalSourcePolicy:
        source = self.registry.get_source(source_id)
        reasons: list[str] = []
        warnings: list[str] = []
        if source is None:
            return RetrievalSourcePolicy(source_id=source_id, allowed=False, status="blocked", reasons=["unregistered_source"])
        if not source.enabled:
            reasons.append("disabled_source")
        if source_id in {"legacy_vectorstore", "web", "raw_logs"}:
            reasons.append(f"{source_id}_blocked")
        if not source.read_only:
            reasons.append("source_not_read_only")
        if source.explicit_request_required and request is not None and not request.explicit:
            reasons.append("explicit_request_required")
        if source.requires_workspace and request is not None and not self._has_workspace(request):
            reasons.append("workspace_required")
        return RetrievalSourcePolicy(source_id=source_id, allowed=not reasons, status="ok" if not reasons else "blocked", reasons=list(dict.fromkeys(reasons)), warnings=warnings)

    def validate_many(self, source_ids: list[str], request: RetrievalRequest) -> list[RetrievalSourcePolicy]:
        return [self.validate_source(source_id, request) for source_id in source_ids]

    def status(self) -> dict[str, object]:
        return {
            "status": "ok",
            "service": "retrieval_source_policy",
            "unregistered_sources_allowed": False,
            "legacy_vectorstore_enabled": False,
            "network_retrieval_enabled": False,
            "raw_log_retrieval_enabled": False,
        }

    def _has_workspace(self, request: RetrievalRequest) -> bool:
        if request.workspace or request.scope.workspace:
            return True
        metadata = request.metadata if isinstance(request.metadata, dict) else {}
        for key in ("workspace_context", "retrieval_context"):
            value = metadata.get(key)
            if not isinstance(value, dict):
                continue
            if value.get("workspace_path") or value.get("workspace_id"):
                return True
            scope = value.get("retrieval_scope")
            if isinstance(scope, dict) and (scope.get("workspace") or scope.get("workspace_id")):
                return True
        return False
