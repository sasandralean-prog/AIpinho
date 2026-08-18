from __future__ import annotations
from typing import Any
from aipinho.schemas.runtime.task_run import TaskRun
from aipinho.schemas.runtime.task_run_context import TaskRunContext
from aipinho.services.rag.integration.context_injection_planner import ContextInjectionPlanner

class TaskRunContextService:
    def build(self, run: TaskRun) -> TaskRunContext:
        runtime_context = run.intent_map.get("runtime_context", {}) if isinstance(run.intent_map, dict) else {}
        outputs: dict[str, Any] = {}
        if isinstance(runtime_context, dict):
            for key in ("project_report", "file_context_bundle", "project_analysis_report"):
                if key in runtime_context: outputs[key] = runtime_context[key]
        if run.context_injection_plan_id:
            plan = ContextInjectionPlanner().get_plan(run.context_injection_plan_id)
            if plan is not None:
                outputs["context_injection_plan"] = plan.model_dump()
        return TaskRunContext(run_id=run.run_id, workspace=run.workspace, outputs=outputs)

    def status(self) -> dict[str, object]:
        return {"status": "ok", "service": "task_run_context", "raw_content_persisted": False, "governed_context_plan_enabled": True}
