from __future__ import annotations

import unicodedata
from typing import Any
from uuid import uuid4

from aipinho.core.paths import PATHS
from aipinho.schemas.runtime.intelligent_planner import (
    ExecutionConstraint,
    ExecutionStrategy,
    PlannerIntent,
    PlannerNode,
    PlannerReasoning,
    PlannerTask,
    PlanningEvidence,
    PlanningReport,
)
from aipinho.services.agents.agent_marketplace_service import AgentMarketplaceService
from aipinho.services.session.session_store import utc_now
from aipinho.utils.yaml_loader import load_yaml_file


class PlanningEngine:
    def __init__(self, policy: dict[str, Any], cost_policy: dict[str, Any], review_policy: dict[str, Any]) -> None:
        self.policy = policy
        self.cost_policy = cost_policy
        self.review_policy = review_policy

    def infer_intent(
        self,
        *,
        objective: str,
        requested_actions: list[str],
        requested_nodes: list[str],
    ) -> PlannerIntent:
        task_type = self._task_type(objective, requested_actions, requested_nodes)
        complexity = "high" if task_type in {"android", "multimodal"} else ("medium" if task_type in {"python", "coding", "debug", "ocr", "vision"} else "low")
        requires_approval = bool(set(self._normalize_actions(requested_actions)).intersection(self._side_effect_actions()))
        return PlannerIntent(
            objective=objective,
            task_type=task_type,
            complexity=complexity,
            requires_graph=True,
            requires_review=(
                bool(self.policy.get("planning", {}).get("default_review_required", True))
                or task_type in set(self.review_policy.get("review", {}).get("required_for", []) or [])
                or task_type != "simple"
            ),
            requires_approval=requires_approval,
            evidence_refs=[{"type": "planner_policy", "ref_id": "config/runtime/planning_policy.yaml"}],
        )

    def _task_type(self, objective: str, requested_actions: list[str], requested_nodes: list[str]) -> str:
        text = self._normalize(" ".join([objective, *requested_actions, *requested_nodes]))
        markers = self.policy.get("task_type_markers", {}) if isinstance(self.policy.get("task_type_markers", {}), dict) else {}
        priority = ("android", "multimodal", "ocr", "vision", "python", "debug", "coding", "review", "artifact")
        for task_type in priority:
            values = markers.get(task_type, []) if isinstance(markers.get(task_type, []), list) else []
            if any(self._normalize(str(marker)) in text for marker in values):
                return task_type
        return "simple"

    @staticmethod
    def _normalize(value: str) -> str:
        decomposed = unicodedata.normalize("NFKD", value.casefold())
        return "".join(ch for ch in decomposed if not unicodedata.combining(ch))

    @staticmethod
    def _normalize_actions(actions: list[str]) -> list[str]:
        return [PlanningEngine._normalize(str(action)).replace("-", "_") for action in actions]

    def _side_effect_actions(self) -> set[str]:
        risk = self.cost_policy.get("risk_actions", {}) if isinstance(self.cost_policy.get("risk_actions", {}), dict) else {}
        return {str(item) for values in risk.values() for item in (values or [])}


