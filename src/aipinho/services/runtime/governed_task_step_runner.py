from __future__ import annotations

from typing import Any
from pathlib import Path

from aipinho.schemas.agents.contracts import AgentRunCreateRequest, AgentSessionCreateRequest
from aipinho.schemas.agents.tool_gateway import ToolInvocationCreateRequest, ToolInvocationResult
from aipinho.schemas.patching.patch_plan import PatchPlan
from aipinho.schemas.runtime.task_run import TaskRun
from aipinho.schemas.runtime.task_run_context import TaskRunContext
from aipinho.schemas.runtime.task_run_step import TaskRunStep
from aipinho.services.agents.agent_local_action_planner import AgentLocalActionPlanner
from aipinho.services.patching.model_assisted_patch_planner_service import ModelAssistedPatchPlannerService
from aipinho.services.patching.apply.hunk_apply_engine import HunkApplyEngine
from aipinho.services.patching.apply.patch_apply_hashing import sha256_file
from aipinho.services.patching.patch_plan_store import PatchPlanStore
from aipinho.services.runtime.project_generation_plan_executor import ProjectGenerationPlanExecutor
from aipinho.services.runtime.readonly_task_step_runner import ReadOnlyTaskStepRunner, TaskStepOutcome
from aipinho.services.runtime.task_no_change_evidence_service import TaskNoChangeEvidenceService
from aipinho.utils.safe_paths import resolve_within_root


