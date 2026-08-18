from __future__ import annotations

from threading import RLock
from typing import Any
from uuid import uuid4

from aipinho.core.paths import PATHS
from aipinho.schemas.common.actor import Actor
from aipinho.schemas.runtime.task_cancellation import TaskCancellationRequest
from aipinho.schemas.runtime.task_run import TaskRun
from aipinho.schemas.runtime.task_queue import TaskQueueReconciliationResult
from aipinho.schemas.runtime.task_run_request import TaskRunRequest
from aipinho.schemas.runtime.task_runtime_status import TaskRuntimeStatus
from aipinho.services.approvals.approval_service import ApprovalService
from aipinho.services.orchestration.task_contract_draft_service import TaskContractDraftService
from aipinho.services.orchestration.task_preview_service import TaskPreviewService
from aipinho.services.policy_kernel.workspace_policy_service import WorkspacePolicyService
from aipinho.services.rag.integration.context_injection_planner import ContextInjectionPlanner
from aipinho.services.rag.integration.context_usage_validator import ContextUsageValidator
from aipinho.services.runtime.supervised_execution_loop import SupervisedExecutionLoop
from aipinho.services.runtime.task_queue_service import TaskQueueService
from aipinho.services.runtime.task_run_audit_service import TaskRunAuditService
from aipinho.services.runtime.task_bootstrap_runtime_service import TaskBootstrapRuntimeService
from aipinho.services.runtime.runtime_timeline_service import RuntimeTimelineService
from aipinho.services.runtime.workflow_runtime_service import WorkflowRuntimeService
from aipinho.services.runtime.runtime_truth_engine import RuntimeTruthEngine
from aipinho.services.runtime.canonical_operation_state_service import CanonicalOperationStateService
from aipinho.services.runtime.workspace_context_service import ExecutionContextService, RetrievalContextService, WorkspaceContextService
from aipinho.services.runtime.task_run_chat_result_publisher_service import (
    TaskRunChatResultPublisherService,
)
from aipinho.services.runtime.task_run_cancellation_service import TaskRunCancellationService
from aipinho.services.runtime.task_run_event_service import TaskRunEventService
from aipinho.services.runtime.task_run_guard import TaskRunGuard
from aipinho.services.runtime.task_run_lifecycle_service import TaskRunLifecycleService
from aipinho.services.runtime.task_run_planner import TaskRunPlanner
from aipinho.services.runtime.task_run_store import TaskRunStore
from aipinho.services.runtime.task_run_trace_service import TaskRunTraceService
from aipinho.services.runtime.task_block_cause_service import TaskBlockCauseService
from aipinho.services.runtime.task_run_executor import TaskRunExecutor
from aipinho.services.runtime.governed_task_step_runner import GovernedTaskStepRunner
from aipinho.services.runtime.execution_graph_service import ExecutionGraphService
from aipinho.services.runtime.intelligent_planner_service import IntelligentPlannerService
from aipinho.services.runtime.evidence_engine_service import EvidenceEngineService
from aipinho.services.runtime.continuous_runtime_service import ContinuousRuntimeService
from aipinho.services.runtime.engineering_autopilot_service import EngineeringAutopilotService
from aipinho.services.runtime.tool_governance_service import ToolGovernanceService
from aipinho.services.runtime.execution_plan_promotion_service import ExecutionPlanPromotionService
from aipinho.services.memory.operational_memory_service import OperationalMemoryService
from aipinho.services.runtime.project_generation_plan_executor import ProjectGenerationPlanExecutor
from aipinho.utils.yaml_loader import inspect_yaml_file, load_yaml_file
from aipinho.schemas.runtime.task_bootstrap import TaskBootstrapRequest