class TaskDecomposer:
    def __init__(self, policy: dict[str, Any], cost_policy: dict[str, Any]) -> None:
        self.policy = policy
        self.cost_policy = cost_policy
        self.marketplace = AgentMarketplaceService()

    def decompose(self, *, intent: PlannerIntent, task: PlannerTask, requested_nodes: list[str]) -> list[PlannerNode]:
        requested = self._requested_node_ids(requested_nodes)
        task_type = intent.task_type
        parallel = ["node_executor"]
        if task_type in {"android", "python", "debug", "coding"} or requested.intersection({"node_debugger"}):
            parallel.append("node_debugger")
        if task_type in {"android", "multimodal", "vision"} or requested.intersection({"node_vision"}):
            parallel.append("node_vision")
        if task_type in {"android", "multimodal", "ocr"} or requested.intersection({"node_ocr"}):
            parallel.append("node_ocr")
        parallel = list(dict.fromkeys([*parallel, *[node for node in requested if node in {"node_executor", "node_debugger", "node_vision", "node_ocr"}]]))
        nodes = [
            self._node(
                "node_planner",
                self._executor_for("planning"),
                "planner",
                "Decompose the task into a policy-aware execution strategy.",
                [],
                ["planning", "policy_context"],
                ["plan_result"],
                "supervised",
                "planning",
                "low",
                False,
            )
        ]
        nodes.extend(self._parallel_node(node_id, intent=intent, task=task) for node_id in parallel)
        nodes.extend(
            [
                self._node(
                    "node_review",
                    self._executor_for("review"),
                    "review",
                    "Review all upstream node outputs and request precise node retries when needed.",
                    parallel,
                    ["review", "speaker_truth"],
                    ["review_result"],
                    "review",
                    "review",
                    intent.requires_approval and "medium" or "low",
                    False,
                ),
                self._node(
                    "node_memory",
                    self._executor_for("memory_candidate"),
                    "memory",
                    "Produce memory candidates; AIpinho decides what is committed.",
                    ["node_review"],
                    ["memory_candidate"],
                    ["memory_candidates"],
                    "memory",
                    "memory",
                    "low",
                    False,
                ),
                self._node(
                    "node_supervisor",
                    self._executor_for("supervision"),
                    "supervisor",
                    "Validate graph truth, policy consistency, and completion evidence.",
                    ["node_review", "node_memory"],
                    ["supervision", "speaker_truth"],
                    ["supervisor_result"],
                    "review",
                    "supervision",
                    "low",
                    False,
                ),
                self._node(
                    "node_final",
                    self._executor_for("final_response"),
                    "final_result",
                    "Publish the final governed answer only after graph validation.",
                    ["node_supervisor"],
                    ["final_response"],
                    ["final_result"],
                    "finalizer",
                    "final",
                    "low",
                    False,
                ),
            ]
        )
        return nodes

    def _parallel_node(self, node_id: str, *, intent: PlannerIntent, task: PlannerTask) -> PlannerNode:
        specs = {
            "node_executor": (
                self._executor_capability_for(intent),
                "executor",
                "Execute governed technical analysis or implementation through output contracts.",
                ["read_workspace", "write_via_contract", "artifact_generate"],
                ["executor_result", "patch_or_analysis_artifact"],
                intent.requires_approval,
            ),
            "node_debugger": (
                "run_tests_with_approval",
                "debugger",
                "Reproduce or diagnose failures with governed tests/build evidence.",
                ["read_workspace", "run_tests_with_approval"],
                ["debugger_result"],
                intent.requires_approval or bool(set(task.requested_actions).intersection({"run_command", "build", "test"})),
            ),
            "node_vision": (
                "vision_analysis",
                "vision",
                "Analyze visual UI evidence and screenshots when available.",
                ["vision_analysis"],
                ["vision_result"],
                False,
            ),
            "node_ocr": (
                "ocr",
                "ocr",
                "Extract text from visual evidence when needed.",
                ["ocr"],
                ["ocr_result"],
                False,
            ),
        }
        executor_capability, profile, objective, capabilities, outputs, approval = specs[node_id]
        return self._node(
            node_id,
            self._executor_for(executor_capability),
            profile,
            objective,
            ["node_planner"],
            capabilities,
            outputs,
            "supervised",
            "analysis",
            self._risk_for_node(profile, intent.requires_approval),
            approval,
        )

    def _node(
        self,
        node_id: str,
        executor: str,
        runtime_profile: str,
        objective: str,
        dependencies: list[str],
        capabilities: list[str],
        output_contracts: list[str],
        mode: str,
        parallel_group: str,
        risk_level: str,
        requires_approval: bool,
    ) -> PlannerNode:
        costs = self.cost_policy.get("node_costs", {}) if isinstance(self.cost_policy.get("node_costs", {}), dict) else {}
        return PlannerNode(
            node_id=node_id,
            executor=executor,
            runtime_profile=runtime_profile,
            objective=objective,
            dependencies=dependencies,
            capabilities=capabilities,
            output_contracts=output_contracts,
            mode=mode,  # type: ignore[arg-type]
            parallel_group=parallel_group,
            requires_review=runtime_profile not in {"final_result"},
            requires_approval=requires_approval,
            risk_level=risk_level,  # type: ignore[arg-type]
            expected_artifacts=list(output_contracts),
            estimated_cost=int(costs.get(runtime_profile, 1)),
        )

    def _requested_node_ids(self, requested_nodes: list[str]) -> set[str]:
        aliases = self.policy.get("requested_node_aliases", {}) if isinstance(self.policy.get("requested_node_aliases", {}), dict) else {}
        values: set[str] = set()
        for item in requested_nodes:
            key = PlanningEngine._normalize(str(item)).replace(" ", "_")
            values.add(str(aliases.get(key) or key))
        return values

    def _executor_for(self, capability_id: str) -> str:
        selected = self.marketplace.select_agent_for_capability(capability_id)
        return selected.agent_id if selected else f"capability:{capability_id}"

    @staticmethod
    def _executor_capability_for(intent: PlannerIntent) -> str:
        if intent.task_type in {"android", "python", "coding"}:
            return "coding"
        return "technical_analysis"

    @staticmethod
    def _risk_for_node(runtime_profile: str, requires_approval: bool) -> str:
        if runtime_profile in {"executor", "debugger"} and requires_approval:
            return "medium"
        return "low"


