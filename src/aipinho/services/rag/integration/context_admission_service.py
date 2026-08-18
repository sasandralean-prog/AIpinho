from __future__ import annotations

from aipinho.schemas.rag.integration.contracts import (
    ContextAdmissionDecision,
    ContextAdmissionRequest,
    ContextInjectionItem,
    RetrievalContextSelection,
)
from aipinho.services.rag.integration.context_budget_coordinator import ContextBudgetCoordinator
from aipinho.services.rag.integration.context_citation_map_service import ContextCitationMapService
from aipinho.services.rag.integration.context_conflict_detector import ContextConflictDetector
from aipinho.services.rag.integration.context_freshness_service import ContextFreshnessService
from aipinho.services.rag.integration.context_sensitivity_gate import ContextSensitivityGate
from aipinho.services.rag.integration.context_usage_trace_service import ContextUsageTraceService
from aipinho.services.rag.integration.memory_context_selector import MemoryContextSelector
from aipinho.services.rag.integration.retrieval_context_selector import RetrievalContextSelector


class ContextAdmissionService:
    def __init__(
        self,
        retrieval_selector: RetrievalContextSelector | None = None,
        memory_selector: MemoryContextSelector | None = None,
        sensitivity: ContextSensitivityGate | None = None,
        freshness: ContextFreshnessService | None = None,
        conflicts: ContextConflictDetector | None = None,
        budget: ContextBudgetCoordinator | None = None,
        citation_map: ContextCitationMapService | None = None,
        trace: ContextUsageTraceService | None = None,
    ) -> None:
        self.retrieval_selector = retrieval_selector or RetrievalContextSelector()
        self.memory_selector = memory_selector or MemoryContextSelector()
        self.sensitivity = sensitivity or ContextSensitivityGate()
        self.freshness = freshness or ContextFreshnessService()
        self.conflicts = conflicts or ContextConflictDetector()
        self.budget = budget or ContextBudgetCoordinator()
        self.citation_map = citation_map or ContextCitationMapService()
        self.trace = trace or ContextUsageTraceService()

    def admit(self, request: ContextAdmissionRequest) -> ContextAdmissionDecision:
        traces = [self.trace.item("admission", "started", "context_admission_requested")]
        if not request.policy_decision.allowed:
            return ContextAdmissionDecision(
                status="blocked",
                usage_mode=request.usage_mode,
                blocked_reasons=["rag_memory_policy_not_allowed", *request.policy_decision.blocked_reasons],
                trace=traces if request.include_trace else [],
            )
        workspace = str(request.scope.get("workspace") or "") or None
        retrieval = (
            self.retrieval_selector.select(
                request.retrieval_result,
                request.retrieval_context_bundle,
                usage_mode=request.usage_mode,
            )
            if request.retrieval_result or request.retrieval_context_bundle
            else RetrievalContextSelection()
        )
        memory = self.memory_selector.select(
            request.memory_items,
            explicit=request.usage_mode == "explicit_user_request" and request.policy_decision.allow_curated_memory,
            workspace=workspace,
        ) if request.memory_items else None
        attachment = self._attachment_select(request.attachment_context_items) if request.attachment_context_items else RetrievalContextSelection()
        items = [*retrieval.items, *(memory.items if memory else []), *attachment.items]
        blocked_items = [*retrieval.blocked_items, *(memory.blocked_items if memory else []), *attachment.blocked_items]
        blocked_reasons = [*retrieval.blocked_reasons, *(memory.blocked_reasons if memory else []), *attachment.blocked_reasons]
        warnings = [*retrieval.warnings, *(memory.warnings if memory else []), *attachment.warnings]
        if request.retrieval_context_bundle and workspace:
            bundle_workspace = ((request.retrieval_context_bundle.get("scope") or {}).get("workspace"))
            if bundle_workspace and bundle_workspace != workspace:
                blocked_reasons.append("retrieval_scope_mismatch")
        safe_items = []
        for item in items:
            sensitivity = self.sensitivity.validate(item)
            if not sensitivity["valid"]:
                blocked_items.append({"context_item_id": item.context_item_id, "reason": sensitivity["blocked_reasons"]})
                blocked_reasons.extend(sensitivity["blocked_reasons"])
            else:
                safe_items.append(item)
        freshness = self.freshness.check(safe_items)
        blocked_reasons.extend(freshness.blocked_reasons)
        warnings.extend(freshness.warnings)
        conflicts = self.conflicts.detect(safe_items)
        if any(conflict.severity == "high" and not conflict.resolved for conflict in conflicts):
            blocked_reasons.append("unresolved_high_context_conflict")
        elif conflicts:
            warnings.append("context_conflict_detected")
        selected, budget_result = self.budget.apply(safe_items, request.budget)
        warnings.extend(budget_result.warnings)
        citation_map = self.citation_map.build(selected)
        if not citation_map.valid and selected:
            blocked_reasons.extend(citation_map.blocked_reasons or ["context_citation_map_invalid"])
        if not selected:
            blocked_reasons.append("no_admissible_context")
        critical = bool(blocked_reasons)
        if critical:
            status = "blocked"
        elif budget_result.status == "partial":
            status = "partial"
        elif warnings:
            status = "admitted_with_warnings"
        else:
            status = "admitted"
        traces.extend(
            [
                self.trace.item("selection", "ok" if items else "blocked", "context_items_normalized", {"items": len(items)}),
                self.trace.item("budget", budget_result.status, "shared_context_budget_applied", budget_result.model_dump()),
                self.trace.item("citation_map", "ok" if citation_map.valid else "blocked", "citation_map_built"),
            ]
        )
        return ContextAdmissionDecision(
            status=status,
            usage_mode=request.usage_mode,
            workspace=workspace,
            admitted_items=selected if not critical else [],
            blocked_items=blocked_items,
            warnings=list(dict.fromkeys(warnings)),
            blocked_reasons=list(dict.fromkeys(blocked_reasons)),
            budget_result=budget_result,
            conflicts=conflicts,
            freshness=freshness,
            citation_map=citation_map,
            safe_for_prompt_assembly=not critical and citation_map.valid and bool(selected),
            trace=traces if request.include_trace else [],
        )

    def _attachment_select(self, raw_items: list[dict]) -> RetrievalContextSelection:
        selection = RetrievalContextSelection()
        allowed_kinds = {"visual_evidence", "ocr_text_block", "vision_context_item", "ocr_context_item"}
        for raw in raw_items:
            try:
                item = ContextInjectionItem.model_validate(raw)
            except Exception as exc:
                selection.blocked_items.append({"reason": "invalid_attachment_context_item", "error": str(exc)})
                selection.blocked_reasons.append("invalid_attachment_context_item")
                continue
            if item.kind not in allowed_kinds:
                selection.blocked_items.append({"context_item_id": item.context_item_id, "reason": "unsupported_attachment_context_kind"})
                selection.blocked_reasons.append("unsupported_attachment_context_kind")
                continue
            if not item.citation_ids:
                selection.blocked_items.append({"context_item_id": item.context_item_id, "reason": "attachment_context_missing_citation"})
                selection.blocked_reasons.append("attachment_context_missing_citation")
                continue
            selection.items.append(item)
        return selection

    def status(self) -> dict[str, object]:
        return {"status": "ok", "service": "context_admission", "default": "deny", "fetches_sources": False}