class TaskRuntimeService:
    CONFIGS = [
        "task_runtime_policy.yaml",
        "task_run_lifecycle_policy.yaml",
        "task_run_store_policy.yaml",
        "task_run_event_policy.yaml",
        "supervised_execution_policy.yaml",
        "governed_task_steps.yaml",
        "task_runtime_limits.yaml",
        "task_cancellation_policy.yaml",
        "task_result_policy.yaml",
        "task_completion_policy.yaml",
        "task_queue_policy.yaml",
        "planning_policy.yaml",
        "planning_constraints.yaml",
        "planning_cost_policy.yaml",
        "planning_parallel_policy.yaml",
        "planning_review_policy.yaml",
    ]
    _queue_process_lock = RLock()

    def __init__(
        self,
        store=None,
        drafts=None,
        previews=None,
        approvals=None,
        result_publisher=None,
        operational_memory=None,
        engineering_autopilot=None,
    ):
        self.store = store or TaskRunStore()
        self.drafts = drafts or TaskContractDraftService()
        self.previews = previews or TaskPreviewService()
        self.approvals = approvals or ApprovalService()
        self.policy = load_yaml_file(
            PATHS.config_root / "runtime" / "task_runtime_policy.yaml",
            critical=True,
            root=PATHS.config_root / "runtime",
        )
        self.planner = TaskRunPlanner()
        self.lifecycle = TaskRunLifecycleService()
        self.events = TaskRunEventService(self.store)
        self.trace = TaskRunTraceService()
        self.block_causes = TaskBlockCauseService()
        self.guard = TaskRunGuard(
            approvals=self.approvals,
            lifecycle=self.lifecycle,
        )
        self.audit = TaskRunAuditService(self.store)
        self.context_planner = ContextInjectionPlanner()
        self.context_validator = ContextUsageValidator()
        draft_store = getattr(self.drafts, "store", None)
        runner = GovernedTaskStepRunner(
            project_generation_executor=ProjectGenerationPlanExecutor(
                draft_store=draft_store,
            ),
        )
        self.loop = SupervisedExecutionLoop(
            store=self.store,
            lifecycle=self.lifecycle,
            guard=self.guard,
            events=self.events,
            audit=self.audit,
            executor=TaskRunExecutor(runner=runner),
        )
        self.cancellation = TaskRunCancellationService(
            self.store,
            self.lifecycle,
            self.events,
        )
        self.queue = TaskQueueService(
            store=self.store,
            lifecycle=self.lifecycle,
            cancellation=self.cancellation,
            approvals=self.approvals,
        )
        self.result_publisher = (
            result_publisher or TaskRunChatResultPublisherService()
        )
        self.execution_graphs = ExecutionGraphService()
        self.intelligent_planner = IntelligentPlannerService()
        self.operational_memory = operational_memory or OperationalMemoryService()
        self.evidence_engine = EvidenceEngineService()
        self.continuous_runtime = ContinuousRuntimeService(evidence=self.evidence_engine)
        self.engineering_autopilot = engineering_autopilot or EngineeringAutopilotService()
        self.tool_governance = ToolGovernanceService()
        self.bootstrap = TaskBootstrapRuntimeService(store=self.store)
        self.timeline = RuntimeTimelineService(store=self.store)
        self.workflows = WorkflowRuntimeService()
        self.truth = RuntimeTruthEngine()
        self.canonical_states = CanonicalOperationStateService()
        self.workspace_contexts = WorkspaceContextService()
        self.retrieval_contexts = RetrievalContextService()
        self.execution_contexts = ExecutionContextService(
            workspace_contexts=self.workspace_contexts,
            retrieval_contexts=self.retrieval_contexts,
        )
        self.execution_plan_promotion = ExecutionPlanPromotionService()

    def create_run(self, request: TaskRunRequest) -> TaskRun:
        requested_start = bool(request.start_immediately)
        plan = self.planner.plan(request)
        runtime_profile = str(plan.metadata.get("runtime_profile") or request.runtime_profile or "") or None
        effective_operation_type = str(
            request.operation_type
            or request.intent_map.get("operation_type")
            or request.intent_map.get("intent_type")
            or request.contract_type
        )
        workspace_context = self.workspace_contexts.from_request(request, runtime_profile=runtime_profile)
        retrieval_context = self.retrieval_contexts.from_workspace_context(
            workspace_context,
            task_id=request.task_id,
            task_run_id=request.task_run_id,
            phase=str(request.intent_map.get("current_phase") or request.intent_map.get("phase") or "") or None,
        )
        effective_workspace = workspace_context.workspace_path or request.workspace
        bootstrap = self.bootstrap.bootstrap(
            TaskBootstrapRequest(
                session_id=request.session_id,
                workspace=effective_workspace,
                contract_type=request.contract_type,
                operation_type=effective_operation_type,
                runtime_profile=runtime_profile,
                requested_actions=list(plan.metadata.get("normalized_actions", []) or request.requested_actions),
                intent_map=dict(request.intent_map),
                source_channel=request.source_channel,
                task_id=request.task_id,
                operation_id=request.operation_id,
                task_run_id=request.task_run_id,
                workspace_id=workspace_context.workspace_id or request.workspace_id,
                project_id=workspace_context.project_id or request.project_id,
                parent_task_id=request.parent_task_id,
            )
        )
        task = bootstrap.universal_task
        profile_requirements = (plan.metadata.get("workspace_requirements") or {}) if isinstance(plan.metadata.get("workspace_requirements"), dict) else {}
        workspace = WorkspacePolicyService().load().evaluate(
            workspace_path=effective_workspace,
            requires_workspace=bool(profile_requirements.get("required", request.contract_type in {"analysis_readonly", "readonly_analysis", "validation_request"})),
        )
        run = TaskRun(
            run_id=task.task_run_id,
            task_id=task.task_id,
            operation_id=task.operation_id,
            task_run_id=task.task_run_id,
            workspace_id=task.workspace_id,
            project_id=task.project_id,
            parent_task_id=task.parent_task_id,
            current_sprint=task.current_sprint,
            current_phase=task.current_phase,
            bootstrap_context=task.model_dump(mode="json"),
            source_type=request.source_type,
            draft_id=request.draft_id,
            preview_id=request.preview_id,
            approval_id=request.approval_id,
            session_id=request.session_id,
            workspace=effective_workspace,
            contract_type=request.contract_type,
            operation_type=effective_operation_type,
            runtime_profile=runtime_profile,
            capabilities_required=list(plan.metadata.get("required_capabilities", []) or request.capabilities_required),
            requested_actions=list(plan.metadata.get("normalized_actions", []) or request.requested_actions),
            intent_map=dict(request.intent_map),
            mode=request.mode,
            plan=plan,
            policy_snapshot=self.store.sanitize(request.policy_decision),
            context_injection_plan_id=request.context_injection_plan_id,
            workspace_snapshot={
                "status": workspace.status,
                "workspace_path": workspace.workspace_path,
                "workspace_context_id": workspace_context.context_id,
                "workspace_id": workspace_context.workspace_id,
                "project_id": workspace_context.project_id,
                "project_root": workspace_context.project_root,
                "retrieval_scope": workspace_context.retrieval_scope,
                "blocked": workspace.blocked,
                "needs_clarification": workspace.needs_clarification,
                "reason": workspace.reason,
            },
            workspace_context=workspace_context,
            retrieval_context=retrieval_context,
            approval_snapshot=self._approval_snapshot(request.approval_id),
            auto_run_requested=requested_start,
            warnings=(
                ["auto_run_disabled_by_policy"]
                if requested_start and not self.queue.auto_run_enabled
                else []
            ),
            trace=list(plan.trace),
        )
        if run.plan.canonical_execution_plan is None:
            candidate = self.execution_plan_promotion.candidate_from_task_run_plan(
                request=request,
                plan=run.plan,
                workspace_context=workspace_context.model_dump(mode="json"),
            )
            promotion = self.execution_plan_promotion.promote(
                candidate,
                policy_snapshot=request.policy_decision,
                task_id=run.task_id,
                taskrun_id=run.run_id,
                approval_id=run.approval_id,
            )
            run.plan.candidate_plan = candidate
            run.plan.canonical_execution_plan = promotion.execution_plan
            run.plan.metadata["candidate_plan_id"] = candidate.candidate_plan_id
            if promotion.execution_plan is not None:
                run.plan.metadata["execution_id"] = promotion.execution_plan.execution_id
                run.plan.metadata["canonical_execution_plan"] = promotion.execution_plan.model_dump(mode="json")
            if promotion.reason_codes:
                run.plan.status = "blocked"
                run.plan.blocked_reasons = list(
                    dict.fromkeys([*run.plan.blocked_reasons, *promotion.reason_codes])
                )
            run.trace.append(
                self.trace.item(
                    "legacy_plan_promoted_to_canonical_execution_plan",
                    promotion.status,
                    "task_run_plan_promoted_before_runtime_execution",
                    source="services/runtime/task_runtime_service.py",
                    data={
                        "candidate_plan_id": candidate.candidate_plan_id,
                        "execution_id": promotion.execution_plan.execution_id if promotion.execution_plan else None,
                        "reason_codes": promotion.reason_codes,
                    },
                )
            )
        if run.plan.canonical_execution_plan is not None:
            bound_execution_plan = self.execution_plan_promotion.bind_runtime_identity(
                run.plan.canonical_execution_plan,
                task_id=run.task_id,
                taskrun_id=run.run_id,
                approval_id=run.approval_id,
            )
            run.plan.canonical_execution_plan = bound_execution_plan
            run.plan.metadata["execution_id"] = bound_execution_plan.execution_id
            run.plan.metadata["canonical_execution_plan"] = bound_execution_plan.model_dump(mode="json")
            run.trace.append(
                self.trace.item(
                    "execution_plan_identity_bound",
                    "ready" if bound_execution_plan.status == "ready" else bound_execution_plan.status,
                    "canonical_execution_plan_bound_to_task_run",
                    source="services/runtime/task_runtime_service.py",
                    data={
                        "execution_id": bound_execution_plan.execution_id,
                        "task_id": run.task_id,
                        "task_run_id": run.run_id,
                    },
                )
            )
        run.execution_graph = self.execution_graphs.build_from_plan(
            run_id=run.run_id,
            plan=plan,
            workspace=run.workspace,
            contract_type=run.contract_type,
            operation_type=run.operation_type,
            runtime_profile=run.runtime_profile,
            requested_actions=run.requested_actions,
            capabilities_required=run.capabilities_required,
        )
        run.workflow = self.workflows.create_for_run(run)
        run.execution_context = self.execution_contexts.create_for_run(run)
        run.canonical_state = self.canonical_states.derive(run)
        self._validate_context_plan(run)
        if plan.status == "blocked":
            run.blocked_reasons.extend(plan.blocked_reasons)

        self.store.create_run(run)
        if run.approval_id:
            self.approvals.attach_runtime_context(
                run.approval_id,
                run_id=run.run_id,
                task_id=run.task_id,
                workspace_path=run.workspace,
                execution_plan=run.plan.canonical_execution_plan.model_dump(mode="json") if run.plan.canonical_execution_plan else None,
            )
            run.approval_snapshot = self._approval_snapshot(run.approval_id)
            self.store.update_run(run)
        self.events.create(
            run.run_id,
            "run_created",
            "created",
            "TaskRun created without execution.",
            metadata={
                "source_type": run.source_type,
                "task_id": run.task_id,
                "task_run_id": run.run_id,
                "operation_id": run.operation_id,
                "workspace_id": run.workspace_id,
                "project_id": run.project_id,
                "parent_task_id": run.parent_task_id,
                "workflow_id": run.workflow.workflow_id if run.workflow else None,
                "contract_type": run.contract_type,
                "auto_run_requested": run.auto_run_requested,
            },
        )
        self.events.create(
            run.run_id,
            "task_bootstrap_created",
            "created",
            "Universal Task identity created before execution.",
            metadata={
                "task_id": run.task_id,
                "task_run_id": run.run_id,
                "operation_id": run.operation_id,
                "runtime_profile": run.runtime_profile,
                "workspace_id": run.workspace_id,
                "project_id": run.project_id,
                "current_phase": run.current_phase,
                "workflow_id": run.workflow.workflow_id if run.workflow else None,
                "parent_task_id": run.parent_task_id,
                "execution_allowed_to_start": False,
            },
        )
        self.events.create(
            run.run_id,
            "PlanningStarted",
            "planning",
            "Canonical planning started before execution.",
            metadata={"task_id": run.task_id, "task_run_id": run.run_id},
        )
        self.events.create(
            run.run_id,
            "PlanningFinished",
            "planned" if run.plan.status != "blocked" else "blocked",
            "Canonical planning finished.",
            metadata={"plan_id": run.plan.plan_id, "blocked_reasons": run.plan.blocked_reasons},
        )
        self.events.create(
            run.run_id,
            "ExecutionPlanCreated",
            run.plan.canonical_execution_plan.status if run.plan.canonical_execution_plan else "missing",
            "Canonical ExecutionPlan created as execution boundary.",
            metadata={
                "execution_id": run.plan.canonical_execution_plan.execution_id if run.plan.canonical_execution_plan else None,
                "approval_required": run.plan.canonical_execution_plan.approval_required if run.plan.canonical_execution_plan else None,
                "targets": run.plan.canonical_execution_plan.targets if run.plan.canonical_execution_plan else [],
            },
        )
        decision = self.guard.check_run(run)
        approval_reason_markers = [
            reason
            for reason in decision.blocked_reasons
            if reason == "approval_required" or str(reason).startswith("permission_requires_approval:")
        ]
        approval_wait = (
            bool(run.approval_id)
            and bool(approval_reason_markers)
        )
        hard_guard_reasons = [
            reason
            for reason in decision.blocked_reasons
            if reason not in approval_reason_markers
        ]
        approval_missing = (
            bool(approval_reason_markers)
            and not run.approval_id
        )

        if (
            hard_guard_reasons
            or plan.status == "blocked"
            or run.blocked_reasons
            or approval_missing
        ):
            run.blocked_reasons = list(
                dict.fromkeys(
                    [
                        *run.blocked_reasons,
                        *hard_guard_reasons,
                        *(approval_reason_markers if approval_missing else []),
                    ]
                )
            )
            run.trace.extend(decision.trace)
            self.lifecycle.transition(run, "blocked")
            self.store.update_run(run)
            self.store.save_trace(run.run_id, run.trace)
            if approval_missing or hard_guard_reasons or plan.status == "blocked":
                self.events.create(
                    run.run_id,
                    "policy_blocked_no_approval_possible",
                    "blocked",
                    "Policy blocked the TaskRun without an actionable approval path.",
                    metadata={
                        "approval_missing": approval_missing,
                        "hard_guard_reasons": hard_guard_reasons,
                        "plan_status": plan.status,
                        "blocked_reasons": run.blocked_reasons,
                    },
                )
            self._record_block(run, "TaskRun blocked during creation guard.")
            self.audit.record(
                run_id=run.run_id,
                action="create",
                status="blocked",
                reason=",".join(run.blocked_reasons),
            )
        elif approval_wait:
            run.trace.extend(decision.trace)
            self.lifecycle.transition(run, "waiting_input")
            self.store.update_run(run)
            self.store.save_trace(run.run_id, run.trace)
            self.events.create(
                run.run_id,
                "run_waiting_input",
                "waiting_input",
                "TaskRun queued and waiting for explicit approval.",
                metadata={"approval_id": run.approval_id},
            )
            self.events.create(
                run.run_id,
                "approval_preview_created",
                "pending",
                "TaskRun tem preview e ApprovalRequest acionavel antes de qualquer side effect.",
                metadata={"approval_id": run.approval_id, "operation_type": run.operation_type},
            )
            self.events.create(
                run.run_id,
                "approval_required",
                "pending",
                "Explicit approval is required before execution.",
                metadata={"approval_id": run.approval_id},
            )
            self.audit.record(
                run_id=run.run_id,
                action="create",
                status="waiting_input",
                reason="approval_required",
            )
        elif requested_start and self.queue.auto_run_enabled:
            run.trace.extend(decision.trace)
            self.lifecycle.transition(run, "queued")
            self.store.update_run(run)
            self.store.save_trace(run.run_id, run.trace)
            self.events.create(
                run.run_id,
                "run_queued",
                "queued",
                "TaskRun entered the governed queue.",
            )
            self.events.create(
                run.run_id,
                "run_auto_start_requested",
                "queued",
                "Auto-run requested; queue order and runtime guards still apply.",
            )
            self.audit.record(
                run_id=run.run_id,
                action="create",
                status="queued",
                reason="auto_run_requested",
            )
        else:
            self.audit.record(
                run_id=run.run_id,
                action="create",
                status="allowed",
                reason="created_awaiting_queue_action",
            )

        self.queue.reconcile()
        final_run = self.store.get_run(run.run_id) or run
        self.operational_memory.capture_task_run(final_run, trigger="task_run_created")
        return final_run

    def create_from_draft(
        self,
        draft_id: str,
        overrides: dict[str, Any] | None = None,
    ) -> TaskRun:
        draft = self.drafts.get_draft(draft_id)
        if draft is None:
            raise ValueError("task_draft_not_found")
        data = overrides or {}
        return self.create_run(
            TaskRunRequest(
                source_type="draft",
                draft_id=draft.draft_id,
                session_id=draft.session_id,
                workspace=draft.workspace.path,
                contract_type=draft.contract_type,
                operation_type=str(draft.operation_type or draft.intent_map.get("operation_type") or draft.intent_map.get("intent_type") or draft.contract_type),
                runtime_profile=draft.runtime_profile,
                intent_map=draft.intent_map,
                policy_decision=draft.policy_decision,
                context_injection_plan_id=data.get("context_injection_plan_id"),
                approval_id=data.get("approval_id"),
                requested_actions=list(draft.requested_actions),
                start_immediately=bool(data.get("start_immediately", False)),
                include_trace=bool(data.get("include_trace", False)),
            )
        )

    def create_from_preview(
        self,
        preview_id: str,
        overrides: dict[str, Any] | None = None,
    ) -> TaskRun:
        preview = self.previews.get_preview(preview_id)
        if preview is None:
            raise ValueError("task_preview_not_found")
        draft = self.drafts.get_draft(preview.draft_id)
        if draft is None:
            raise ValueError("task_draft_not_found")
        data = overrides or {}
        approval_id = data.get("approval_id")
        if preview.status == "approval_required" and not approval_id:
            approval = self.approvals.create_approval_for_preview(
                preview.preview_id,
                reason="task_runtime_preview_requires_approval",
            )
            approval_id = approval.approval_id
        snapshot = preview.policy_snapshot.model_dump()
        snapshot["status"] = snapshot.get("policy_status")
        return self.create_run(
            TaskRunRequest(
                source_type="preview",
                draft_id=draft.draft_id,
                preview_id=preview.preview_id,
                session_id=preview.session_id,
                workspace=draft.workspace.path,
                contract_type=preview.contract_type,
                operation_type=str(draft.operation_type or draft.intent_map.get("operation_type") or draft.intent_map.get("intent_type") or preview.contract_type),
                runtime_profile=draft.runtime_profile,
                intent_map=draft.intent_map,
                policy_decision=snapshot,
                context_injection_plan_id=data.get("context_injection_plan_id"),
                approval_id=approval_id,
                requested_actions=list(preview.requested_actions),
                start_immediately=bool(data.get("start_immediately", False)),
                include_trace=bool(data.get("include_trace", False)),
            )
        )

    def start(self, run_id):
        run, result = self.loop.run(run_id)
        self._publish_terminal_result(run, result)
        self.operational_memory.capture_task_run(run, trigger="task_run_finished")
        return run, result

    def cancel(
        self,
        run_id,
        request: TaskCancellationRequest | None = None,
    ):
        run = self.store.get_run(run_id)
        result = self.cancellation.cancel(run_id, request)
        if run is not None and result.cancellation_requested:
            self._cancel_linked_pending_approval(
                run.approval_id,
                request.reason if request else "task_cancelled",
            )
        self.queue.reconcile()
        return result

    def get_run(self, run_id):
        return self.store.get_run(run_id)

    def get_events(self, run_id):
        return self.events.list(run_id)

    def get_timeline(self, run_id):
        return self.timeline.build(run_id)

    def get_runtime_truth(self, run_id):
        run = self.store.get_run_lightweight(run_id)
        if run is None:
            return None
        result = self.store.get_result(run_id)
        if result is None and str(run.status) in {"created", "queued", "running", "waiting_input", "waiting_delegation"}:
            return self.truth.evaluate(run, result=None, timeline=None)
        if str(run.status) in {"blocked", "failed", "cancelled", "expired"}:
            return self.truth.evaluate(run, result=result, timeline=None)
        return self.truth.evaluate(
            run,
            result=result,
            timeline=self.timeline.build(run_id),
        )

    def get_trace(self, run_id):
        return self.store.get_trace(run_id)

    def get_execution_graph(self, run_id):
        run = self.store.get_run(run_id)
        if run is None:
            return None
        return run.execution_graph

    def create_cooperative_execution_graph(
        self,
        run_id,
        *,
        objective: str | None = None,
        requested_nodes: list[str] | None = None,
    ):
        run = self.store.get_run(run_id)
        if run is None:
            return None
        planning_report = self.intelligent_planner.plan(
            objective=objective or run.operation_type or run.contract_type or "cooperative_task",
            workspace=run.workspace,
            contract_type=run.contract_type,
            operation_type=run.operation_type,
            runtime_profile=run.runtime_profile,
            requested_actions=run.requested_actions,
            requested_capabilities=run.capabilities_required,
            requested_nodes=requested_nodes or [],
            policy_snapshot=run.policy_snapshot,
        )
        run.execution_graph = self.execution_graphs.build_from_planning_report(
            run_id=run.run_id,
            planning_report=planning_report,
            workspace=run.workspace,
            contract_type="multi_agent_execution_graph",
            operation_type="multi_agent_execution_graph",
            runtime_profile="cooperative_graph",
            requested_actions=run.requested_actions,
        )
        run.intent_map["execution_graph_id"] = run.execution_graph.graph_id
        run.intent_map["execution_graph_type"] = run.execution_graph.graph_type
        run.intent_map["planning_report"] = planning_report.model_dump(mode="json")
        self.store.update_run(run)
        self.events.create(
            run.run_id,
            "planning_report_created",
            planning_report.status,
            "Intelligent Planner created an adaptive execution strategy.",
            metadata={
                "planning_report_id": planning_report.report_id,
                "task_type": planning_report.intent.task_type,
                "strategy": planning_report.strategy.name,
                "nodes": [node.node_id for node in planning_report.nodes],
            },
        )
        self.events.create(
            run.run_id,
            "execution_graph_created",
            run.execution_graph.status,
            "Multi-agent ExecutionGraph created by AIpinho.",
            metadata={
                "graph_id": run.execution_graph.graph_id,
                "graph_type": run.execution_graph.graph_type,
                "nodes": [node.node_id for node in run.execution_graph.nodes],
            },
        )
        for node in run.execution_graph.nodes:
            if node.status in {"ready", "waiting"}:
                self.events.create(
                    run.run_id,
                    "node_waiting",
                    node.status,
                    f"Node {node.node_id} is {node.status}.",
                    metadata={"graph_id": run.execution_graph.graph_id, "node_id": node.node_id, "executor": node.executor},
                )
        return run.execution_graph

    def get_planning_report(self, run_id):
        run = self.store.get_run(run_id)
        if run is None:
            return None
        report = (run.intent_map or {}).get("planning_report") if isinstance(run.intent_map, dict) else None
        if isinstance(report, dict):
            return report
        graph = getattr(run, "execution_graph", None)
        report = getattr(graph, "planning_report", None) if graph is not None else None
        return report if isinstance(report, dict) else None

    def replan_execution_node(self, run_id, node_id, *, reason: str = "node_replan_requested"):
        run = self.store.get_run(run_id)
        if run is None:
            return None
        report_data = self.get_planning_report(run_id)
        if not isinstance(report_data, dict):
            return None
        from aipinho.schemas.runtime.intelligent_planner import PlanningReport

        replanned = self.intelligent_planner.replan_after_node_failure(
            PlanningReport(**report_data),
            failed_node_id=node_id,
            reason=reason,
        )
        run.intent_map["planning_report"] = replanned.model_dump(mode="json")
        if run.execution_graph is not None:
            run.execution_graph.planning_report = replanned.model_dump(mode="json")
            run.execution_graph = self.execution_graphs.retry_node(run.execution_graph, node_id, reason=reason)
        self.store.update_run(run)
        self.events.create(
            run.run_id,
            "execution_plan_replanned",
            "ready",
            f"Planner replanned around node {node_id}.",
            metadata={
                "planning_report_id": replanned.report_id,
                "replan_of": replanned.replan_of,
                "node_id": node_id,
                "reason": reason,
            },
        )
        return {"planning_report": replanned, "execution_graph": run.execution_graph}

    def poll_execution_graph(self, run_id):
        run = self.store.get_run(run_id)
        if run is None:
            return None
        run.execution_graph = self.execution_graphs.poll_graph(run.execution_graph)
        self.store.update_run(run)
        return run.execution_graph

    def start_execution_node(self, run_id, node_id):
        run = self.store.get_run(run_id)
        if run is None:
            return None
        run.execution_graph = self.execution_graphs.mark_node_started(run.execution_graph, node_id)
        self.store.update_run(run)
        self.events.create(
            run.run_id,
            "node_started",
            "running",
            f"ExecutionGraph node {node_id} started.",
            metadata=self._graph_node_event_metadata(run, node_id),
        )
        return run.execution_graph

    def complete_execution_node(
        self,
        run_id,
        node_id,
        *,
        outputs: dict[str, Any] | None = None,
        artifact_refs: list[dict[str, Any]] | None = None,
        memory_candidates: list[dict[str, Any]] | None = None,
        speakertruth: dict[str, Any] | None = None,
        review: dict[str, Any] | None = None,
        validation: dict[str, Any] | None = None,
    ):
        run = self.store.get_run(run_id)
        if run is None:
            return None
        before_edges = {
            (dep.source_node_id, dep.target_node_id): dep.status
            for dep in (run.execution_graph.dependencies if run.execution_graph else [])
        }
        run.execution_graph = self.execution_graphs.mark_node_finished(
            run.execution_graph,
            node_id,
            status="completed",
            outputs=outputs,
            artifact_refs=artifact_refs,
            memory_candidates=memory_candidates,
            speakertruth=speakertruth,
            review=review,
            validation=validation,
        )
        self.store.update_run(run)
        self.events.create(
            run.run_id,
            "node_completed",
            "completed",
            f"ExecutionGraph node {node_id} completed.",
            metadata=self._graph_node_event_metadata(run, node_id),
        )
        for dependency in (run.execution_graph.dependencies if run.execution_graph else []):
            key = (dependency.source_node_id, dependency.target_node_id)
            if before_edges.get(key) != "completed" and dependency.status == "completed":
                self.events.create(
                    run.run_id,
                    "edge_completed",
                    "completed",
                    f"ExecutionGraph edge {dependency.source_node_id} -> {dependency.target_node_id} completed.",
                    metadata={
                        "graph_id": run.execution_graph.graph_id,
                        "source_node_id": dependency.source_node_id,
                        "target_node_id": dependency.target_node_id,
                    },
                )
        if run.execution_graph and run.execution_graph.status == "completed":
            self.events.create(
                run.run_id,
                "graph_completed",
                "completed",
                "ExecutionGraph completed.",
                metadata={"graph_id": run.execution_graph.graph_id},
            )
        return run.execution_graph

    def fail_execution_node(self, run_id, node_id, *, reason: str = "node_failed"):
        run = self.store.get_run(run_id)
        if run is None:
            return None
        run.execution_graph = self.execution_graphs.mark_node_finished(
            run.execution_graph,
            node_id,
            status="failed",
            violations=[reason],
        )
        self.store.update_run(run)
        self.events.create(
            run.run_id,
            "node_failed",
            "failed",
            f"ExecutionGraph node {node_id} failed.",
            metadata={**self._graph_node_event_metadata(run, node_id), "reason": reason},
        )
        if run.execution_graph and run.execution_graph.status in {"failed", "blocked"}:
            self.events.create(
                run.run_id,
                "graph_failed",
                run.execution_graph.status,
                "ExecutionGraph failed or blocked.",
                metadata={"graph_id": run.execution_graph.graph_id, "reason": reason},
            )
        return run.execution_graph

    def retry_execution_node(self, run_id, node_id, *, reason: str = "retry_node_requested"):
        run = self.store.get_run(run_id)
        if run is None:
            return None
        run.execution_graph = self.execution_graphs.retry_node(run.execution_graph, node_id, reason=reason)
        self.store.update_run(run)
        self.events.create(
            run.run_id,
            "node_waiting",
            "retry",
            f"ExecutionGraph node {node_id} scheduled for retry.",
            metadata={**self._graph_node_event_metadata(run, node_id), "reason": reason},
        )
        return run.execution_graph

    def cancel_execution_node(self, run_id, node_id, *, reason: str = "node_cancelled"):
        run = self.store.get_run(run_id)
        if run is None:
            return None
        run.execution_graph = self.execution_graphs.cancel_node(run.execution_graph, node_id, reason=reason)
        self.store.update_run(run)
        self.events.create(
            run.run_id,
            "node_failed",
            "cancelled",
            f"ExecutionGraph node {node_id} cancelled.",
            metadata={**self._graph_node_event_metadata(run, node_id), "reason": reason},
        )
        return run.execution_graph

    def get_operational_memory(self, run_id):
        return self.operational_memory.list_for_run(run_id)

    def build_evidence_decision(self, run_id, *, subject, decision, required_kinds=None):
        run = self.store.get_run(run_id)
        if run is None:
            return None
        return self.evidence_engine.decide_from_task_run(
            run,
            subject=subject,
            decision=decision,
            required_kinds=required_kinds,
            operational_memory=self.get_operational_memory(run_id),
        )

    def _graph_node_event_metadata(self, run, node_id) -> dict[str, Any]:
        graph = run.execution_graph
        node = None
        if graph is not None:
            node = next((item for item in graph.nodes if item.node_id == node_id), None)
        return {
            "graph_id": graph.graph_id if graph else None,
            "graph_status": graph.status if graph else None,
            "node_id": node_id,
            "executor": getattr(node, "executor", None) or getattr(node, "worker", None),
            "runtime_profile": getattr(node, "runtime_profile", None),
            "retry_count": getattr(node, "retry_count", 0),
        }

    def evaluate_continuous_runtime(self, run_id, *, objective=None):
        run = self.store.get_run(run_id)
        if run is None:
            return None
        return self.continuous_runtime.evaluate(run, objective=objective)

    def create_engineering_mission_from_run(self, run_id, *, objective=None):
        run = self.store.get_run(run_id)
        if run is None:
            return None
        mission = self.engineering_autopilot.create_mission(
            objective=objective or run.operation_type or run.contract_type or "governed_engineering_mission",
            session_id=run.session_id,
            workspace=run.workspace,
        )
        cycle = self.continuous_runtime.evaluate(run, objective=mission.objective)
        return self.engineering_autopilot.attach_run(mission, run, cycle)

    def build_tool_governance_trail(self, run_id):
        run = self.store.get_run(run_id)
        if run is None:
            return None
        return self.tool_governance.build_and_audit(
            run,
            result=self.store.get_result(run_id),
        )

    def get_result(self, run_id):
        result = self.store.get_result(run_id)
        if result is not None:
            return result
        return self.store.ensure_terminal_result(run_id)

    def list_runs(self, **filters):
        self.queue.reconcile()
        return self.store.list_runs(**filters)

    def get_active_run(self, session_id=None):
        queue = self.queue.reconcile().snapshot
        for item in queue.items:
            if session_id and item.session_id != session_id:
                continue
            run = self.store.get_run(item.run_id)
            if run is not None:
                return run
        return None

    def queue_status(self):
        snapshot = self.queue.snapshot()
        return TaskQueueReconciliationResult(
            status="degraded" if snapshot.warnings else "ok",
            cancelled_run_ids=[],
            cancelled_approval_ids=[],
            warnings=list(snapshot.warnings),
            snapshot=snapshot,
        )

    def process_queue(self):
        with self._queue_process_lock:
            queue = self.queue.reconcile().snapshot
            if queue.active_count:
                return {
                    "status": "active_task_running",
                    "started_run_id": None,
                    "queue": queue,
                }
            head = queue.items[0] if queue.items else None
            if head is None:
                return {
                    "status": "queue_empty",
                    "started_run_id": None,
                    "queue": queue,
                }
            if head.requires_decision:
                return {
                    "status": "waiting_for_human_decision",
                    "started_run_id": None,
                    "queue": queue,
                }
            if (
                self.queue.auto_run_requires_explicit_request
                and not head.auto_run_requested
            ):
                return {
                    "status": "manual_start_required",
                    "started_run_id": None,
                    "queue": queue,
                }
            run = self.store.get_run(head.run_id)
            if run is None:
                return {
                    "status": "queue_head_missing",
                    "started_run_id": None,
                    "queue": queue,
                }
            if run.status not in {"created", "queued", "waiting_input"}:
                return {
                    "status": "queue_head_not_startable",
                    "started_run_id": None,
                    "queue": queue,
                }
            started, result = self.loop.run(run.run_id)
            self._publish_terminal_result(started, result)
            self.operational_memory.capture_task_run(started, trigger="task_run_finished")
            return {
                "status": started.status,
                "started_run_id": started.run_id,
                "run": started,
                "result": result,
                "queue": self.queue.reconcile().snapshot,
            }

    def _publish_terminal_result(self, run, result) -> None:
        try:
            self.result_publisher.publish(run, result)
        except Exception:
            # Chat publication is best-effort and must not invalidate a completed task.
            return

    def _validate_context_plan(self, run: TaskRun) -> None:
        if not run.context_injection_plan_id:
            return
        context_plan = self.context_planner.get_plan(run.context_injection_plan_id)
        if context_plan is None:
            run.blocked_reasons.append("context_injection_plan_not_found")
            return
        context_validation = self.context_validator.validate_plan(context_plan)
        run.blocked_reasons.extend(context_validation.violations)
        if any(item.kind == "curated_memory" for item in context_plan.context_items):
            run.blocked_reasons.append(
                "task_runtime_curated_memory_blocked_by_default"
            )

    def _approval_snapshot(self, approval_id):
        approval = self.approvals.get_approval(approval_id) if approval_id else None
        return self.store.sanitize(approval.model_dump()) if approval else {}

    def _cancel_linked_pending_approval(self, approval_id, reason):
        if not approval_id:
            return
        approval = self.approvals.get_approval(approval_id)
        if approval is not None and approval.status == "pending":
            self.approvals.cancel(
                approval_id,
                actor=Actor(type="system", id="task_runtime_service"),
                reason=reason,
            )

    def _record_block(self, run: TaskRun, message: str) -> None:
        cause = self.block_causes.build(run, run.blocked_reasons)
        run.block_cause = cause
        run.trace.append(
            self.trace.item(
                "task_blocked",
                "blocked",
                cause.block_reason_code,
                source="services/runtime/task_runtime_service.py",
                data={
                    "block_id": cause.block_id,
                    "blocked_stage": cause.blocked_stage,
                    "safe_alternatives": cause.safe_alternatives,
                },
            )
        )
        policy_event = self.events.create(
            run.run_id,
            "policy_decision",
            "blocked",
            "A runtime policy decision blocked the task.",
            metadata={"block_cause": cause.model_dump()},
        )
        event = self.events.create(
            run.run_id,
            "task_blocked",
            "blocked",
            message,
            metadata={"block_cause": cause.model_dump(), "policy_event_id": policy_event.event_id},
        )
        cause.event_id = event.event_id
        run.block_cause = cause
        self.events.create(
            run.run_id,
            "run_blocked",
            "blocked",
            message,
            metadata={"block_id": cause.block_id, "task_blocked_event_id": event.event_id},
        )
        self.store.update_run(run)
        self.store.save_trace(run.run_id, run.trace)

    def status(self):
        statuses = {
            name: inspect_yaml_file(
                PATHS.config_root / "runtime" / name,
                root=PATHS.project_root,
            ).__dict__
            for name in self.CONFIGS
        }
        warnings = [
            f"{name}:{value.get('status')}"
            for name, value in statuses.items()
            if value.get("status") != "ok"
        ]
        settings = (
            self.policy.get("task_runtime", {})
            if isinstance(self.policy.get("task_runtime", {}), dict)
            else {}
        )
        side = (
            self.policy.get("side_effects", {})
            if isinstance(self.policy.get("side_effects", {}), dict)
            else {}
        )
        return TaskRuntimeStatus(
            status="degraded" if warnings else "ok",
            enabled=bool(settings.get("enabled", False)),
            mode=str(settings.get("mode", "read_only")),
            write_enabled=bool(side.get("workspace_write_enabled", False)),
            patch_enabled=bool(side.get("patch_enabled", False)),
            shell_enabled=bool(side.get("shell_enabled", False)),
            git_write_enabled=bool(side.get("git_write_enabled", False)),
            rag_enabled=bool(side.get("rag_write_enabled", False)),
            memory_write_enabled=bool(side.get("memory_write_enabled", False)),
            background_execution=bool(
                settings.get("allow_background_execution", False)
            ),
            real_model_auto_use=False,
            model_tool_calling_enabled=False,
            allowed_actions=list(self.policy.get("allowed_actions", []) or []),
            configs=statuses,
            warnings=warnings,
            validation_gate_enabled=True,
            report_quality_gate_enabled=True,
            side_effect_validation_enabled=True,
        )