class GovernedTaskStepRunner(ReadOnlyTaskStepRunner):
    """Executes governed runtime steps through existing policy/tool services."""

    def __init__(
        self,
        local_actions: AgentLocalActionPlanner | None = None,
        no_change_evidence: TaskNoChangeEvidenceService | None = None,
        model_patch_planner: ModelAssistedPatchPlannerService | None = None,
        project_generation_executor: ProjectGenerationPlanExecutor | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self.local_actions = local_actions or AgentLocalActionPlanner()
        self.no_change_evidence = no_change_evidence or TaskNoChangeEvidenceService()
        self.model_patch_planner = model_patch_planner or ModelAssistedPatchPlannerService()
        self.project_generation_executor = project_generation_executor or ProjectGenerationPlanExecutor()
        self.patch_plans = PatchPlanStore()
        self.hunk_engine = HunkApplyEngine()

    def _execute_filesystem_operation(self, run: TaskRun, context: TaskRunContext) -> TaskStepOutcome:
        prompt = self._execution_goal_for_run(run)
        if not prompt:
            return TaskStepOutcome(status="blocked", violations=["execution_goal_missing"])
        agent_run_id = self._agent_run_id(run, "filesystem_write")
        result = self.local_actions.run_explicit_create_file(
            agent_id="aipinho",
            run_id=agent_run_id,
            prompt=prompt,
            workspace_context=run.workspace,
            requested_capabilities=["create_file"],
            approval_id=run.approval_id,
            metadata_sanitized=self._metadata(run, context, "execute_filesystem_operation"),
        )
        if result is None:
            result = self.local_actions.run_explicit_modify_file(
                agent_id="aipinho",
                run_id=agent_run_id,
                prompt=prompt,
                workspace_context=run.workspace,
                requested_capabilities=["modify_file"],
                approval_id=run.approval_id,
                metadata_sanitized=self._metadata(run, context, "execute_filesystem_operation"),
            )
        if result is None:
            result = self.local_actions.run_inferred_ui_text_update(
                agent_id="aipinho",
                run_id=agent_run_id,
                prompt=prompt,
                workspace_context=run.workspace,
                requested_capabilities=["modify_file"],
                approval_id=run.approval_id,
                metadata_sanitized=self._metadata(run, context, "execute_filesystem_operation"),
            )
        if result is None:
            return TaskStepOutcome(
                status="blocked",
                violations=["filesystem_action_not_planned"],
                limitations=["no_targetable_filesystem_action"],
            )
        return self._tool_outcome(result, context, "filesystem_operation")

    def _execute_patch_pipeline(self, run: TaskRun, context: TaskRunContext) -> TaskStepOutcome:
        bound_plan = self._bound_patch_plan(run)
        if bound_plan is not None:
            return self._execute_bound_patch_plan(run, context, bound_plan)
        prompt = self._execution_goal_for_run(run)
        if not prompt:
            return TaskStepOutcome(status="blocked", violations=["execution_goal_missing"])
        agent_run_id = self._agent_run_id(run, "patch_pipeline")
        no_change = self.no_change_evidence.evaluate(prompt=prompt, workspace=run.workspace)
        if no_change is not None:
            return self._complete_without_patch(
                run=run,
                context=context,
                prompt=prompt,
                agent_run_id=agent_run_id,
                no_change=no_change,
            )
        result = self.local_actions.run_explicit_modify_file(
            agent_id="aipinho",
            run_id=agent_run_id,
            prompt=prompt,
            workspace_context=run.workspace,
            requested_capabilities=["modify_file"],
            approval_id=run.approval_id,
            metadata_sanitized=self._metadata(run, context, "execute_patch_pipeline"),
        )
        if result is None:
            result = self.local_actions.run_inferred_ui_text_update(
                agent_id="aipinho",
                run_id=agent_run_id,
                prompt=prompt,
                workspace_context=run.workspace,
                requested_capabilities=["modify_file"],
                approval_id=run.approval_id,
                metadata_sanitized=self._metadata(run, context, "execute_patch_pipeline"),
            )
        if result is None:
            planned = self.model_patch_planner.create_plan(
                workspace=run.workspace or "",
                objective=prompt,
                source_id=run.run_id,
                file_context_bundle=context.outputs.get("_file_context"),
                include_trace=True,
            )
            if planned.status == "ready" and planned.plan is not None:
                summary = {
                    "status": "patch_preview_created",
                    "plan_id": planned.plan.plan_id,
                    "plan_status": planned.plan.status,
                    "model_run_id": planned.model_run_id,
                    "model_id": planned.model_id,
                    "provider_id": planned.provider_id,
                    "quality_gate": planned.plan.quality_gate,
                    "apply_enabled": False,
                    "write_enabled": False,
                    "next_action": "request_patch_apply_approval",
                }
                context.outputs["_patch_result"] = summary
                context.outputs["_patch_plan"] = planned.plan.model_dump()
                return TaskStepOutcome(status="completed", summary=summary, warnings=list(planned.warnings))
            return TaskStepOutcome(
                status="blocked",
                violations=list(dict.fromkeys([*planned.blocked_reasons, "patch_plan_missing"])),
                limitations=["no_targetable_patch_action", *planned.warnings],
            )
        return self._tool_outcome(result, context, "patch_result")

    def _bound_patch_plan(self, run: TaskRun) -> PatchPlan | None:
        payload = self._current_step_patch_plan_input(run)
        if not isinstance(payload, dict):
            intent = run.intent_map if isinstance(run.intent_map, dict) else {}
            payload = intent.get("patch_plan")
        plan_id = None
        if isinstance(payload, dict):
            plan_id = payload.get("patch_plan_id") or payload.get("plan_id")
        if plan_id:
            stored = self.patch_plans.get_plan(str(plan_id))
            if stored is not None:
                return stored
        if isinstance(payload, dict) and payload.get("affected_files") and payload.get("hunks"):
            try:
                return PatchPlan.model_validate(
                    {
                        "plan_id": str(payload.get("plan_id") or payload.get("patch_plan_id")),
                        "status": str(payload.get("status") or "ready_for_review"),
                        "workspace": str(payload.get("workspace") or run.workspace or ""),
                        "source_type": str(payload.get("source_type") or "runtime_contract"),
                        "source_id": payload.get("source_id") or run.run_id,
                        "objective": str(payload.get("objective") or run.operation_type or ""),
                        "affected_files": payload.get("affected_files") or [],
                        "hunks": payload.get("hunks") or [],
                        "diff_proposal": payload.get("diff_proposal"),
                        "created_at": str(payload.get("created_at") or ""),
                        "updated_at": str(payload.get("updated_at") or ""),
                    }
                )
            except Exception:
                return None
        return None

    def _current_step_patch_plan_input(self, run: TaskRun) -> dict[str, Any] | None:
        execution_plan = run.plan.canonical_execution_plan if run.plan else None
        if execution_plan is None:
            return None
        for step in execution_plan.execution_steps:
            if run.current_step_id and step.step_id != run.current_step_id:
                continue
            if not run.current_step_id and step.action not in {"apply_patch", "patch_apply"}:
                continue
            payload = step.inputs.get("patch_plan")
            return payload if isinstance(payload, dict) else None
        return None

    def _execute_bound_patch_plan(
        self,
        run: TaskRun,
        context: TaskRunContext,
        plan: PatchPlan,
    ) -> TaskStepOutcome:
        if not run.approval_id:
            return TaskStepOutcome(status="blocked", violations=["approval_required"])
        if not plan.hunks or plan.diff_proposal is None or not plan.diff_proposal.diff.diff_text:
            return TaskStepOutcome(status="blocked", violations=["patch_plan_not_executable"])
        workspace_text = str(plan.workspace or run.workspace or "")
        if not workspace_text:
            return TaskStepOutcome(status="blocked", violations=["workspace_required"])
        workspace = Path(workspace_text)
        agent_run_id = self._agent_run_id(run, "patch_pipeline")
        results: list[dict[str, Any]] = []
        hunks_by_file: dict[str, list] = {}
        for hunk in plan.hunks:
            hunks_by_file.setdefault(self._path_key(hunk.file_path), []).append(hunk)
        for affected in plan.affected_files:
            rel = affected.relative_path or affected.path
            path_text = affected.normalized_path or str(workspace / rel)
            try:
                candidate = Path(path_text)
                if not candidate.is_absolute():
                    candidate = workspace / path_text
                path = resolve_within_root(candidate, workspace)
            except Exception:
                return TaskStepOutcome(status="blocked", violations=[f"target_outside_workspace:{rel}"])
            existed_before = path.exists()
            if affected.original_hash and existed_before and sha256_file(path) != affected.original_hash:
                return TaskStepOutcome(status="blocked", violations=[f"stale_snapshot:{rel}"])
            content = path.read_text(encoding="utf-8") if existed_before else ""
            updated = content
            file_hunks = hunks_by_file.get(self._path_key(rel), [])
            if not file_hunks:
                return TaskStepOutcome(status="blocked", violations=[f"hunks_missing_for_target:{rel}"])
            for hunk in file_hunks:
                updated, hunk_result = self.hunk_engine.apply(updated, hunk)
                if not hunk_result.applied:
                    return TaskStepOutcome(status="blocked", violations=[hunk_result.reason])
            tool_name = "modify_file" if existed_before else "create_file"
            tool_input: dict[str, Any] = {"content": updated}
            if existed_before:
                tool_input["expected_hash"] = sha256_file(path)
            else:
                tool_input["overwrite"] = False
            result = self.local_actions.tool_gateway.invoke(
                "aipinho",
                agent_run_id,
                tool_name,
                ToolInvocationCreateRequest(
                    operation_type=tool_name,
                    workspace_id=self.local_actions.infer_workspace_id(str(workspace)),
                    path_ref=str(path),
                    approval_id=run.approval_id,
                    input=tool_input,
                    metadata_sanitized={
                        **self._metadata(run, context, "execute_bound_patch_plan"),
                        "patch_plan_id": plan.plan_id,
                        "relative_path": rel,
                    },
                ),
            )
            summary = self._tool_summary(result)
            results.append(summary or {})
            if result.status != "succeeded":
                context.outputs["_patch_result"] = {
                    "status": result.status,
                    "plan_id": plan.plan_id,
                    "files": results,
                }
                return self._tool_outcome(result, context, "patch_result")
        summary = {
            "status": "patch_applied",
            "plan_id": plan.plan_id,
            "files": results,
            "diff_ref": plan.diff_proposal.proposal_id if plan.diff_proposal else None,
            "approval_id": run.approval_id,
        }
        context.outputs["_patch_result"] = summary
        context.outputs["_patch_plan"] = plan.model_dump(mode="json")
        return TaskStepOutcome(status="completed", summary=summary)

    def _path_key(self, path: str) -> str:
        return str(path or "").replace("\\", "/").strip("/")

    def _complete_without_patch(self, *, run, context, prompt, agent_run_id, no_change) -> TaskStepOutcome:
        report_result = self.local_actions.run_explicit_create_file(
            agent_id="aipinho",
            run_id=agent_run_id,
            prompt=prompt,
            workspace_context=run.workspace,
            requested_capabilities=["create_file"],
            content_hint=self._no_change_report(prompt, no_change),
            approval_id=run.approval_id,
            metadata_sanitized={
                **self._metadata(run, context, "execute_patch_pipeline"),
                "planner_mode": "no_changes_needed_report",
                "no_change_reason_code": no_change.reason_code,
                "no_change_report_path": no_change.report_path,
            },
        )
        if report_result is not None and report_result.status != "succeeded":
            return self._tool_outcome(report_result, context, "patch_result")
        summary = {
            "status": "no_changes_needed",
            "reason_code": no_change.reason_code,
            "verdict": no_change.verdict,
            "evidence_refs": no_change.evidence_refs,
            "source_report": no_change.report_path,
            "summary": no_change.summary,
            "report_write": self._tool_summary(report_result) if report_result is not None else None,
        }
        context.outputs["_patch_result"] = summary
        context.outputs["_patch_pipeline"] = summary
        return TaskStepOutcome(status="completed", summary=summary, warnings=["no_changes_needed"])

    def _execute_project_generation(self, run: TaskRun, context: TaskRunContext) -> TaskStepOutcome:
        planned = self.project_generation_executor.execute(run)
        if planned is not None:
            context.outputs["_project_generation"] = planned
            if planned.get("status") == "succeeded":
                return TaskStepOutcome(status="completed", summary=planned)
            reason = str(planned.get("reason_code") or "project_generation_plan_failed")
            return TaskStepOutcome(status="blocked", summary=planned, violations=[reason])
        prompt = self._execution_goal_for_run(run)
        if not prompt:
            return TaskStepOutcome(status="blocked", violations=["execution_goal_missing"])
        agent_run_id = self._agent_run_id(run, "project_generation")
        result = self.local_actions.run_explicit_create_file(
            agent_id="aipinho",
            run_id=agent_run_id,
            prompt=prompt,
            workspace_context=run.workspace,
            requested_capabilities=["create_file"],
            approval_id=run.approval_id,
            metadata_sanitized=self._metadata(run, context, "execute_project_generation"),
        )
        if result is None:
            return TaskStepOutcome(
                status="blocked",
                violations=["project_generation_plan_missing"],
                limitations=["no_targetable_project_generation_action"],
            )
        return self._tool_outcome(result, context, "project_generation")

    def _generate_artifact(self, run: TaskRun, context: TaskRunContext) -> TaskStepOutcome:
        return TaskStepOutcome(
            status="blocked",
            violations=["artifact_generation_plan_missing"],
            limitations=["artifact_content_not_planned"],
        )

    def _execute_governed_shell(self, run: TaskRun, context: TaskRunContext) -> TaskStepOutcome:
        plan = self._shell_plan(run)
        if not plan:
            return TaskStepOutcome(
                status="blocked",
                violations=["shell_command_plan_missing"],
                limitations=["no_governed_shell_command_planned"],
            )
        command = plan.get("command")
        argv = plan.get("argv")
        if not command and not argv:
            return TaskStepOutcome(
                status="blocked",
                violations=["shell_command_missing"],
                limitations=["shell_plan_without_command"],
            )
        agent_run_id = self._agent_run_id(run, "governed_shell")
        result = self.local_actions.tool_gateway.invoke(
            "aipinho",
            agent_run_id,
            "run_shell",
            ToolInvocationCreateRequest(
                operation_type="run_command",
                workspace_id=self.local_actions.infer_workspace_id(run.workspace) if run.workspace else None,
                approval_id=run.approval_id,
                input={
                    "command": command,
                    "argv": argv,
                    "cwd": plan.get("cwd") or run.workspace,
                    "timeout_seconds": int(plan.get("timeout_seconds") or 120),
                    "shell_category": str(plan.get("shell_category") or "unknown_shell"),
                },
                metadata_sanitized={
                    **self._metadata(run, context, "execute_governed_shell"),
                    "shell_plan_ref": plan.get("plan_ref"),
                    "shell_category": str(plan.get("shell_category") or "unknown_shell"),
                },
            ),
        )
        summary = self._tool_summary(result)
        context.outputs["_shell"] = summary
        if result.status == "succeeded":
            output = summary.get("output") if isinstance(summary, dict) else {}
            exit_code = output.get("exit_code") if isinstance(output, dict) else None
            expected_exit_code = int(plan.get("expected_exit_code") or 0)
            if exit_code != expected_exit_code:
                if isinstance(summary, dict):
                    summary["status"] = "failed"
                    summary["reason_code"] = "shell_exit_code_mismatch"
                    summary["expected_exit_code"] = expected_exit_code
                return TaskStepOutcome(status="failed", summary=summary, violations=["shell_exit_code_mismatch"])
            return TaskStepOutcome(status="completed", summary=summary)
        return self._tool_outcome(result, context, "shell")

    def _validate_filesystem_result(self, run: TaskRun, context: TaskRunContext) -> TaskStepOutcome:
        return self._validate_tool_result(context, "filesystem_operation")

    def _validate_patch_result(self, run: TaskRun, context: TaskRunContext) -> TaskStepOutcome:
        return self._validate_tool_result(context, "patch_result", validation_output_key="validation_result")

    def _validate_project_result(self, run: TaskRun, context: TaskRunContext) -> TaskStepOutcome:
        return self._validate_tool_result(context, "project_generation", validation_output_key="validation_result")

    def _validate_artifact(self, run: TaskRun, context: TaskRunContext) -> TaskStepOutcome:
        return self._validate_tool_result(context, "artifact")

    def _validate_shell_result(self, run: TaskRun, context: TaskRunContext) -> TaskStepOutcome:
        return self._validate_tool_result(context, "shell")

    def _shell_plan(self, run: TaskRun) -> dict[str, Any] | None:
        execution_plan = run.plan.canonical_execution_plan if run.plan else None
        if execution_plan is not None:
            for step in execution_plan.execution_steps:
                if run.current_step_id and step.step_id != run.current_step_id:
                    continue
                if not run.current_step_id and step.action not in {"run_command", "shell"}:
                    continue
                plan = step.inputs.get("shell_plan")
                if isinstance(plan, dict) and plan:
                    return plan
                if step.inputs:
                    return dict(step.inputs)
        intent = run.intent_map if isinstance(run.intent_map, dict) else {}
        plan = intent.get("shell_plan")
        if isinstance(plan, dict) and plan:
            return plan
        return None

    def _execution_goal_for_run(self, run: TaskRun) -> str:
        plan = run.plan.canonical_execution_plan if run.plan else None
        if plan is not None and plan.semantic_goal.strip():
            return plan.semantic_goal.strip()
        return ""

    def _agent_run_id(self, run: TaskRun, operation_type: str) -> str:
        session_id = run.session_id or f"task_runtime_{run.run_id}"
        kernel = self.local_actions.tool_gateway.kernel
        if kernel.get_session("aipinho", session_id) is None:
            session = kernel.create_session(
                "aipinho",
                AgentSessionCreateRequest(
                    title="Task runtime",
                    metadata_sanitized={"task_run_id": run.run_id, "source": "task_runtime"},
                ),
            )
            session_id = session.session_id
        agent_run = kernel.create_run(
            "aipinho",
            session_id,
            AgentRunCreateRequest(
                operation_type=operation_type,
                status="running",
                capabilities_requested=list(run.capabilities_required),
                metadata_sanitized={
                    "task_run_id": run.run_id,
                    "task_step_source": "governed_task_step_runner",
                },
            ),
        )
        return agent_run.run_id

    def _metadata(self, run: TaskRun, context: TaskRunContext, stage: str) -> dict[str, Any]:
        return {
            "task_run_id": run.run_id,
            "task_contract_type": run.contract_type,
            "task_operation_type": run.operation_type,
            "task_stage": stage,
            "context_outputs": sorted(context.outputs.keys()),
        }

    def _tool_outcome(self, result: ToolInvocationResult, context: TaskRunContext, output_key: str) -> TaskStepOutcome:
        summary = self._tool_summary(result)
        context.outputs[f"_{output_key}"] = summary
        if result.status == "succeeded":
            return TaskStepOutcome(status="completed", summary=summary)
        if result.status == "approval_required":
            return TaskStepOutcome(status="blocked", summary=summary, violations=["tool_approval_required"])
        if result.status == "blocked":
            reason = result.tool_invocation.block_reason_code or result.policy_decision.reason_code or "tool_blocked"
            return TaskStepOutcome(status="blocked", summary=summary, violations=[reason])
        return TaskStepOutcome(status="failed", summary=summary, violations=[result.tool_invocation.error_code or "tool_failed"])

    def _tool_summary(self, result: ToolInvocationResult | None) -> dict[str, Any] | None:
        if result is None:
            return None
        return {
            "status": result.status,
            "tool_invocation_id": result.tool_invocation.tool_invocation_id,
            "policy_decision": result.policy_decision.decision,
            "reason_code": result.policy_decision.reason_code,
            "output": result.output,
            "validation": result.validation_result.model_dump() if result.validation_result else None,
            "artifact_ids": [artifact.artifact_id for artifact in result.artifacts],
        }

    def _validate_tool_result(
        self,
        context: TaskRunContext,
        output_key: str,
        *,
        validation_output_key: str | None = None,
    ) -> TaskStepOutcome:
        result = context.outputs.get(f"_{output_key}")
        if not isinstance(result, dict):
            return TaskStepOutcome(status="blocked", violations=[f"{output_key}_result_missing"])
        if result.get("status") in {"succeeded", "no_changes_needed", "patch_preview_created", "patch_applied"}:
            validation = {
                "status": "passed",
                "validated_output": output_key,
                "reason_code": result.get("reason_code") or ("patch_preview_ready_for_review" if result.get("status") == "patch_preview_created" else "tool_result_succeeded"),
            }
            if validation_output_key:
                context.outputs[f"_{validation_output_key}"] = validation
            return TaskStepOutcome(status="completed", summary=validation)
        return TaskStepOutcome(status="blocked", summary={"validated_output": output_key}, violations=[f"{output_key}_not_succeeded"])

    def _no_change_report(self, prompt: str, no_change) -> str:
        return (
            "Relatorio de correcao governada\n\n"
            "Status\n"
            "no_changes_needed\n\n"
            "Motivo\n"
            f"{no_change.reason_code}\n\n"
            "Evidencia usada\n"
            f"- Relatorio: {no_change.report_path}\n"
            f"- Veredito: {no_change.verdict}\n\n"
            "Resumo\n"
            f"{no_change.summary}\n\n"
            "Resultado\n"
            "Nenhum patch foi aplicado porque a evidencia anterior indica que a capacidade solicitada ja esta satisfeita. "
            "O fluxo registrou essa conclusao como resultado governado em vez de inventar uma alteracao.\n\n"
            "Solicitacao original\n"
            f"{prompt.strip()}\n"
        )

    def status(self):
        base = super().status()
        base.update({"service": "governed_task_step_runner", "write_enabled": True, "patch_enabled": True, "shell_enabled": True})
        return base
