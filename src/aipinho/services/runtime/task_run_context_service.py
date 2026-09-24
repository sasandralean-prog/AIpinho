from __future__ import annotations

from typing import Any

from aipinho.schemas.runtime.task_run import TaskRun
from aipinho.schemas.runtime.task_run_context import TaskRunContext
from aipinho.services.context.context_plan_runtime_service import ContextPlanRuntimeService


class TaskRunContextService:
    def __init__(
        self,
        *,
        context_plans: ContextPlanRuntimeService | None = None,
    ) -> None:
        self.context_plans = context_plans or ContextPlanRuntimeService()

    def build(self, run: TaskRun) -> TaskRunContext:
        runtime_context = (
            run.intent_map.get("runtime_context", {})
            if isinstance(run.intent_map, dict)
            else {}
        )
        outputs: dict[str, Any] = {}
        if isinstance(runtime_context, dict):
            for key in (
                "project_report",
                "file_context_bundle",
                "project_analysis_report",
            ):
                if key in runtime_context:
                    outputs[key] = runtime_context[key]

        if run.context_injection_plan_id:
            resolution = self.context_plans.resolve(
                run.context_injection_plan_id
            )
            outputs["context_plan_resolution"] = {
                "status": resolution.status,
                "source": resolution.source,
                "violations": list(resolution.violations),
                "warnings": list(resolution.warnings),
            }
            if resolution.plan:
                outputs["context_injection_plan"] = dict(resolution.plan)
            if resolution.bundle:
                outputs["context_bundle"] = dict(resolution.bundle)
            if resolution.evidence_context:
                outputs["evidence_context"] = list(
                    resolution.evidence_context
                )

        return TaskRunContext(
            run_id=run.run_id,
            workspace=run.workspace,
            outputs=outputs,
        )

    def status(self) -> dict[str, object]:
        return {
            "status": "ok",
            "service": "task_run_context",
            "raw_content_persisted": False,
            "governed_context_plan_enabled": True,
            "context_plan_runtime": self.context_plans.status(),
        }
