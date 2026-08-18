from __future__ import annotations

from time import monotonic
from typing import Any

from aipinho.schemas.runtime.execution_graph import (
    ExecutionCheckpoint,
    ExecutionContext,
    ExecutionEdge,
    ExecutionDependency,
    ExecutionGraph,
    ExecutionMetrics,
    ExecutionNode,
    ExecutionResult,
    NodeRuntime,
    ExecutionResume,
)
from aipinho.schemas.runtime.intelligent_planner import PlanningReport
from aipinho.schemas.runtime.task_run_plan import TaskRunPlan
from aipinho.schemas.runtime.task_run_step import TaskRunStep
from aipinho.services.session.session_store import utc_now
from aipinho.services.runtime.worker_registry_service import WorkerRegistryService


class DependencyResolver:
    """Builds a DAG from runtime steps without relying on a fixed linear executor."""

    def resolve(self, steps: list[TaskRunStep]) -> list[ExecutionEdge]:
        edges: list[ExecutionEdge] = []
        last_context_node: str | None = None
        last_side_effect_node: str | None = None
        previous_required_node: str | None = None
        for step in steps:
            node_id = self.node_id(step)
            action = str(step.action or "")
            step_type = str(step.step_type or "")
            dependencies: list[tuple[str, str]] = []
            if self._is_validation(action, step_type) and last_side_effect_node:
                dependencies.append((last_side_effect_node, "validate_latest_side_effect"))
            elif step.side_effect and last_context_node:
                dependencies.append((last_context_node, "requires_context_before_side_effect"))
            elif self._is_reporting(action, step_type) and previous_required_node:
                dependencies.append((previous_required_node, "report_after_required_work"))
            elif previous_required_node and step.required:
                dependencies.append((previous_required_node, "required_step_dependency"))
            for source_id, reason in dependencies:
                edges.append(ExecutionEdge(from_node_id=source_id, to_node_id=node_id, reason=reason))
            if not step.side_effect:
                last_context_node = node_id
            if step.side_effect:
                last_side_effect_node = node_id
            if step.required:
                previous_required_node = node_id
        return edges

    @staticmethod
    def node_id(step: TaskRunStep) -> str:
        return f"node_{step.step_id}"

    @staticmethod
    def _is_validation(action: str, step_type: str) -> bool:
        text = f"{action} {step_type}".casefold()
        return "validat" in text or "test" in text

    @staticmethod
    def _is_reporting(action: str, step_type: str) -> bool:
        text = f"{action} {step_type}".casefold()
        return "report" in text or "artifact" in text or "publish" in text


class ExecutionScheduler:
    def ready_nodes(self, graph: ExecutionGraph) -> list[ExecutionNode]:
        completed = {node.node_id for node in graph.nodes if node.status in {"completed", "partial", "skipped"}}
        blocked = {node.node_id for node in graph.nodes if node.status in {"blocked", "failed", "cancelled"}}
        ready: list[ExecutionNode] = []
        for node in graph.nodes:
            if node.status not in {"pending", "waiting"}:
                continue
            dependencies = [edge.from_node_id for edge in graph.edges if edge.to_node_id == node.node_id and edge.required]
            if any(dep in blocked for dep in dependencies):
                continue
            if all(dep in completed for dep in dependencies):
                ready.append(node)
        return ready

    def resume(self, graph: ExecutionGraph) -> ExecutionResume:
        return ExecutionResume(
            graph_id=graph.graph_id,
            run_id=graph.run_id,
            ready_node_ids=[node.node_id for node in self.ready_nodes(graph)],
            blocked_node_ids=[node.node_id for node in graph.nodes if node.status == "blocked"],
            completed_node_ids=[node.node_id for node in graph.nodes if node.status in {"completed", "partial"}],
            status=graph.status,
        )


