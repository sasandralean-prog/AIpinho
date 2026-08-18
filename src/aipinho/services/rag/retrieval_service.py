from __future__ import annotations

from aipinho.schemas.rag.retrieval_request import RetrievalAudit, RetrievalRequest, RetrievalResult
from aipinho.services.rag.retrieval_audit_service import RetrievalAuditService
from aipinho.services.rag.retrieval_budget_service import RetrievalBudgetService
from aipinho.services.rag.retrieval_context_builder import RetrievalContextBuilder
from aipinho.services.rag.retrieval_dedupe_service import RetrievalDedupeService
from aipinho.services.rag.retrieval_executor import RetrievalExecutor
from aipinho.services.rag.retrieval_query_service import RetrievalQueryService
from aipinho.services.rag.retrieval_ranker import RetrievalRanker
from aipinho.services.rag.retrieval_scope_service import RetrievalScopeService
from aipinho.services.rag.retrieval_sensitivity_filter import RetrievalSensitivityFilter
from aipinho.services.rag.retrieval_source_policy_service import RetrievalSourcePolicyService
from aipinho.services.rag.retrieval_source_registry import RetrievalSourceRegistry
from aipinho.services.rag.retrieval_status_service import RetrievalStatusService
from aipinho.services.rag.retrieval_trace_service import RetrievalTraceService


class RetrievalService:
    def __init__(
        self,
        registry: RetrievalSourceRegistry | None = None,
        source_policy: RetrievalSourcePolicyService | None = None,
        scope_service: RetrievalScopeService | None = None,
        query_service: RetrievalQueryService | None = None,
        executor: RetrievalExecutor | None = None,
        sensitivity: RetrievalSensitivityFilter | None = None,
        dedupe: RetrievalDedupeService | None = None,
        ranker: RetrievalRanker | None = None,
        budget: RetrievalBudgetService | None = None,
        context_builder: RetrievalContextBuilder | None = None,
        audit: RetrievalAuditService | None = None,
        trace_service: RetrievalTraceService | None = None,
    ) -> None:
        self.registry = registry or RetrievalSourceRegistry()
        self.source_policy = source_policy or RetrievalSourcePolicyService(self.registry)
        self.scope_service = scope_service or RetrievalScopeService()
        self.query_service = query_service or RetrievalQueryService()
        self.executor = executor or RetrievalExecutor(self.registry)
        self.sensitivity = sensitivity or RetrievalSensitivityFilter()
        self.dedupe = dedupe or RetrievalDedupeService()
        self.ranker = ranker or RetrievalRanker()
        self.budget = budget or RetrievalBudgetService()
        self.context_builder = context_builder or RetrievalContextBuilder()
        self.audit = audit or RetrievalAuditService()
        self.trace_service = trace_service or RetrievalTraceService()

    def retrieve(self, request: RetrievalRequest) -> RetrievalResult:
        request = self._request_with_canonical_context(request)
        source_ids = request.sources
        query = self.query_service.normalize(request.query, request.budget)
        trace = [self.trace_service.item("request", "ok", "retrieval_request_received", data={"sources": source_ids})]
        warnings: list[str] = []
        blocked: list[str] = []
        if not source_ids:
            blocked.append("retrieval_source_required")
        query_check = self.query_service.validate(query)
        if not query_check.valid:
            blocked.extend(query_check.blocked_reasons)
        scope_check = self.scope_service.validate(request)
        if not scope_check.valid:
            blocked.extend(scope_check.blocked_reasons)
        policies = self.source_policy.validate_many(source_ids, request)
        allowed_sources = [policy.source_id for policy in policies if policy.allowed]
        for policy in policies:
            if not policy.allowed:
                blocked.extend(policy.reasons)
                trace.append(self.trace_service.item("source_policy", "blocked", ",".join(policy.reasons), source_id=policy.source_id))
        if blocked:
            result = RetrievalResult(status="blocked", query=query, sources_requested=source_ids, blocked_reasons=list(dict.fromkeys(blocked)), trace=trace, warnings=warnings)
            result.audit = RetrievalAudit(retrieval_id=result.retrieval_id, status=result.status, sources=allowed_sources, warnings=result.warnings, trace_ref=f"{result.retrieval_id}/trace")
            self.audit.save_result(result)
            return result
        hits, execution_trace, exec_warnings = self.executor.execute(request, allowed_sources)
        trace.extend(execution_trace)
        warnings.extend(exec_warnings)
        hits = self.sensitivity.filter_hits(hits)
        hits = [hit for hit in hits if not hit.blocked]
        hits = self.dedupe.dedupe(hits)
        hits = self.ranker.rank(hits, query)
        hits, budget_warnings, budget_status = self.budget.apply(hits, request.budget)
        warnings.extend(budget_warnings)
        bundle = self.context_builder.build(request, hits, warnings=warnings)
        status = "blocked" if bundle.status == "blocked" else budget_status
        if not hits and status != "blocked":
            status = "no_results"
        result = RetrievalResult(
            status=status,
            query=query,
            sources_requested=source_ids,
            sources_used=allowed_sources,
            hits=hits,
            context_bundle=bundle,
            evidence_bundle=bundle.evidence_bundle,
            warnings=list(dict.fromkeys(warnings)),
            blocked_reasons=bundle.blocked_reasons,
            trace=trace if request.include_trace else [],
            vectorstore_used=False,
            embeddings_used=False,
            legacy_vectorstore_used=False,
            side_effects=False,
        )
        result.context_bundle.retrieval_id = result.retrieval_id
        result.audit = RetrievalAudit(retrieval_id=result.retrieval_id, status=result.status, sources=allowed_sources, warnings=result.warnings, trace_ref=f"{result.retrieval_id}/trace")
        self.audit.save_result(result)
        return result

    def _request_with_canonical_context(self, request: RetrievalRequest) -> RetrievalRequest:
        metadata = request.metadata if isinstance(request.metadata, dict) else {}
        workspace_context = metadata.get("workspace_context")
        retrieval_context = metadata.get("retrieval_context")
        workspace = request.workspace or request.scope.workspace
        workspace_id = None
        allowed_roots = []
        if isinstance(workspace_context, dict):
            workspace = workspace or workspace_context.get("workspace_path") or workspace_context.get("project_root")
            workspace_id = workspace_context.get("workspace_id")
            allowed_roots = list(workspace_context.get("allowed_roots") or [])
        if isinstance(retrieval_context, dict):
            scope = retrieval_context.get("retrieval_scope")
            if isinstance(scope, dict):
                workspace = workspace or scope.get("workspace")
                workspace_id = workspace_id or scope.get("workspace_id")
                allowed_roots = allowed_roots or list(scope.get("allowed_roots") or [])
            allowed_roots = allowed_roots or list(retrieval_context.get("allowed_roots") or [])
        if not workspace:
            return request
        scope = request.scope.model_copy(
            update={
                "workspace": request.scope.workspace or workspace,
                "project": request.scope.project or workspace_id,
            }
        )
        merged_metadata = dict(metadata)
        merged_metadata.setdefault(
            "canonical_retrieval",
            {
                "workspace": workspace,
                "workspace_id": workspace_id,
                "allowed_roots": allowed_roots,
                "source": "RetrievalService._request_with_canonical_context",
            },
        )
        return request.model_copy(update={"workspace": request.workspace or workspace, "scope": scope, "metadata": merged_metadata})

    def get_retrieval(self, retrieval_id: str):
        return self.audit.get_result(retrieval_id)

    def list_retrievals(self, limit: int = 100):
        return self.audit.list_results(limit=limit)

    def status(self) -> dict[str, object]:
        return RetrievalStatusService().status()
