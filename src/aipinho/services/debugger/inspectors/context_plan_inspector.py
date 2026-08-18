from __future__ import annotations

from aipinho.services.debugger.inspectors._shared import BaseInspector, finding
from aipinho.services.rag.integration.context_injection_planner import ContextInjectionPlanner


class ContextPlanInspector(BaseInspector):
    target_type = "context_plan"

    def inspect(self, plan_id: str):
        plan = ContextInjectionPlanner().get_plan(plan_id)
        if plan is None:
            return self.missing(plan_id)
        data = plan.model_dump()
        findings = []
        if not data.get("citation_map", {}).get("valid") and data.get("context_items"):
            findings.append(finding("context_citation_map_invalid", "Context plan citation map is invalid"))
        if not data.get("safe_for_prompt_assembly"):
            findings.append(finding("context_not_safe_for_prompt", "Context plan is not safe for prompt assembly", "high"))
        return self.result(plan_id, {"plan": data}, findings, summary="Context plan inspected")
