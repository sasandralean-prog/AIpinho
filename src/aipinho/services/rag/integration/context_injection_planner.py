from __future__ import annotations

from aipinho.schemas.rag.integration.contracts import ContextAdmissionDecision, ContextInjectionPlan
from aipinho.services.rag.integration.context_citation_map_service import ContextCitationMapService
from aipinho.services.rag.integration.context_usage_audit_service import ContextUsageAuditService
from aipinho.services.rag.integration.context_usage_trace_service import ContextUsageTraceService


class ContextInjectionPlanner:
    def __init__(
        self,
        audit: ContextUsageAuditService | None = None,
        citation_map: ContextCitationMapService | None = None,
        trace: ContextUsageTraceService | None = None,
    ) -> None:
        self.audit = audit or ContextUsageAuditService()
        self.citation_map = citation_map or ContextCitationMapService()
        self.trace = trace or ContextUsageTraceService()

    def plan(self, admission: ContextAdmissionDecision, *, policy_decision_id: str | None = None) -> ContextInjectionPlan:
        traces = list(admission.trace)
        if not admission.safe_for_prompt_assembly:
            plan = ContextInjectionPlan(
                admission_id=admission.admission_id,
                policy_decision_id=policy_decision_id,
                status="blocked",
                usage_mode=admission.usage_mode,
                workspace=admission.workspace,
                warnings=admission.warnings,
                blocked_reasons=admission.blocked_reasons or ["context_admission_not_safe"],
                limitations=["No context may be injected from a blocked admission."],
                trace=[*traces, self.trace.item("plan", "blocked", "admission_not_safe")],
            )
            return self.audit.save_plan(plan)
        citation_map = self.citation_map.validate(admission.citation_map, admission.admitted_items)
        if not citation_map.valid:
            plan = ContextInjectionPlan(
                admission_id=admission.admission_id,
                policy_decision_id=policy_decision_id,
                status="blocked",
                usage_mode=admission.usage_mode,
                workspace=admission.workspace,
                blocked_reasons=citation_map.blocked_reasons,
                trace=[*traces, self.trace.item("plan", "blocked", "citation_map_invalid")],
            )
            return self.audit.save_plan(plan)
        sources: dict[tuple[str, str], int] = {}
        for item in admission.admitted_items:
            key = (item.source_id, item.source_type)
            sources[key] = sources.get(key, 0) + 1
        status = "partial" if admission.status == "partial" else "ready"
        plan = ContextInjectionPlan(
            admission_id=admission.admission_id,
            policy_decision_id=policy_decision_id,
            status=status,
            usage_mode=admission.usage_mode,
            workspace=admission.workspace,
            context_items=admission.admitted_items,
            citation_map=citation_map,
            source_summary=[{"source_id": key[0], "source_type": key[1], "items": count} for key, count in sorted(sources.items())],
            budget_summary=admission.budget_result,
            limitations=["Context is read-only and does not grant execution authority."],
            warnings=admission.warnings,
            safe_for_prompt_assembly=True,
            trace=[*traces, self.trace.item("plan", "ready", "context_injection_plan_created", {"items": len(admission.admitted_items)})],
        )
        return self.audit.save_plan(plan)

    def get_plan(self, plan_id: str) -> ContextInjectionPlan | None:
        return self.audit.get_plan(plan_id)

    def list_plans(self, limit: int = 100) -> list[ContextInjectionPlan]:
        return self.audit.list_plans(limit=limit)

    def status(self) -> dict[str, object]:
        return {"status": "ok", "service": "context_injection_planner", "only_prompt_payload": True}