class ExecutionGraphService:
    def __init__(self, resolver: DependencyResolver | None = None, scheduler: ExecutionScheduler | None = None, workers: WorkerRegistryService | None = None) -> None:
        self.resolver = resolver or DependencyResolver()
        self.scheduler = scheduler or ExecutionScheduler()
        self.workers = workers or WorkerRegistryService()

    def build_from_plan(
        self,
        *,
        run_id: str,
        plan: TaskRunPlan,
        workspace: str | None,
        contract_type: str | None,
        operation_type: str | None,
        runtime_profile: str | None,
        requested_actions: list[str],
        capabilities_required: list[str],
    ) -> ExecutionGraph:
        nodes = [
            self._node_from_step(
                step,
                contract_type=contract_type,
                capabilities_required=capabilities_required,
            )
            for step in plan.steps
        ]
        edges = self.resolver.resolve(plan.steps)
        graph = ExecutionGraph(
            run_id=run_id,
            graph_type="task_plan",
            status="ready" if plan.status == "ready" else "blocked",
            context=ExecutionContext(
                run_id=run_id,
                workspace=workspace,
                contract_type=contract_type,
                operation_type=operation_type,
                runtime_profile=runtime_profile,
                requested_actions=requested_actions,
                evidence_refs=[{"type": "task_run_plan", "ref_id": plan.plan_id}],
            ),
            nodes=nodes,
            edges=edges,
            checkpoints=[
                ExecutionCheckpoint(
                    status=plan.status,
                    summary="ExecutionGraph built from TaskRunPlan.",
                    evidence_refs=[{"type": "task_run_plan", "ref_id": plan.plan_id}],
                )
            ],
            warnings=[] if self._is_acyclic(nodes, edges) else ["execution_graph_cycle_detected"],
        )
        if graph.warnings:
            graph.status = "blocked"
            graph.lifecycle.status = "blocked"
        else:
            graph.lifecycle.status = graph.status
        for node in self.scheduler.ready_nodes(graph):
            node.status = "ready"
        return graph

    def build_cooperative_graph(
        self,
        *,
        run_id: str,
        objective: str,
        workspace: str | None = None,
        contract_type: str | None = "multi_agent_execution_graph",
        operation_type: str | None = "multi_agent_execution_graph",
        runtime_profile: str | None = "cooperative_graph",
        requested_actions: list[str] | None = None,
        requested_nodes: list[str] | None = None,
    ) -> ExecutionGraph:
        node_specs = self._cooperative_node_specs(objective, requested_nodes or [])
        nodes = [
            self._cooperative_node(
                node_id=spec["node_id"],
                executor=spec["executor"],
                objective=spec["objective"],
                runtime_profile=str(spec["runtime_profile"]),
                mode=str(spec["mode"]),
                dependencies=list(spec.get("dependencies", [])),
                capabilities=list(spec.get("capabilities", [])),
                output_contracts=list(spec.get("output_contracts", [])),
            )
            for spec in node_specs
        ]
        edges: list[ExecutionEdge] = []
        dependencies: list[ExecutionDependency] = []
        for node in nodes:
            for source_node_id in node.dependencies:
                edges.append(
                    ExecutionEdge(
                        from_node_id=source_node_id,
                        to_node_id=node.node_id,
                        reason="node_dependency",
                    )
                )
                dependencies.append(
                    ExecutionDependency(
                        source_node_id=source_node_id,
                        target_node_id=node.node_id,
                        output_contract=self._node_output_contract(source_node_id, nodes),
                    )
                )
        graph = ExecutionGraph(
            run_id=run_id,
            graph_type="cooperative",
            status="ready",
            context=ExecutionContext(
                run_id=run_id,
                workspace=workspace,
                contract_type=contract_type,
                operation_type=operation_type,
                runtime_profile=runtime_profile,
                requested_actions=list(requested_actions or []),
                evidence_refs=[{"type": "cooperative_graph_request", "ref_id": run_id}],
            ),
            nodes=nodes,
            edges=edges,
            dependencies=dependencies,
            checkpoints=[
                ExecutionCheckpoint(
                    status="ready",
                    summary="Cooperative ExecutionGraph created by AIpinho.",
                    evidence_refs=[{"type": "task_run", "ref_id": run_id}],
                )
            ],
            supervisor={
                "authority": "aipinho",
                "providers_can_create_nodes": False,
                "providers_can_finish_graph": False,
            },
            speakertruth={
                "node_output_validation": True,
                "graph_output_validation": True,
                "authority": "aipinho",
            },
        )
        if not self._is_acyclic(nodes, edges):
            graph.status = "blocked"
            graph.lifecycle.status = "blocked"
            graph.warnings.append("execution_graph_cycle_detected")
        else:
            graph.lifecycle.status = graph.status
            self._refresh_ready_nodes(graph)
        return graph

    def build_from_planning_report(
        self,
        *,
        run_id: str,
        planning_report: PlanningReport,
        workspace: str | None = None,
        contract_type: str | None = "multi_agent_execution_graph",
        operation_type: str | None = "multi_agent_execution_graph",
        runtime_profile: str | None = "cooperative_graph",
        requested_actions: list[str] | None = None,
    ) -> ExecutionGraph:
        nodes = [
            self._cooperative_node(
                node_id=node.node_id,
                executor=node.executor,
                objective=node.objective,
                runtime_profile=node.runtime_profile,
                mode=node.mode,
                dependencies=list(node.dependencies),
                capabilities=list(node.capabilities),
                output_contracts=list(node.output_contracts),
            )
            for node in planning_report.nodes
        ]
        node_meta = {node.node_id: node for node in planning_report.nodes}
        for graph_node in nodes:
            planned = node_meta.get(graph_node.node_id)
            if planned is None:
                continue
            graph_node.approval = {
                "required": planned.requires_approval,
                "risk_level": planned.risk_level,
            }
            graph_node.validation_gate.update(
                {
                    "planning_report_id": planning_report.report_id,
                    "requires_review": planned.requires_review,
                    "risk_level": planned.risk_level,
                }
            )
            graph_node.artifacts_expected = list(dict.fromkeys([*graph_node.artifacts_expected, *planned.expected_artifacts]))
        edges: list[ExecutionEdge] = []
        dependencies: list[ExecutionDependency] = []
        for node in nodes:
            for source_node_id in node.dependencies:
                edges.append(
                    ExecutionEdge(
                        from_node_id=source_node_id,
                        to_node_id=node.node_id,
                        reason="planner_dependency",
                    )
                )
                dependencies.append(
                    ExecutionDependency(
                        source_node_id=source_node_id,
                        target_node_id=node.node_id,
                        output_contract=self._node_output_contract(source_node_id, nodes),
                    )
                )
        graph = ExecutionGraph(
            run_id=run_id,
            graph_type="cooperative",
            status="ready" if planning_report.status == "ready" else "blocked",
            context=ExecutionContext(
                run_id=run_id,
                workspace=workspace,
                contract_type=contract_type,
                operation_type=operation_type,
                runtime_profile=runtime_profile,
                requested_actions=list(requested_actions or []),
                evidence_refs=[{"type": "planning_report", "ref_id": planning_report.report_id}],
            ),
            nodes=nodes,
            edges=edges,
            dependencies=dependencies,
            checkpoints=[
                ExecutionCheckpoint(
                    status=planning_report.status,
                    summary="ExecutionGraph created from Intelligent Planner strategy.",
                    evidence_refs=[{"type": "planning_report", "ref_id": planning_report.report_id}],
                )
            ],
            supervisor={
                "authority": "aipinho",
                "providers_can_create_nodes": False,
                "providers_can_finish_graph": False,
            },
            speakertruth={
                "node_output_validation": True,
                "graph_output_validation": True,
                "authority": "aipinho",
            },
            planning_report=planning_report.model_dump(mode="json"),
        )
        if not self._is_acyclic(nodes, edges):
            graph.status = "blocked"
            graph.lifecycle.status = "blocked"
            graph.warnings.append("execution_graph_cycle_detected")
        else:
            graph.lifecycle.status = graph.status
            self._refresh_ready_nodes(graph)
        return graph

    def poll_graph(self, graph: ExecutionGraph | None) -> ExecutionGraph | None:
        if graph is None:
            return None
        self._refresh_lifecycle(graph)
        self._refresh_ready_nodes(graph)
        graph.updated_at = utc_now()
        graph.checkpoints.append(
            ExecutionCheckpoint(
                status=graph.status,
                summary="ExecutionGraph polled from node runtime state.",
            )
        )
        return graph

    def mark_step_started(self, graph: ExecutionGraph | None, step_id: str) -> ExecutionGraph | None:
        if graph is None:
            return None
        node = self._find_step_node(graph, step_id)
        if node is None:
            return graph
        now = utc_now()
        graph.status = "running"
        graph.lifecycle.status = "running"
        graph.lifecycle.current_node_id = node.node_id
        graph.lifecycle.updated_at = now
        graph.metrics.started_at = graph.metrics.started_at or now
        node.status = "running"
        node.metrics.started_at = node.metrics.started_at or now
        node.metrics.attempts += 1
        graph.checkpoints.append(ExecutionCheckpoint(node_id=node.node_id, status="running", summary=f"Node {node.node_id} started."))
        graph.updated_at = now
        return graph

    def mark_node_started(self, graph: ExecutionGraph | None, node_id: str) -> ExecutionGraph | None:
        if graph is None:
            return None
        node = self._find_node(graph, node_id)
        if node is None:
            return graph
        now = utc_now()
        graph.status = "running"
        graph.lifecycle.status = "running"
        graph.lifecycle.current_node_id = node.node_id
        graph.lifecycle.updated_at = now
        graph.metrics.started_at = graph.metrics.started_at or now
        node.status = "running"
        node.metrics.started_at = node.metrics.started_at or now
        node.metrics.attempts += 1
        graph.checkpoints.append(ExecutionCheckpoint(node_id=node.node_id, status="running", summary=f"Node {node.node_id} started."))
        graph.updated_at = now
        return graph

    def mark_step_finished(
        self,
        graph: ExecutionGraph | None,
        step_id: str,
        *,
        status: str,
        output_summary: dict[str, Any] | None = None,
        warnings: list[str] | None = None,
        violations: list[str] | None = None,
    ) -> ExecutionGraph | None:
        if graph is None:
            return None
        node = self._find_step_node(graph, step_id)
        if node is None:
            return graph
        now = utc_now()
        node.status = self._node_status(status)
        node.output_summary = output_summary or {}
        node.warnings = list(dict.fromkeys(warnings or []))
        node.violations = list(dict.fromkeys(violations or []))
        node.metrics.finished_at = now
        node.metrics.warnings_count = len(node.warnings)
        node.metrics.violations_count = len(node.violations)
        graph.lifecycle.current_node_id = None
        self._refresh_lifecycle(graph)
        for ready in self.scheduler.ready_nodes(graph):
            ready.status = "ready"
        graph.checkpoints.append(
            ExecutionCheckpoint(
                node_id=node.node_id,
                status=node.status,
                summary=f"Node {node.node_id} finished with status {node.status}.",
            )
        )
        graph.updated_at = now
        return graph

    def mark_node_finished(
        self,
        graph: ExecutionGraph | None,
        node_id: str,
        *,
        status: str,
        outputs: dict[str, Any] | None = None,
        artifact_refs: list[dict[str, Any]] | None = None,
        memory_candidates: list[dict[str, Any]] | None = None,
        speakertruth: dict[str, Any] | None = None,
        review: dict[str, Any] | None = None,
        validation: dict[str, Any] | None = None,
        warnings: list[str] | None = None,
        violations: list[str] | None = None,
    ) -> ExecutionGraph | None:
        if graph is None:
            return None
        node = self._find_node(graph, node_id)
        if node is None:
            return graph
        now = utc_now()
        node.status = self._node_status(status)
        node.outputs = outputs or {}
        node.output_summary = outputs or {}
        node.artifacts = list(artifact_refs or [])
        node.memory_candidates = list(memory_candidates or [])
        node.speakertruth = speakertruth or {}
        node.review = review or {}
        node.warnings = list(dict.fromkeys(warnings or []))
        node.violations = list(dict.fromkeys(violations or []))
        node.metrics.finished_at = now
        node.metrics.warnings_count = len(node.warnings)
        node.metrics.violations_count = len(node.violations)
        if node.metrics.started_at:
            node.metrics.duration_ms = self._duration_ms(node.metrics.started_at, now)
        result = ExecutionResult(
            node_id=node.node_id,
            status=node.status,
            output_contract=self._node_output_contract(node.node_id, graph.nodes),
            outputs=node.outputs,
            artifact_refs=node.artifacts,
            memory_candidates=node.memory_candidates,
            evidence_refs=[{"type": "execution_node", "ref_id": node.node_id}],
            speakertruth=node.speakertruth,
            review=node.review,
            validation=validation or {},
        )
        graph.results.append(result)
        graph.artifacts.extend(node.artifacts)
        graph.memory_candidates.extend(node.memory_candidates)
        graph.lifecycle.current_node_id = None
        self._mark_edges_completed_from(graph, node.node_id)
        self._refresh_lifecycle(graph)
        self._refresh_ready_nodes(graph)
        graph.checkpoints.append(
            ExecutionCheckpoint(
                node_id=node.node_id,
                status=node.status,
                summary=f"Node {node.node_id} finished with status {node.status}.",
                evidence_refs=[{"type": "node_result", "ref_id": result.result_id}],
            )
        )
        graph.updated_at = now
        return graph

    def retry_node(self, graph: ExecutionGraph | None, node_id: str, *, reason: str = "retry_node_requested") -> ExecutionGraph | None:
        if graph is None:
            return None
        node = self._find_node(graph, node_id)
        if node is None:
            return graph
        node.retry_count += 1
        node.status = "pending"
        node.outputs = {}
        node.output_summary = {}
        node.artifacts = []
        node.memory_candidates = []
        node.speakertruth = {}
        node.review = {}
        node.warnings = []
        node.violations = []
        node.metrics.started_at = None
        node.metrics.finished_at = None
        for downstream_id in self._downstream_node_ids(graph, node_id):
            downstream = self._find_node(graph, downstream_id)
            if downstream is not None and downstream.status in {"ready", "waiting", "blocked", "failed", "completed", "partial"}:
                downstream.status = "pending"
        graph.checkpoints.append(ExecutionCheckpoint(node_id=node.node_id, status="pending", summary=reason))
        self._refresh_lifecycle(graph)
        self._refresh_ready_nodes(graph)
        graph.updated_at = utc_now()
        return graph

    def cancel_node(self, graph: ExecutionGraph | None, node_id: str, *, reason: str = "node_cancelled") -> ExecutionGraph | None:
        if graph is None:
            return None
        node = self._find_node(graph, node_id)
        if node is None:
            return graph
        node.status = "cancelled"
        node.violations = list(dict.fromkeys([*node.violations, reason]))
        for downstream_id in self._downstream_node_ids(graph, node_id):
            downstream = self._find_node(graph, downstream_id)
            if downstream is not None and downstream.status in {"pending", "ready", "waiting"}:
                downstream.status = "blocked"
                downstream.violations = list(dict.fromkeys([*downstream.violations, f"dependency_cancelled:{node_id}"]))
        graph.checkpoints.append(ExecutionCheckpoint(node_id=node.node_id, status="cancelled", summary=reason))
        self._refresh_lifecycle(graph)
        graph.updated_at = utc_now()
        return graph

    def mark_cancelled(self, graph: ExecutionGraph | None, reason: str) -> ExecutionGraph | None:
        if graph is None:
            return None
        for node in graph.nodes:
            if node.status in {"pending", "ready", "running"}:
                node.status = "cancelled"
        graph.status = "cancelled"
        graph.lifecycle.status = "cancelled"
        graph.lifecycle.cancelled_node_ids = [node.node_id for node in graph.nodes if node.status == "cancelled"]
        graph.checkpoints.append(ExecutionCheckpoint(status="cancelled", summary=reason))
        graph.updated_at = utc_now()
        return graph

    def resume(self, graph: ExecutionGraph | None) -> ExecutionResume | None:
        return self.scheduler.resume(graph) if graph is not None else None

    def _node_from_step(self, step: TaskRunStep, *, contract_type: str | None, capabilities_required: list[str]) -> ExecutionNode:
        worker_route = self.workers.route_step(step)
        capabilities = list(dict.fromkeys([*capabilities_required, *worker_route.capabilities]))
        artifacts_expected = list(dict.fromkeys([*self._artifacts_for_step(step), *worker_route.output_contracts]))
        return ExecutionNode(
            node_id=self.resolver.node_id(step),
            step_id=step.step_id,
            objective=f"Execute {step.step_type}",
            worker=worker_route.worker_id,
            executor=worker_route.worker_id,
            runtime_profile=step.step_type,
            runtime=NodeRuntime(
                profile=step.step_type,
                executor=worker_route.worker_id,
                allowed_capabilities=capabilities,
                execution_mode="supervised",
            ),
            capabilities=capabilities,
            contracts=[contract_type] if contract_type else [],
            artifacts_expected=artifacts_expected,
            validation_gate={
                "required": step.required,
                "action": step.action,
                "worker_route": worker_route.model_dump(mode="json"),
            },
            rollback={"strategy": "checkpoint_and_abort" if step.side_effect else "not_required"},
            action=step.action,
            side_effect=step.side_effect,
            required=step.required,
        )

    def _cooperative_node(
        self,
        *,
        node_id: str,
        executor: str,
        objective: str,
        runtime_profile: str,
        mode: str,
        dependencies: list[str],
        capabilities: list[str],
        output_contracts: list[str],
    ) -> ExecutionNode:
        return ExecutionNode(
            node_id=node_id,
            objective=objective,
            worker=executor,
            executor=executor,
            runtime_profile=runtime_profile,
            runtime=NodeRuntime(
                profile=runtime_profile,
                executor=executor,
                execution_mode=mode if mode in {"direct", "delegated", "supervised", "review", "memory", "finalizer"} else "supervised",
                allowed_capabilities=capabilities,
                poll_endpoint=None,
            ),
            dependencies=dependencies,
            capabilities=capabilities,
            contracts=output_contracts,
            artifacts_expected=output_contracts,
            validation_gate={
                "speakertruth_node_output": True,
                "speakertruth_graph_output": True,
                "output_contract_required": bool(output_contracts),
            },
            rollback={"strategy": "retry_node"},
            action=runtime_profile,
            side_effect=runtime_profile in {"executor", "debugger", "shell", "patch"},
            required=True,
        )

    def _cooperative_node_specs(self, objective: str, requested_nodes: list[str]) -> list[dict[str, Any]]:
        requested = {item.strip().casefold() for item in requested_nodes if item.strip()}
        text = objective.casefold()
        wants_visual = bool(requested & {"vision", "ocr"}) or any(marker in text for marker in ("android", "ui", "visual", "imagem", "screenshot", "tela", "ocr"))
        parallel_nodes = [
            {
                "node_id": "node_executor",
                "executor": "ExecutorWorker",
                "objective": "Execute the planned technical analysis or implementation through governed contracts.",
                "runtime_profile": "executor",
                "mode": "supervised",
                "dependencies": ["node_planner"],
                "capabilities": ["read_workspace", "write_via_contract", "artifact_generate"],
                "output_contracts": ["executor_result", "patch_or_analysis_artifact"],
            },
            {
                "node_id": "node_debugger",
                "executor": "DebuggerWorker",
                "objective": "Reproduce, inspect, or diagnose failures without bypassing policy.",
                "runtime_profile": "debugger",
                "mode": "supervised",
                "dependencies": ["node_planner"],
                "capabilities": ["read_workspace", "run_tests_with_approval"],
                "output_contracts": ["debugger_result"],
            },
        ]
        if wants_visual:
            parallel_nodes.extend(
                [
                    {
                        "node_id": "node_vision",
                        "executor": "VisionWorker",
                        "objective": "Analyze visual UI evidence and screenshots when available.",
                        "runtime_profile": "vision",
                        "mode": "supervised",
                        "dependencies": ["node_planner"],
                        "capabilities": ["vision_analysis"],
                        "output_contracts": ["vision_result"],
                    },
                    {
                        "node_id": "node_ocr",
                        "executor": "OCRWorker",
                        "objective": "Extract text from visual evidence when needed.",
                        "runtime_profile": "ocr",
                        "mode": "supervised",
                        "dependencies": ["node_planner"],
                        "capabilities": ["ocr"],
                        "output_contracts": ["ocr_result"],
                    },
                ]
            )
        review_dependencies = [item["node_id"] for item in parallel_nodes]
        return [
            {
                "node_id": "node_planner",
                "executor": "PlannerWorker",
                "objective": "Decompose the task into governed node contracts.",
                "runtime_profile": "planner",
                "mode": "supervised",
                "dependencies": [],
                "capabilities": ["planning", "policy_context"],
                "output_contracts": ["plan_result"],
            },
            *parallel_nodes,
            {
                "node_id": "node_review",
                "executor": "ReviewWorker",
                "objective": "Review all upstream outputs and request node retry when needed.",
                "runtime_profile": "review",
                "mode": "review",
                "dependencies": review_dependencies,
                "capabilities": ["review", "speaker_truth"],
                "output_contracts": ["review_result"],
            },
            {
                "node_id": "node_memory",
                "executor": "MemoryWorker",
                "objective": "Produce memory candidates without committing memory directly.",
                "runtime_profile": "memory",
                "mode": "memory",
                "dependencies": ["node_review"],
                "capabilities": ["memory_candidate"],
                "output_contracts": ["memory_candidates"],
            },
            {
                "node_id": "node_supervisor",
                "executor": "SupervisorWorker",
                "objective": "Validate graph truth and decide whether the graph can finish.",
                "runtime_profile": "supervisor",
                "mode": "review",
                "dependencies": ["node_review", "node_memory"],
                "capabilities": ["supervision", "speaker_truth"],
                "output_contracts": ["supervisor_result"],
            },
            {
                "node_id": "node_final",
                "executor": "AIpinho",
                "objective": "Publish the final governed answer only after graph validation.",
                "runtime_profile": "final_result",
                "mode": "finalizer",
                "dependencies": ["node_supervisor"],
                "capabilities": ["final_response"],
                "output_contracts": ["final_result"],
            },
        ]

    @staticmethod
    def _artifacts_for_step(step: TaskRunStep) -> list[str]:
        if "artifact" in step.action or "report" in step.action:
            return ["artifact_result"]
        if "validat" in step.action or "test" in step.action:
            return ["validation_result"]
        if step.side_effect:
            return [f"{step.action}_result"]
        return []

    @staticmethod
    def _find_step_node(graph: ExecutionGraph, step_id: str) -> ExecutionNode | None:
        for node in graph.nodes:
            if node.step_id == step_id:
                return node
        return None

    @staticmethod
    def _find_node(graph: ExecutionGraph, node_id: str) -> ExecutionNode | None:
        for node in graph.nodes:
            if node.node_id == node_id:
                return node
        return None

    @staticmethod
    def _node_status(value: str) -> str:
        return value if value in {"completed", "partial", "blocked", "failed", "cancelled", "skipped"} else "failed"

    def _refresh_lifecycle(self, graph: ExecutionGraph) -> None:
        graph.lifecycle.completed_node_ids = [node.node_id for node in graph.nodes if node.status in {"completed", "partial"}]
        graph.lifecycle.blocked_node_ids = [node.node_id for node in graph.nodes if node.status == "blocked"]
        graph.lifecycle.failed_node_ids = [node.node_id for node in graph.nodes if node.status == "failed"]
        graph.lifecycle.cancelled_node_ids = [node.node_id for node in graph.nodes if node.status == "cancelled"]
        if graph.lifecycle.blocked_node_ids:
            graph.status = "blocked"
        elif graph.lifecycle.failed_node_ids:
            graph.status = "failed"
        elif graph.lifecycle.cancelled_node_ids:
            graph.status = "cancelled"
        elif all(node.status in {"completed", "partial", "skipped"} for node in graph.nodes):
            graph.status = "completed"
            graph.metrics.finished_at = graph.metrics.finished_at or utc_now()
        elif any(node.status == "running" for node in graph.nodes):
            graph.status = "running"
        else:
            graph.status = "ready"
        graph.lifecycle.status = graph.status
        graph.lifecycle.updated_at = utc_now()

    def _refresh_ready_nodes(self, graph: ExecutionGraph) -> None:
        for node in self.scheduler.ready_nodes(graph):
            if node.status in {"pending", "waiting"}:
                node.status = "ready"
        for node in graph.nodes:
            if node.status == "pending" and node.dependencies:
                node.status = "waiting"

    def _mark_edges_completed_from(self, graph: ExecutionGraph, node_id: str) -> None:
        for dependency in graph.dependencies:
            if dependency.source_node_id == node_id:
                dependency.status = "completed"

    def _downstream_node_ids(self, graph: ExecutionGraph, node_id: str) -> list[str]:
        direct = [edge.to_node_id for edge in graph.edges if edge.from_node_id == node_id]
        seen: set[str] = set()
        stack = list(direct)
        while stack:
            current = stack.pop()
            if current in seen:
                continue
            seen.add(current)
            stack.extend(edge.to_node_id for edge in graph.edges if edge.from_node_id == current)
        return list(seen)

    @staticmethod
    def _node_output_contract(node_id: str, nodes: list[ExecutionNode]) -> str | None:
        for node in nodes:
            if node.node_id == node_id:
                return node.contracts[0] if node.contracts else None
        return None

    @staticmethod
    def _duration_ms(started_at: str, finished_at: str) -> int | None:
        try:
            from datetime import datetime

            start = datetime.fromisoformat(started_at)
            finish = datetime.fromisoformat(finished_at)
            return max(0, int((finish - start).total_seconds() * 1000))
        except Exception:
            return None

    @staticmethod
    def _is_acyclic(nodes: list[ExecutionNode], edges: list[ExecutionEdge]) -> bool:
        node_ids = {node.node_id for node in nodes}
        incoming = {node_id: 0 for node_id in node_ids}
        outgoing: dict[str, list[str]] = {node_id: [] for node_id in node_ids}
        for edge in edges:
            if edge.from_node_id not in node_ids or edge.to_node_id not in node_ids:
                return False
            incoming[edge.to_node_id] += 1
            outgoing[edge.from_node_id].append(edge.to_node_id)
        ready = [node_id for node_id, count in incoming.items() if count == 0]
        visited = 0
        while ready:
            node_id = ready.pop()
            visited += 1
            for target in outgoing[node_id]:
                incoming[target] -= 1
                if incoming[target] == 0:
                    ready.append(target)
        return visited == len(node_ids)