class ExecutionStrategyBuilder:
    def build(self, *, intent: PlannerIntent, nodes: list[PlannerNode]) -> ExecutionStrategy:
        analysis_group = [node.node_id for node in nodes if node.parallel_group == "analysis"]
        risk_levels = {node.risk_level for node in nodes}
        risk = "high" if "high" in risk_levels else ("medium" if "medium" in risk_levels or intent.requires_approval else "low")
        discarded = [
            "single_linear_workflow: discarded because independent analysis nodes can run in parallel",
            "provider_owned_graph: discarded because AIpinho remains graph authority",
        ]
        return ExecutionStrategy(
            name="risk_aware_adaptive_graph",
            summary=f"Adaptive {intent.task_type} task graph with AIpinho-owned planning, review, supervisor, and finalization.",
            parallel_groups=[analysis_group] if analysis_group else [],
            review_required=intent.requires_review,
            approval_required=intent.requires_approval,
            risk_level=risk,  # type: ignore[arg-type]
            estimated_steps=len(nodes),
            discarded_alternatives=discarded,
        )


class PlannerDependencyResolver:
    def dependencies(self, nodes: list[PlannerNode]) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        for node in nodes:
            for dep in node.dependencies:
                items.append(
                    {
                        "source_node_id": dep,
                        "target_node_id": node.node_id,
                        "reason": "planner_dependency",
                        "output_contract": self._output_contract(dep, nodes),
                    }
                )
        return items

    @staticmethod
    def _output_contract(node_id: str, nodes: list[PlannerNode]) -> str | None:
        for node in nodes:
            if node.node_id == node_id:
                return node.output_contracts[0] if node.output_contracts else None
        return None


class GraphOptimizer:
    def order(self, nodes: list[PlannerNode]) -> list[str]:
        ordered: list[str] = []
        pending = {node.node_id: node for node in nodes}
        while pending:
            progressed = False
            for node_id, node in list(pending.items()):
                if all(dep in ordered for dep in node.dependencies):
                    ordered.append(node_id)
                    pending.pop(node_id)
                    progressed = True
            if not progressed:
                ordered.extend(sorted(pending))
                break
        return ordered


class RiskAwarePlanner:
    def constraints(self, *, intent: PlannerIntent, nodes: list[PlannerNode], raw_constraints: dict[str, Any]) -> list[ExecutionConstraint]:
        constraints: list[ExecutionConstraint] = []
        for group in raw_constraints.get("constraints", {}).values() if isinstance(raw_constraints.get("constraints", {}), dict) else []:
            for item in group or []:
                if isinstance(item, dict):
                    constraints.append(
                        ExecutionConstraint(
                            kind=str(item.get("kind") or "policy"),
                            summary=str(item.get("summary") or ""),
                            applies_to=[str(value) for value in item.get("applies_to", []) or []],
                            blocking=bool(item.get("blocking", False)),
                        )
                    )
        if intent.requires_approval:
            risky_nodes = [node.node_id for node in nodes if node.requires_approval]
            constraints.append(
                ExecutionConstraint(
                    kind="approval_gate",
                    summary="Side-effect capable nodes require approval before runtime execution.",
                    applies_to=risky_nodes,
                    blocking=False,
                )
            )
        return constraints


