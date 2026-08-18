from __future__ import annotations

from aipinho.schemas.rag.integration.contracts import RAGMemoryPolicyDecision, RAGMemoryPolicyRequest
from aipinho.services.memory.memory_read_policy_service import MemoryReadPolicyService
from aipinho.services.rag.integration.config import integration_config
from aipinho.services.rag.integration.context_usage_trace_service import ContextUsageTraceService
from aipinho.services.rag.retrieval_source_registry import RetrievalSourceRegistry


class RAGMemoryPolicyService:
    def __init__(
        self,
        config: dict | None = None,
        registry: RetrievalSourceRegistry | None = None,
        memory_policy: MemoryReadPolicyService | None = None,
        trace: ContextUsageTraceService | None = None,
    ) -> None:
        self.config = config or integration_config("rag_memory_policy.yaml")
        self.registry = registry or RetrievalSourceRegistry()
        self.memory_policy = memory_policy or MemoryReadPolicyService()
        self.trace = trace or ContextUsageTraceService()

    def decide(self, request: RAGMemoryPolicyRequest) -> RAGMemoryPolicyDecision:
        mode_config = (self.config.get("usage_modes") or {}).get(request.usage_mode, {})
        traces = [self.trace.item("usage_mode", "checked", request.usage_mode)]
        warnings: list[str] = []
        blocked_reasons: list[str] = []
        allowed_sources: list[str] = []
        blocked_sources: list[str] = []
        if not mode_config or not bool(mode_config.get("enabled", False)):
            blocked_reasons.append(f"usage_mode_blocked:{request.usage_mode}")
        if not request.requested_sources:
            blocked_reasons.append("requested_sources_required")
        mode_allows_retrieval = bool(mode_config.get("allow_retrieval", False)) and request.allow_retrieval
        mode_allows_memory = bool(mode_config.get("allow_curated_memory", False)) and request.allow_curated_memory
        for source_id in request.requested_sources:
            source = self.registry.get_source(source_id)
            reasons: list[str] = []
            if source is None:
                reasons.append("unregistered_source")
            elif not source.enabled or not source.read_only:
                reasons.append("source_blocked")
            elif source_id == "curated_memory":
                if not mode_allows_memory:
                    reasons.append("curated_memory_not_allowed")
                if request.usage_mode != "explicit_user_request":
                    reasons.append("curated_memory_explicit_required")
                if not self.memory_policy.explicit_read_allowed():
                    reasons.append("memory_read_policy_blocked")
            elif not mode_allows_retrieval:
                reasons.append("retrieval_not_allowed")
            if source and source.requires_workspace and not request.workspace:
                reasons.append("workspace_required")
            if reasons:
                blocked_sources.append(source_id)
                blocked_reasons.extend(f"{source_id}:{reason}" for reason in reasons)
                traces.append(self.trace.item("source_policy", "blocked", ",".join(reasons), {"source_id": source_id}))
            else:
                allowed_sources.append(source_id)
                traces.append(self.trace.item("source_policy", "allowed", "registered_read_only_source", {"source_id": source_id}))
        allowed = bool(allowed_sources) and not blocked_reasons
        status = "allowed" if allowed else "blocked"
        return RAGMemoryPolicyDecision(
            allowed=allowed,
            status=status,
            usage_mode=request.usage_mode,
            allowed_sources=allowed_sources,
            blocked_sources=list(dict.fromkeys(blocked_sources)),
            allow_retrieval=mode_allows_retrieval and any(item != "curated_memory" for item in allowed_sources),
            allow_curated_memory=mode_allows_memory and "curated_memory" in allowed_sources,
            warnings=list(dict.fromkeys(warnings)),
            blocked_reasons=list(dict.fromkeys(blocked_reasons)),
            trace=traces if request.include_trace else [],
        )

    def status(self) -> dict[str, object]:
        return {
            "status": "ok",
            "service": "rag_memory_policy",
            "enabled": True,
            "automatic_chat": False,
            "automatic_prompt_assembly": False,
            "curated_memory_explicit_required": True,
        }
