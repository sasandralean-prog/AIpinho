from __future__ import annotations

from aipinho.schemas.mobile_view_models import (
    MobilePipelineViewModel,
    MobileScreenState,
    MobileTaskQueueSummary,
)
from aipinho.services.approvals.approval_service import ApprovalService
from aipinho.services.mobile_view_models.mobile_card_builder import MobileCardBuilder
from aipinho.services.mobile_view_models.mobile_evidence_mapper import MobileEvidenceMapper
from aipinho.services.mobile_view_models.mobile_safe_action_builder import MobileSafeActionBuilder
from aipinho.services.mobile_view_models.mobile_status_precedence_service import MobileStatusPrecedenceService
from aipinho.services.runtime.task_run_lifecycle_service import TaskRunLifecycleService
from aipinho.services.runtime.task_runtime_service import TaskRuntimeService
from aipinho.services.runtime.universal_task_session_service import UniversalTaskSessionService


class PipelineMobileAggregator:
    def __init__(
        self,
        approvals: ApprovalService | None = None,
        task_runtime: TaskRuntimeService | None = None,
    ) -> None:
        self.cards = MobileCardBuilder()
        self.evidence = MobileEvidenceMapper()
        self.actions = MobileSafeActionBuilder()
        self.approvals = approvals or ApprovalService()
        self.task_runtime = task_runtime or TaskRuntimeService()
        self.lifecycle = getattr(self.task_runtime, "lifecycle", TaskRunLifecycleService())
        self.status_precedence = MobileStatusPrecedenceService()
        self.universal_sessions = UniversalTaskSessionService(
            store=getattr(self.task_runtime, "store", None),
            approvals=self.approvals,
        )

    def view_model(self, task_id: str | None = None) -> MobilePipelineViewModel:
        queue = self._queue_snapshot()
        pending_approvals = self._pending_approvals()
        task_approvals, standalone_approvals = self._split_pending_approvals(pending_approvals)
        run = self._resolve_run(task_id, queue)
        universal_session = self._universal_session(run)
        planning_report = self._planning_report_summary(run)
        execution_graph = self._execution_graph_summary(run)
        task_ref = run.run_id if run is not None else None
        external_collaboration = self._external_collaboration_summary(task_ref)
        approval = self._selected_approval(run, standalone_approvals)
        linked_task_run_id = self._linked_task_run_id(approval)
        approval_kind = self._approval_kind(approval, linked_task_run_id=linked_task_run_id)
        visual_status = self._visual_status(getattr(run, "status", None), approval is not None)
        intent_label = self._intent_label(run)
        planned_actions = self._planned_actions(run)
        required_permissions = self._required_permissions(run, approval)
        task_happening = (
            f"A task selecionada esta {self._status_label(run.status)}. "
            f"Objetivo: {intent_label}."
            if run is not None
            else "Nao ha task correspondente ao filtro atual."
        )
        task_why = (
            f"Plano previsto: {planned_actions}. "
            f"Permissoes pendentes: {required_permissions}."
            if run is not None
            else "O campo de task permanece vazio ate existir uma task elegivel."
        )
        approval_metadata = {"apply_direct": False}
        approval_evidence = []
        approval_actions = ["Atualizar pipeline."]
        approval_status = "completed"
        approval_severity = "info"
        approval_happening = "Nenhum pedido de aprovacao esta pendente."
        if approval is not None:
            approval_metadata.update({
                "approval_id": approval.approval_id,
                "preview_id": approval.preview_id,
                "approval_status": approval.status,
                "actions_requested": list(approval.actions_requested),
                "approval_kind": approval_kind,
                "linked_task_run_id": linked_task_run_id,
                "operation_type": approval.operation_type,
                "risk_level": approval.risk_level,
            })
            approval_evidence = [
                self.evidence.ref("approval", approval.approval_id, "approval ledger"),
            ]
            approval_actions = ["Revisar pedido.", "Aprovar.", "Negar."]
            approval_status = approval.status
            approval_severity = "warning"
            approval_happening = "Existe um pedido de aprovacao pendente para decisao humana."
        task_state_evidence = (
            [self.evidence.ref("task_run", task_ref, "task runtime")]
            if task_ref
            else []
        )
        patch_evidence = (
            [self.evidence.ref("task_run", task_ref, "task run patch state")]
            if task_ref
            else []
        )
        validation_evidence = (
            [self.evidence.ref("validation", task_ref, "task validation state")]
            if task_ref
            else []
        )
        skill_evidence = (
            [self.evidence.ref("skill_trace", task_ref, "task skill trace")]
            if task_ref
            else []
        )
        task_safety, task_safety_reason = self._task_safety(run, approval)
        cards = [
            self.cards.card(
                card_id="pipeline_task_state",
                screen="pipeline",
                card_type="task_state",
                title="Task State",
                status=visual_status,
                severity="info",
                happening=task_happening,
                why=task_why,
                safety=task_safety,
                safety_reason=task_safety_reason,
                actions=["Atualizar task.", "Abrir timeline.", "Copiar resumo."],
                evidence=task_state_evidence,
                metadata={
                    "task_id": task_ref,
                        "queue_total": queue.total_visible if queue is not None else int(run is not None),
                    "queue_requires_decision": queue.requires_decision_count if queue is not None else int(approval is not None),
                    "selected_task_id": task_ref,
                    "selected_approval_id": approval.approval_id if approval is not None else None,
                    "approval_kind": approval_kind,
                    "linked_task_run_id": linked_task_run_id,
                    "task_approvals_pending": len(task_approvals),
                    "standalone_approvals_pending": len(standalone_approvals),
                    "intent": intent_label,
                    "planned_actions": planned_actions,
                    "required_permissions": required_permissions,
                    "universal_task_session": universal_session,
                    "universal_task_session_endpoint": f"/api/v1/task_runs/{task_ref}" if task_ref else None,
                    "universal_task_events_endpoint": f"/api/v1/task_runs/{task_ref}/events" if task_ref else None,
                    "universal_task_artifacts_endpoint": f"/api/v1/task_runs/{task_ref}/artifacts" if task_ref else None,
                    "planning_report": planning_report,
                    "planning_report_endpoint": f"/api/v1/task-runs/{task_ref}/planning/report" if task_ref else None,
                    "execution_graph": execution_graph,
                    "execution_graph_endpoint": f"/api/v1/task-runs/{task_ref}/execution-graph" if task_ref else None,
                    "execution_graph_poll_endpoint": f"/api/v1/task-runs/{task_ref}/execution-graph/poll" if task_ref else None,
                    "external_collaboration": external_collaboration,
                    "external_collaboration_endpoint": f"/api/v1/external/collaboration-sessions?task_run_id={task_ref}" if task_ref else None,
                    **self._block_metadata(run),
                },
                safe_actions=[self.actions.refresh("pipeline")],
            ),
            self.cards.card(
                card_id="pipeline_execution_plan",
                screen="pipeline",
                card_type="execution_plan",
                title="Execution Plan",
                status=self._card_status(planning_report.get("status")),
                severity="info",
                happening=self._planning_happening(planning_report),
                why="O Planning Engine decompoe a task em nodes, dependencias, custo, risco e revisoes antes do runtime.",
                safety="caution" if planning_report.get("risk_level") in {"medium", "high"} else "safe",
                safety_reason="O plano vem da Universal Task Session; a UI nao inventa estrategia nem progresso.",
                actions=["Abrir plano.", "Abrir dependencias.", "Copiar estrategia."],
                evidence=(
                    [self.evidence.ref("planning_report", str(planning_report.get("report_id")), "intelligent planner")]
                    if planning_report.get("report_id")
                    else []
                ),
                metadata={
                    "planning_report": planning_report,
                    "planning_report_endpoint": f"/api/v1/task-runs/{task_ref}/planning/report" if task_ref else None,
                },
            ),
            self.cards.card(
                card_id="pipeline_execution_graph",
                screen="pipeline",
                card_type="execution_graph",
                title="Execution Graph",
                status=self._card_status(execution_graph.get("status")),
                severity="info",
                happening=self._graph_happening(execution_graph),
                why="Cada node publica output contract; retries e cancelamentos atuam no node, nao na task inteira.",
                safety="caution" if execution_graph.get("blocked_nodes") else "safe",
                safety_reason="Provider externo nao cria nem finaliza nodes; a autoridade do grafo e AIpinho.",
                actions=["Poll graph.", "Abrir node details.", "Retry node.", "Cancelar node."],
                evidence=(
                    [self.evidence.ref("execution_graph", str(execution_graph.get("graph_id")), "cooperative execution graph")]
                    if execution_graph.get("graph_id")
                    else []
                ),
                metadata={
                    "execution_graph": execution_graph,
                    "retry_node_endpoint_template": f"/api/v1/task-runs/{task_ref}/execution-graph/nodes/{{node_id}}/retry" if task_ref else None,
                    "cancel_node_endpoint_template": f"/api/v1/task-runs/{task_ref}/execution-graph/nodes/{{node_id}}/cancel" if task_ref else None,
                },
            ),
            self.cards.card(
                card_id="pipeline_approval",
                screen="pipeline",
                card_type="approval",
                title="Approval Preview",
                status=approval_status,
                severity=approval_severity,
                happening=approval_happening,
                why="Escrita, artifact e patch exigem preview/approval conforme policy.",
                safety="caution" if approval is not None else "safe",
                safety_reason="Aprovar e side effect; o mobile mostra preview, nao aplica sozinho.",
                actions=approval_actions,
                evidence=approval_evidence,
                metadata=approval_metadata,
                safe_actions=[],
            ),
            self.cards.card(
                card_id="pipeline_patch_preview",
                screen="pipeline",
                card_type="patch_preview",
                title="Patch Preview / Quality",
                status="blocked",
                severity="blocked",
                happening="Patch aparece apenas como preview/risk/quality/evidence.",
                why="Patch apply direto nao e uma SafeUiAction no mobile.",
                safety="blocked",
                safety_reason="Aplicacao de patch exige pipeline oficial, approval e validation.",
                actions=["Ver diff sanitizado.", "Ver risk.", "Ver quality gate."],
                evidence=patch_evidence,
                metadata={"direct_apply_visible": False},
            ),
            self.cards.card(
                card_id="pipeline_validation",
                screen="pipeline",
                card_type="validation",
                title="Validation",
                status=visual_status,
                severity="info",
                happening="Validation mostra plano, resultado e traces.",
                why="Sucesso depende do Success Contract, nao apenas de patch.",
                safety=task_safety,
                safety_reason=task_safety_reason,
                actions=["Abrir resultado.", "Copiar validation summary."],
                evidence=validation_evidence,
                metadata={"success_contract_aware": True, **self._block_metadata(run)},
            ),
            self.cards.card(
                card_id="pipeline_skill_permission",
                screen="pipeline",
                card_type="skill_permission",
                title="Skill/Tool Permission",
                status="blocked",
                severity="warning",
                happening="Skills/tools aparecem como preview/dry-run e permissoes.",
                why="Allowed/forbidden tools sao definidos pelo backend policy.",
                safety="caution",
                safety_reason="Tool real perigosa permanece bloqueada sem approval.",
                actions=["Abrir skill trace.", "Copiar bloqueios."],
                evidence=skill_evidence,
                metadata={"ui_decides_policy": False},
            ),
        ]
        return MobilePipelineViewModel(
            state=MobileScreenState(
                screen="pipeline",
                status=visual_status,
                human_summary="Pipeline humano carregado com task state, approval, patch preview, validation e skills.",
            ),
            cards=cards,
            task_id=task_ref,
            selected_task_id=task_ref,
            selected_approval_id=approval.approval_id if approval is not None else None,
            approval_kind=approval_kind,
            linked_task_run_id=linked_task_run_id,
            task_approvals_pending=len(task_approvals),
            standalone_approvals_pending=len(standalone_approvals),
            queue=MobileTaskQueueSummary(
                total=queue.total_visible if queue is not None else int(run is not None),
                active=queue.active_count if queue is not None else int(getattr(run, "status", None) == "running"),
                pending=queue.pending_count if queue is not None else int(run is not None),
                requires_decision=queue.requires_decision_count if queue is not None else int(approval is not None),
                max_pending=queue.max_pending_tasks if queue is not None else 0,
                selected_task_id=task_ref,
                selected_approval_id=approval.approval_id if approval is not None else None,
                approval_kind=approval_kind,
                linked_task_run_id=linked_task_run_id,
                task_approvals_pending=len(task_approvals),
                standalone_approvals_pending=len(standalone_approvals),
            ),
            trace_id="mobile_vm_pipeline",
        )

    def _resolve_run(self, task_id: str | None, queue):
        if task_id == "active":
            if queue is None:
                return None
            active = next((item for item in queue.items if item.status == "running"), None)
            return self.task_runtime.get_run(active.run_id) if active is not None else None
        if task_id:
            try:
                run = self.task_runtime.get_run(task_id)
            except ValueError:
                return None
            return run
        if queue is not None and queue.items:
            return self.task_runtime.get_run(queue.items[0].run_id)
        return self.task_runtime.get_active_run()

    def _universal_session(self, run) -> dict:
        if run is None:
            return {}
        try:
            session = self.universal_sessions.get_session(run.run_id)
        except Exception:
            return {"status": "unavailable", "source": "universal_task_session"}
        return session.model_dump() if session is not None else {}

    @staticmethod
    def _execution_graph_summary(run) -> dict:
        graph = getattr(run, "execution_graph", None) if run is not None else None
        if graph is None:
            return {"status": "none", "nodes": [], "edges": [], "source": "task_run.execution_graph"}
        nodes = []
        for node in getattr(graph, "nodes", []) or []:
            nodes.append({
                "node_id": node.node_id,
                "executor": getattr(node, "executor", None) or getattr(node, "worker", ""),
                "runtime_profile": getattr(node, "runtime_profile", None) or getattr(node, "action", ""),
                "status": node.status,
                "dependencies": list(getattr(node, "dependencies", []) or []),
                "retry_count": getattr(node, "retry_count", 0),
                "artifacts": list(getattr(node, "artifacts", []) or []),
                "memory_candidates": list(getattr(node, "memory_candidates", []) or []),
                "speakertruth": getattr(node, "speakertruth", {}) or {},
                "review": getattr(node, "review", {}) or {},
            })
        edges = [
            {
                "from": edge.from_node_id,
                "to": edge.to_node_id,
                "reason": edge.reason,
                "required": edge.required,
            }
            for edge in getattr(graph, "edges", []) or []
        ]
        return {
            "graph_id": graph.graph_id,
            "graph_type": getattr(graph, "graph_type", "task_plan"),
            "status": graph.status,
            "nodes": nodes,
            "edges": edges,
            "ready_nodes": [node["node_id"] for node in nodes if node["status"] == "ready"],
            "running_nodes": [node["node_id"] for node in nodes if node["status"] == "running"],
            "completed_nodes": list(getattr(graph.lifecycle, "completed_node_ids", []) or []),
            "blocked_nodes": list(getattr(graph.lifecycle, "blocked_node_ids", []) or []),
            "failed_nodes": list(getattr(graph.lifecycle, "failed_node_ids", []) or []),
            "artifacts": list(getattr(graph, "artifacts", []) or []),
            "memory_candidates": list(getattr(graph, "memory_candidates", []) or []),
            "speakertruth": getattr(graph, "speakertruth", {}) or {},
            "review": getattr(graph, "review", {}) or {},
            "source": "task_run.execution_graph",
        }

    @staticmethod
    def _planning_report_summary(run) -> dict:
        if run is None:
            return {"status": "none", "nodes": [], "source": "task_run.intent_map.planning_report"}
        intent_map = getattr(run, "intent_map", {}) if isinstance(getattr(run, "intent_map", {}), dict) else {}
        report = intent_map.get("planning_report")
        if not isinstance(report, dict):
            graph = getattr(run, "execution_graph", None)
            report = getattr(graph, "planning_report", None) if graph is not None else None
        if not isinstance(report, dict):
            return {"status": "none", "nodes": [], "source": "task_run.intent_map.planning_report"}
        strategy = report.get("strategy") if isinstance(report.get("strategy"), dict) else {}
        intent = report.get("intent") if isinstance(report.get("intent"), dict) else {}
        nodes = report.get("nodes") if isinstance(report.get("nodes"), list) else []
        dependencies = report.get("dependencies") if isinstance(report.get("dependencies"), list) else []
        return {
            "report_id": report.get("report_id"),
            "status": report.get("status", "ready"),
            "objective": report.get("objective"),
            "task_type": intent.get("task_type"),
            "complexity": intent.get("complexity"),
            "strategy": strategy.get("name"),
            "strategy_summary": strategy.get("summary"),
            "risk_level": strategy.get("risk_level"),
            "estimated_steps": strategy.get("estimated_steps"),
            "approval_required": strategy.get("approval_required"),
            "review_required": strategy.get("review_required"),
            "parallel_groups": strategy.get("parallel_groups") if isinstance(strategy.get("parallel_groups"), list) else [],
            "nodes": [
                {
                    "node_id": item.get("node_id"),
                    "executor": item.get("executor"),
                    "runtime_profile": item.get("runtime_profile"),
                    "dependencies": item.get("dependencies") if isinstance(item.get("dependencies"), list) else [],
                    "capabilities": item.get("capabilities") if isinstance(item.get("capabilities"), list) else [],
                    "risk_level": item.get("risk_level"),
                    "requires_approval": item.get("requires_approval"),
                    "estimated_cost": item.get("estimated_cost"),
                }
                for item in nodes
                if isinstance(item, dict)
            ],
            "dependencies": dependencies,
            "risks": report.get("risks") if isinstance(report.get("risks"), list) else [],
            "order": report.get("order") if isinstance(report.get("order"), list) else [],
            "alternatives_discarded": report.get("alternatives_discarded") if isinstance(report.get("alternatives_discarded"), list) else [],
            "replan_of": report.get("replan_of"),
            "replan_reason": report.get("replan_reason"),
            "source": "task_run.intent_map.planning_report",
        }

    @staticmethod
    def _planning_happening(planning_report: dict) -> str:
        if not planning_report or planning_report.get("status") == "none":
            return "Nenhum plano inteligente selecionado."
        return (
            f"Plano {planning_report.get('report_id')} para {planning_report.get('task_type') or 'task'} "
            f"com {len(planning_report.get('nodes') or [])} nodes, risco {planning_report.get('risk_level') or '-'} "
            f"e estrategia {planning_report.get('strategy') or '-'}."
        )

    @staticmethod
    def _graph_happening(execution_graph: dict) -> str:
        if not execution_graph or execution_graph.get("status") == "none":
            return "Nenhum Execution Graph selecionado."
        nodes = execution_graph.get("nodes") if isinstance(execution_graph.get("nodes"), list) else []
        counts: dict[str, int] = {}
        for node in nodes:
            status = str(node.get("status") or "unknown") if isinstance(node, dict) else "unknown"
            counts[status] = counts.get(status, 0) + 1
        parts = [f"{status}: {count}" for status, count in sorted(counts.items())]
        return f"Graph {execution_graph.get('graph_id')} status {execution_graph.get('status')}. " + ", ".join(parts)

    @staticmethod
    def _external_collaboration_summary(task_ref: str | None) -> dict:
        if not task_ref:
            return {"status": "none", "count": 0, "sessions": [], "source": "continuous_collaboration_runtime"}
        try:
            from aipinho.services.external_collaboration_service import ExternalCollaborationService

            sessions = ExternalCollaborationService().list_continuous_sessions(task_run_id=task_ref, limit=25)
        except Exception:
            return {"status": "unavailable", "count": 0, "sessions": [], "source": "continuous_collaboration_runtime"}
        items = []
        for session in sessions:
            retry_state = getattr(session, "retry_state", {}) or {}
            items.append({
                "session_id": session.session_id,
                "provider": session.provider,
                "status": session.status,
                "review_iteration": session.review_iteration,
                "retry_count": session.retry_count,
                "retry_strategy": retry_state.get("strategy") or "",
                "retry_reason": retry_state.get("reason") or "",
                "last_activity": session.last_activity,
                "last_evaluation_id": session.last_evaluation_id,
                "success_contract_id": session.success_contract_id,
                "endpoint": f"/api/v1/external/collaboration-sessions/{session.session_id}",
                "poll_endpoint": f"/api/v1/external/collaboration-sessions/{session.session_id}/poll",
            })
        active = [item for item in items if item["status"] not in {"completed", "cancelled", "expired"}]
        return {
            "status": "active" if active else ("none" if not items else "completed"),
            "count": len(items),
            "active_count": len(active),
            "sessions": items,
            "source": "continuous_collaboration_runtime",
        }

    def _queue_snapshot(self):
        queue_status = getattr(self.task_runtime, "queue_status", None)
        if not callable(queue_status):
            return None
        try:
            return queue_status().snapshot
        except Exception:
            return None

    def _pending_approvals(self):
        try:
            return self.approvals.list_approvals(status="pending", limit=500)
        except Exception:
            return []

    @staticmethod
    def _split_pending_approvals(approvals):
        task_approvals = []
        standalone_approvals = []
        for approval in approvals or []:
            if getattr(approval, "run_id", None) or getattr(approval, "task_id", None):
                task_approvals.append(approval)
            else:
                standalone_approvals.append(approval)
        return task_approvals, standalone_approvals

    def _selected_approval(self, run, standalone_approvals):
        linked = self._pending_approval(run)
        if linked is not None:
            return linked
        if run is None and standalone_approvals:
            return standalone_approvals[0]
        return None

    @staticmethod
    def _linked_task_run_id(approval) -> str | None:
        if approval is None:
            return None
        return getattr(approval, "run_id", None) or getattr(approval, "task_id", None)

    @staticmethod
    def _approval_kind(approval, *, linked_task_run_id: str | None) -> str | None:
        if approval is None:
            return None
        scope = str(getattr(approval, "approval_scope", "") or "").strip()
        operation = str(getattr(approval, "operation_type", "") or "").strip()
        if linked_task_run_id:
            return "task_approval"
        return scope or operation or "standalone_approval"

    def _pending_approval(self, run):
        approval_id = getattr(run, "approval_id", None) if run is not None else None
        if not approval_id:
            return None
        approval = self.approvals.get_approval(approval_id)
        return approval if approval is not None and approval.status == "pending" else None

    @staticmethod
    def _intent_label(run) -> str:
        if run is None:
            return "nenhuma"
        intent_map = getattr(run, "intent_map", {})
        intent = intent_map if isinstance(intent_map, dict) else {}
        value = (
            intent.get("overall_intent")
            or intent.get("primary_intent")
            or intent.get("intent_type")
            or getattr(run, "contract_type", "nao informado")
        )
        return str(value).replace("_", " ").strip() or "nao informado"

    @staticmethod
    def _planned_actions(run) -> str:
        if run is None:
            return "nenhuma"
        actions = [
            str(step.action).replace("_", " ")
            for step in getattr(getattr(run, "plan", None), "steps", [])
            if step.required
        ]
        if not actions:
            actions = [
                str(item).replace("_", " ")
                for item in getattr(run, "requested_actions", [])
            ]
        return ", ".join(dict.fromkeys(actions)) if actions else "nenhuma acao operacional"

    @staticmethod
    def _required_permissions(run, approval) -> str:
        if approval is not None:
            actions = [str(item).replace("_", " ") for item in approval.actions_requested]
            return ", ".join(actions) if actions else "decisao humana"
        if run is None:
            return "nenhuma"
        policy_snapshot = getattr(run, "policy_snapshot", {})
        policy = policy_snapshot if isinstance(policy_snapshot, dict) else {}
        actions = [
            str(item).replace("_", " ")
            for item in policy.get("approval_required_for", []) or []
        ]
        return ", ".join(actions) if actions else "nenhuma"

    @staticmethod
    def _status_label(status: str) -> str:
        return {
            "created": "criada e aguardando inicio",
            "queued": "na fila para execucao",
            "running": "em execucao",
            "waiting_input": "aguardando permissao",
            "completed": "concluida",
            "partial": "concluida parcialmente",
            "failed": "com falha",
            "cancelled": "cancelada",
            "blocked": "bloqueada",
            "expired": "expirada",
        }.get(status, status.replace("_", " "))

    def _visual_status(self, status: str | None, approval_pending: bool = False) -> str:
        signals = [status]
        if approval_pending:
            signals.append("pending_approval")
        return self.status_precedence.resolve(signals)

    @staticmethod
    def _card_status(value: object) -> str:
        text = str(value or "").strip().lower()
        allowed = {
            "healthy",
            "degraded",
            "offline",
            "blocked",
            "pending",
            "running",
            "completed",
            "failed",
            "historical",
            "unknown",
        }
        return text if text in allowed else "unknown"

    @staticmethod
    def _block_metadata(run) -> dict:
        cause = getattr(run, "block_cause", None) if run is not None else None
        if cause is None:
            return {}
        return {
            "block_id": cause.block_id,
            "blocked_stage": cause.blocked_stage,
            "block_reason_code": cause.block_reason_code,
            "human_reason": cause.human_reason,
            "approval_status": cause.approval_status or "",
            "validation_status": cause.validation_status or "",
            "trace_id": cause.trace_id or "",
        }

    @staticmethod
    def _task_safety(run, approval) -> tuple[str, str]:
        if run is None:
            return "safe", "Nao ha task selecionada."
        if approval is not None or run.status == "waiting_input":
            return "caution", "Aguardando aprovacao humana antes de continuar."
        if run.status == "blocked":
            cause = getattr(run, "block_cause", None)
            stage = getattr(cause, "blocked_stage", "policy")
            return "blocked", f"Bloqueado por {str(stage).replace('_', ' ')}."
        if run.status == "failed":
            return "risky", "Falha operacional; consulte o trace e a validacao."
        if run.status == "completed":
            return "safe", "Task concluida; consulte o resultado de validacao."
        return "caution", "Task em andamento ou aguardando reconciliacao."