class IntelligentPlannerService:
    CONFIG_NAMES = (
        "planning_policy.yaml",
        "planning_constraints.yaml",
        "planning_cost_policy.yaml",
        "planning_parallel_policy.yaml",
        "planning_review_policy.yaml",
    )

    def __init__(self) -> None:
        root = PATHS.config_root / "runtime"
        self.policy = load_yaml_file(root / "planning_policy.yaml", critical=True, root=root)
        self.constraints_policy = load_yaml_file(root / "planning_constraints.yaml", critical=True, root=root)
        self.cost_policy = load_yaml_file(root / "planning_cost_policy.yaml", critical=True, root=root)
        self.parallel_policy = load_yaml_file(root / "planning_parallel_policy.yaml", critical=True, root=root)
        self.review_policy = load_yaml_file(root / "planning_review_policy.yaml", critical=True, root=root)
        self.engine = PlanningEngine(self.policy, self.cost_policy, self.review_policy)
        self.decomposer = TaskDecomposer(self.policy, self.cost_policy)
        self.strategy_builder = ExecutionStrategyBuilder()
        self.dependencies = PlannerDependencyResolver()
        self.optimizer = GraphOptimizer()
        self.risk = RiskAwarePlanner()

    def plan(
        self,
        *,
        objective: str,
        workspace: str | None = None,
        contract_type: str | None = None,
        operation_type: str | None = None,
        runtime_profile: str | None = None,
        requested_actions: list[str] | None = None,
        requested_capabilities: list[str] | None = None,
        requested_nodes: list[str] | None = None,
        policy_snapshot: dict[str, Any] | None = None,
    ) -> PlanningReport:
        actions = list(requested_actions or [])
        capabilities = list(requested_capabilities or [])
        node_hints = list(requested_nodes or [])
        intent = self.engine.infer_intent(objective=objective, requested_actions=actions, requested_nodes=node_hints)
        evidence = [
            PlanningEvidence(
                kind="objective",
                summary=f"Task classified as {intent.task_type} with {intent.complexity} complexity.",
            ),
            PlanningEvidence(
                kind="runtime_context",
                summary=f"operation={operation_type or '-'} contract={contract_type or '-'} profile={runtime_profile or '-'}",
            ),
        ]
        task = PlannerTask(
            objective=objective,
            workspace=workspace,
            stack_hint=intent.task_type,
            requested_actions=actions,
            requested_capabilities=capabilities,
            constraints=["policy_governed", "speaker_truth_required", "provider_graph_mutation_forbidden"],
            policy_snapshot=policy_snapshot or {},
        )
        nodes = self.decomposer.decompose(intent=intent, task=task, requested_nodes=node_hints)
        strategy = self.strategy_builder.build(intent=intent, nodes=nodes)
        dependencies = self.dependencies.dependencies(nodes)
        constraints = self.risk.constraints(intent=intent, nodes=nodes, raw_constraints=self.constraints_policy)
        order = self.optimizer.order(nodes)
        reasoning = [
            PlannerReasoning(
                question="O problema pode ser dividido?",
                answer="Sim. O planner separou planejamento, execucao/analise paralela, review, memoria, supervisao e resposta final.",
                evidence_ids=[evidence[0].evidence_id],
            ),
            PlannerReasoning(
                question="Quais especialistas serao usados?",
                answer=", ".join(dict.fromkeys(node.executor for node in nodes)),
                evidence_ids=[evidence[0].evidence_id],
            ),
            PlannerReasoning(
                question="Quais nos podem executar em paralelo?",
                answer=", ".join(strategy.parallel_groups[0]) if strategy.parallel_groups else "Nenhum grupo paralelo necessario.",
                evidence_ids=[evidence[0].evidence_id],
            ),
            PlannerReasoning(
                question="Existe aprovacao obrigatoria?",
                answer="Sim." if strategy.approval_required else "Nao antes de uma acao com side effect concreta.",
                evidence_ids=[evidence[1].evidence_id],
            ),
        ]
        return PlanningReport(
            objective=objective,
            intent=intent,
            task=task,
            strategy=strategy,
            nodes=nodes,
            constraints=constraints,
            reasoning=reasoning,
            evidence=evidence,
            risks=self._risks(strategy, nodes),
            dependencies=dependencies,
            order=order,
            alternatives_discarded=strategy.discarded_alternatives,
        )

    def replan_after_node_failure(self, report: PlanningReport, *, failed_node_id: str, reason: str) -> PlanningReport:
        data = report.model_dump()
        data["report_id"] = f"planning_report_{uuid4().hex}"
        data["replan_of"] = report.report_id
        data["replan_reason"] = reason
        data["created_at"] = utc_now()
        data["strategy"]["strategy_id"] = f"execution_strategy_{uuid4().hex}"
        data["strategy"]["summary"] = f"Replan focused on node {failed_node_id}: {reason}"
        data["reasoning"].append(
            {
                "question": "Como recuperar a falha?",
                "answer": f"Retry/replan apenas do node {failed_node_id} e dos dependentes, preservando outputs upstream validos.",
                "evidence_ids": [],
            }
        )
        data["risks"] = list(dict.fromkeys([*data.get("risks", []), f"node_replan:{failed_node_id}"]))
        return PlanningReport(**data)

    @staticmethod
    def _risks(strategy: ExecutionStrategy, nodes: list[PlannerNode]) -> list[str]:
        risks = [f"risk_level:{strategy.risk_level}"]
        if strategy.approval_required:
            risks.append("approval_required_before_side_effect")
        if any(node.runtime_profile in {"vision", "ocr"} for node in nodes):
            risks.append("visual_evidence_may_be_missing")
        return risks

    def status(self) -> dict[str, Any]:
        return {
            "status": "ok",
            "service": "intelligent_planner",
            "configs": list(self.CONFIG_NAMES),
            "planning_enabled": bool(self.policy.get("planning", {}).get("enabled", False)),
        }
