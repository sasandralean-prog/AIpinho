from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, ClassVar

from aipinho.core.paths import PATHS
from aipinho.schemas.agents.contracts import AgentEvent, AgentRun
from aipinho.schemas.artifacts.artifact_interaction_contracts import ArtifactUploadRequest
from aipinho.schemas.events.contracts import utc_now_iso
from aipinho.schemas.multi_agent_observability import (
    DebugBundleExportRequest,
    DebugBundleExportResponse,
    DebuggerEventsResponse,
    DebuggerEventView,
    MultiAgentDashboard,
    MultiAgentStatusItem,
    ObservabilityCard,
    StateConsistencyIssue,
    StateConsistencyReport,
    TraceGraphEdge,
    TraceGraphNode,
    TraceGraphResponse,
)
from aipinho.services.agents.agent_delegation_store import AgentDelegationStore
from aipinho.services.agents.agent_profile_registry_service import AgentProfileRegistryService
from aipinho.services.agents.agent_session_store import AgentSessionStore
from aipinho.services.agents.agent_tool_invocation_store import AgentToolInvocationStore
from aipinho.services.agents.agent_tool_registry_service import AgentToolRegistryService
from aipinho.services.agents.multi_agent_policy_audit_store import MultiAgentPolicyAuditStore
from aipinho.services.artifacts.artifact_interaction_core import ArtifactRegistryRepository, ArtifactUploadService
from aipinho.services.events.event_core import redact_payload
from aipinho.services.supervisor.backend_control_service import BackendControlService
from aipinho.utils.yaml_loader import load_yaml_file


TERMINAL_STATUSES = {"completed", "completed_with_warnings", "failed", "blocked", "cancelled", "validation_failed"}
ACTIVE_STATUSES = {"created", "running", "pending_approval", "pending_validation", "delegation_running", "waiting_child_run", "applying"}
FAILURE_STATUSES = {"failed", "validation_failed"}
BLOCKED_STATUSES = {"blocked", "policy_denied"}
DELEGATION_TERMINAL_STATUSES = {"completed", "completed_with_warnings", "blocked", "failed", "cancelled", "timed_out", "rejected"}
TOOL_INVOCATION_TERMINAL_STATUSES = {"succeeded", "succeeded_with_warnings", "blocked", "failed", "cancelled"}


def _dump(value: Any) -> dict[str, Any]:
    if hasattr(value, "model_dump"):
        return value.model_dump()
    if hasattr(value, "dict"):
        return value.dict()
    if isinstance(value, dict):
        return value
    return {"value": value}


class MultiAgentObservabilityService:
    _dashboard_cache: ClassVar[dict[tuple[str, ...], tuple[float, MultiAgentDashboard]]] = {}

    def __init__(
        self,
        *,
        sessions: AgentSessionStore | None = None,
        profiles: AgentProfileRegistryService | None = None,
        delegations: AgentDelegationStore | None = None,
        tools: AgentToolInvocationStore | None = None,
        tool_registry: AgentToolRegistryService | None = None,
        policy_audit: MultiAgentPolicyAuditStore | None = None,
        artifact_registry: ArtifactRegistryRepository | None = None,
        backend_control: BackendControlService | None = None,
    ) -> None:
        self.sessions = sessions or AgentSessionStore()
        self.profiles = profiles or AgentProfileRegistryService()
        self.delegations = delegations or AgentDelegationStore()
        self.tools = tools or AgentToolInvocationStore()
        self.tool_registry = tool_registry or AgentToolRegistryService()
        self.policy_audit = policy_audit or MultiAgentPolicyAuditStore()
        self.artifact_registry = artifact_registry or ArtifactRegistryRepository()
        self.backend_control = backend_control or BackendControlService()

    def dashboard(self) -> MultiAgentDashboard:
        cache_key = self._dashboard_cache_key()
        cached = self._dashboard_cache.get(cache_key)
        ttl_seconds = self._dashboard_cache_ttl_seconds()
        started = time.monotonic()
        if cached and ttl_seconds > 0 and started - cached[0] <= ttl_seconds:
            return cached[1]
        backend = self._safe_backend_status()
        sessions = self.sessions.list_sessions()
        runs = self.sessions.list_runs()
        events = self._all_events(include_hidden=True)
        delegations = self.delegations.list_requests()
        invocations = self.tools.list_invocations()
        policies = self.policy_audit.list_policy_decisions()
        auto_approvals = self.policy_audit.list_auto_approvals()
        tool_artifacts = [artifact.model_dump() for artifact in self.tools.list_artifacts(include_all=True)[:50]]
        chat_artifacts = [artifact.model_dump() for artifact in self.artifact_registry.list()[-50:]]
        active_runs = [self._run_summary(run) for run in runs if self._run_effective_status(run, events) in ACTIVE_STATUSES]
        active_delegations = [self._delegation_summary(item) for item in delegations if item.status in {"created", "accepted", "running", "approval_required"}]
        pending_approvals = self._pending_approvals(runs, events, policies)
        blocks = [self._run_summary(run) for run in runs if self._run_effective_status(run, events) in BLOCKED_STATUSES]
        failures = [self._run_summary(run) for run in runs if self._run_effective_status(run, events) in FAILURE_STATUSES]
        agent_items = self._agent_items(runs, events)
        consistency = self.state_consistency()
        self_healing_status = self._self_healing_status()
        warnings = [issue.summary for issue in consistency.issues if issue.severity in {"warning", "danger", "critical"}]
        cards = self._dashboard_cards(
            backend_status=str(backend.get("status", "unknown")),
            agents=agent_items,
            active_runs=active_runs,
            active_delegations=active_delegations,
            pending_approvals=pending_approvals,
            failures=failures,
            blocks=blocks,
            consistency=consistency,
            policy_count=len(policies),
            tool_count=len(invocations),
            artifact_count=len(tool_artifacts) + len(chat_artifacts),
            self_healing_status=self_healing_status,
        )
        dashboard = MultiAgentDashboard(
            backend_status=str(backend.get("status", "unknown")),
            ports={
                "core_backend": backend.get("backend_port"),
                "control": backend.get("control_port"),
                "exclusive_control_port": backend.get("exclusive_control_port", True),
            },
            agents=agent_items,
            active_runs=active_runs,
            active_delegations=active_delegations,
            pending_approvals=pending_approvals,
            auto_approvals=[item.model_dump() for item in auto_approvals[:50]],
            blocks=blocks,
            failures=failures,
            validations=self._validation_summaries(runs, events),
            artifacts=tool_artifacts + chat_artifacts,
            reports=self._report_summaries(),
            memory={"status": "observable", "source": "agent_memory_gateway", "raw_default_visible": False},
            self_healing=self_healing_status,
            policy={
                "decisions": len(policies),
                "auto_approvals": len(auto_approvals),
                "denied": len([item for item in policies if item.decision == "deny"]),
                "approval_required": len([item for item in policies if item.decision == "require_approval"]),
            },
            tool_gateway={
                "registry": self._safe_tool_registry_status(),
                "invocations": len(invocations),
                "running": len([item for item in invocations if item.status == "running"]),
                "blocked": len([item for item in invocations if item.status == "blocked"]),
            },
            event_bus={
                "events": len(events),
                "visible": len([event for event in events if event.visible_in_timeline]),
                "hidden": len([event for event in events if not event.visible_in_timeline]),
            },
            warnings=warnings,
            safe_actions=self._dashboard_safe_actions(),
            cards=cards,
        )
        if ttl_seconds > 0:
            self._dashboard_cache[cache_key] = (time.monotonic(), dashboard)
        return dashboard

    def _dashboard_cache_key(self) -> tuple[str, ...]:
        return (
            str(self.sessions.root),
            str(self.delegations.root),
            str(self.tools.root),
            str(self.policy_audit.root),
            str(self.artifact_registry.path),
        )

    def _dashboard_cache_ttl_seconds(self) -> float:
        config = load_yaml_file(PATHS.config_root / "runtime" / "multi_agent_observability_policy.yaml", critical=False, root=PATHS.config_root)
        cache = config.get("dashboard_cache", {}) if isinstance(config, dict) else {}
        try:
            return max(0.0, min(float(cache.get("ttl_seconds", 5)), 60.0))
        except (TypeError, ValueError):
            return 5.0

    def health(self) -> dict[str, Any]:
        dashboard = self.dashboard()
        status = "degraded" if dashboard.warnings else "ok"
        return {
            "status": status,
            "backend_status": dashboard.backend_status,
            "agents": len(dashboard.agents),
            "active_runs": len(dashboard.active_runs),
            "pending_approvals": len(dashboard.pending_approvals),
            "warnings": dashboard.warnings,
            "raw_default_visible": False,
        }

    def state_consistency(self) -> StateConsistencyReport:
        runs = self.sessions.list_runs()
        events = self._all_events(include_hidden=True)
        delegations = self.delegations.list_requests()
        invocations = self.tools.list_invocations()
        policies = self.policy_audit.list_policy_decisions()
        issues: list[StateConsistencyIssue] = []
        events_by_run = self._events_by_run(events)
        runs_by_id = {run.run_id: run for run in runs}
        policy_by_tool = {policy.tool_invocation_id: policy for policy in policies if policy.tool_invocation_id}

        for run in runs:
            run_events = events_by_run.get(run.run_id, [])
            status = self._run_effective_status(run, events)
            if status in ACTIVE_STATUSES and not run_events:
                issues.append(self._issue("active_run_without_events", "warning", "run", run.run_id, "Run ativo sem eventos rastreaveis.", [f"run:{run.run_id}"]))
            if run.status in {"completed", "completed_with_warnings"} and not (run.final_message_id or run.artifact_ids or run.validation_status or run_events):
                issues.append(self._issue("completed_without_evidence", "warning", "run", run.run_id, "Run concluido sem evidencia suficiente.", [f"run:{run.run_id}"]))
            if run.status in {"completed", "completed_with_warnings"} and any(event.status == "validation_failed" for event in run_events):
                issues.append(self._issue("validation_failed_but_run_completed", "danger", "run", run.run_id, "Run concluido apesar de evento de validation_failed.", [f"run:{run.run_id}"]))

        for event in events:
            if event.run_id not in runs_by_id:
                issues.append(self._issue("event_without_run", "warning", "event", event.event_id, "Evento aponta para run ausente.", [f"event:{event.event_id}", f"run:{event.run_id}"]))

        for delegation in delegations:
            missing_ref_severity = "info" if delegation.status in DELEGATION_TERMINAL_STATUSES else "warning"
            if delegation.child_run_id and delegation.child_run_id not in runs_by_id:
                issues.append(self._issue("delegation_without_child_run", missing_ref_severity, "delegation", delegation.delegation_id, "Delegacao aponta para child_run ausente.", [f"delegation:{delegation.delegation_id}"]))
            if delegation.parent_run_id not in runs_by_id:
                issues.append(self._issue("delegation_without_parent_run", missing_ref_severity, "delegation", delegation.delegation_id, "Delegacao aponta para parent_run ausente.", [f"delegation:{delegation.delegation_id}"]))

        for invocation in invocations:
            if invocation.run_id not in runs_by_id:
                missing_ref_severity = "info" if invocation.status in TOOL_INVOCATION_TERMINAL_STATUSES else "warning"
                issues.append(self._issue("tool_without_run", missing_ref_severity, "tool_invocation", invocation.tool_invocation_id, "Tool invocation aponta para run ausente.", [f"tool:{invocation.tool_invocation_id}"]))
            if invocation.policy_decision_id and invocation.tool_invocation_id not in policy_by_tool:
                issues.append(self._issue("tool_without_policy_decision", "warning", "tool_invocation", invocation.tool_invocation_id, "Tool invocation declara policy_decision_id sem decisao auditavel.", [f"tool:{invocation.tool_invocation_id}"]))

        counts: dict[str, int] = {}
        for issue in issues:
            counts[issue.issue_type] = counts.get(issue.issue_type, 0) + 1
        status = "ok" if not any(issue.severity in {"warning", "danger", "critical"} for issue in issues) else ("blocked" if any(issue.severity in {"danger", "critical"} for issue in issues) else "degraded")
        return StateConsistencyReport(status=status, issues=issues, counts=counts)

    def debugger_events(
        self,
        *,
        agent_id: str | None = None,
        session_id: str | None = None,
        run_id: str | None = None,
        event_type: str | None = None,
        status: str | None = None,
        severity: str | None = None,
        text: str | None = None,
        cursor: str | None = None,
        limit: int = 200,
        include_hidden: bool = False,
        mode: str = "normal",
        **refs: str | None,
    ) -> DebuggerEventsResponse:
        include = include_hidden or mode in {"details", "raw_debug", "raw"}
        events = [self._event_view(event) for event in self._all_events(include_hidden=include)]
        events.extend(self._policy_event_views(self.policy_audit.list_policy_decisions()))
        events.extend(self._tool_event_views(self.tools.list_invocations()))
        events.extend(self._self_healing_event_views())
        filtered = []
        for event in events:
            if agent_id and event.agent_id != agent_id:
                continue
            if session_id and event.session_id != session_id:
                continue
            if run_id and event.run_id != run_id:
                continue
            if event_type and event.event_type != event_type:
                continue
            if status and event.status != status:
                continue
            if severity and event.severity != severity:
                continue
            if text and text.lower() not in f"{event.human_message} {event.event_type} {event.payload_sanitized}".lower():
                continue
            if not self._refs_match(event.refs, refs):
                continue
            filtered.append(event)
        filtered = sorted(filtered, key=lambda item: item.created_at or "", reverse=True)
        if cursor:
            filtered = self._after_cursor(filtered, cursor)
        selected = filtered[: max(1, min(limit, 500))]
        next_cursor = selected[-1].event_id if len(filtered) > len(selected) and selected else None
        return DebuggerEventsResponse(
            events=selected,
            next_cursor=next_cursor,
            has_more=next_cursor is not None,
            filters_applied=redact_payload({
                "agent_id": agent_id,
                "session_id": session_id,
                "run_id": run_id,
                "event_type": event_type,
                "status": status,
                "severity": severity,
                "cursor": cursor,
                "include_hidden": include_hidden,
                "mode": mode,
                **{key: value for key, value in refs.items() if value},
            }),
        )

    def trace_graph(self, run_id: str) -> TraceGraphResponse:
        run = self.sessions.get_run(run_id)
        if run is None:
            raise FileNotFoundError(run_id)
        events = [self._event_view(event) for event in self.sessions.list_events(run_id, include_hidden=True, limit=100000)]
        nodes: list[TraceGraphNode] = [
            TraceGraphNode(node_id=f"session:{run.session_id}", node_type="session", label=f"Sessao {run.session_id}", refs={"session_id": run.session_id}),
            TraceGraphNode(node_id=f"run:{run.run_id}", node_type="run", label=f"Run {run.operation_type}", status=run.status, refs={"run_id": run.run_id, "agent_id": run.agent_id}),
        ]
        edges = [TraceGraphEdge(source=f"session:{run.session_id}", target=f"run:{run.run_id}", relation="owns")]
        if run.parent_run_id:
            nodes.append(TraceGraphNode(node_id=f"run:{run.parent_run_id}", node_type="parent_run", label="Parent run", refs={"run_id": run.parent_run_id}))
            edges.append(TraceGraphEdge(source=f"run:{run.parent_run_id}", target=f"run:{run.run_id}", relation="parent_of"))
        if run.delegation_id:
            nodes.append(TraceGraphNode(node_id=f"delegation:{run.delegation_id}", node_type="delegation", label="Delegacao", refs={"delegation_id": run.delegation_id}))
            edges.append(TraceGraphEdge(source=f"delegation:{run.delegation_id}", target=f"run:{run.run_id}", relation="created_child_run"))
        for event in events:
            nodes.append(TraceGraphNode(node_id=f"event:{event.event_id}", node_type="event", label=event.event_type, status=event.status, severity=event.severity, refs={"event_id": event.event_id}))
            edges.append(TraceGraphEdge(source=f"run:{run.run_id}", target=f"event:{event.event_id}", relation="emits"))
            for ref_key in ("tool_invocation_id", "policy_decision_id", "approval_id", "validation_id", "artifact_id", "delegation_id"):
                ref_value = event.refs.get(ref_key)
                if ref_value:
                    nodes.append(TraceGraphNode(node_id=f"{ref_key}:{ref_value}", node_type=ref_key, label=ref_key.replace("_", " "), refs={ref_key: ref_value}))
                    edges.append(TraceGraphEdge(source=f"event:{event.event_id}", target=f"{ref_key}:{ref_value}", relation="references"))
        for invocation in self.tools.list_invocations(run_id=run_id):
            nodes.append(TraceGraphNode(node_id=f"tool:{invocation.tool_invocation_id}", node_type="tool_invocation", label=invocation.tool_name, status=invocation.status, refs={"tool_invocation_id": invocation.tool_invocation_id}))
            edges.append(TraceGraphEdge(source=f"run:{run.run_id}", target=f"tool:{invocation.tool_invocation_id}", relation="uses_tool"))
            if invocation.policy_decision_id:
                nodes.append(TraceGraphNode(node_id=f"policy:{invocation.policy_decision_id}", node_type="policy_decision", label="Policy decision", refs={"policy_decision_id": invocation.policy_decision_id}))
                edges.append(TraceGraphEdge(source=f"tool:{invocation.tool_invocation_id}", target=f"policy:{invocation.policy_decision_id}", relation="checked_by"))
        return self._dedupe_trace(TraceGraphResponse(run_id=run_id, nodes=nodes, edges=edges, events=events))

    def entity(self, entity_type: str, entity_id: str) -> dict[str, Any]:
        if entity_type == "run":
            run = self.sessions.get_run(entity_id)
            if run is None:
                raise FileNotFoundError(entity_id)
            return {"entity_type": entity_type, "entity": run.model_dump(), "events": [self._event_view(event).model_dump() for event in self.sessions.list_events(entity_id, include_hidden=True, limit=100000)]}
        if entity_type == "session":
            sessions = [session for session in self.sessions.list_sessions(include_deleted=True) if session.session_id == entity_id]
            if not sessions:
                raise FileNotFoundError(entity_id)
            session = sessions[0]
            return {"entity_type": entity_type, "entity": session.model_dump(), "messages": [message.model_dump() for message in self.sessions.list_messages(session.agent_id, entity_id, limit=200)]}
        if entity_type == "agent":
            profile = self.profiles.get(entity_id)
            if profile is None:
                raise FileNotFoundError(entity_id)
            return {"entity_type": entity_type, "entity": profile.model_dump()}
        if entity_type == "delegation":
            delegation = self.delegations.get_request(entity_id)
            if delegation is None:
                raise FileNotFoundError(entity_id)
            return {"entity_type": entity_type, "entity": delegation.model_dump(), "policy_decision": _dump(self.delegations.get_policy_decision(entity_id)) if self.delegations.get_policy_decision(entity_id) else None, "result": _dump(self.delegations.get_result(entity_id)) if self.delegations.get_result(entity_id) else None}
        if entity_type == "tool_invocation":
            invocation = self.tools.get_invocation(entity_id)
            if invocation is None:
                raise FileNotFoundError(entity_id)
            return {"entity_type": entity_type, "entity": invocation.model_dump()}
        if entity_type == "policy_decision":
            decision = self.policy_audit.get_policy_decision(entity_id)
            if decision is None:
                raise FileNotFoundError(entity_id)
            return {"entity_type": entity_type, "entity": decision.model_dump()}
        if entity_type == "artifact":
            artifact = self.tools.get_artifact(entity_id) or self.artifact_registry.get(entity_id)
            if artifact is None:
                raise FileNotFoundError(entity_id)
            return {"entity_type": entity_type, "entity": _dump(artifact)}
        raise ValueError("unsupported_entity_type")

    def export_debug_bundle(self, request: DebugBundleExportRequest) -> DebugBundleExportResponse:
        payload: dict[str, Any] = {"generated_at": utc_now_iso(), "filters": request.model_dump()}
        if request.include_dashboard:
            payload["dashboard"] = self.dashboard().model_dump()
        if request.include_consistency:
            payload["state_consistency"] = self.state_consistency().model_dump()
        if request.include_events:
            payload["events"] = self.debugger_events(
                agent_id=request.agent_id,
                session_id=request.session_id,
                run_id=request.run_id,
                include_hidden=True,
                mode="details",
                limit=500,
            ).model_dump()
        if request.include_trace and request.run_id:
            payload["trace"] = self.trace_graph(request.run_id).model_dump()
        safe_payload = redact_payload(payload)
        filename = f"multi_agent_debug_bundle_{utc_now_iso().replace(':', '').replace('-', '').split('.')[0]}.json"
        upload = ArtifactUploadService().upload(ArtifactUploadRequest(
            filename=filename,
            content=json.dumps(safe_payload, indent=2, ensure_ascii=True),
            content_type="application/json",
            metadata={"source": "multi_agent_debugger", "sanitized": True},
        ))
        return DebugBundleExportResponse(
            status="ok",
            artifact_id=upload.artifact.artifact_id,
            filename=upload.artifact.filename,
            download_endpoint=upload.download_path,
            summary="Debug bundle sanitizado gerado como artifact protegido por token.",
        )

    def filters(self) -> dict[str, Any]:
        return {
            "status": "ok",
            "filters": {
                "agent_id": [profile.agent_id for profile in self.profiles.list_profiles()],
                "status": sorted(ACTIVE_STATUSES | TERMINAL_STATUSES | BLOCKED_STATUSES | FAILURE_STATUSES),
                "severity": ["info", "success", "warning", "error", "danger", "blocked"],
                "event_type": sorted({event.event_type for event in self._all_events(include_hidden=True)}),
                "entity_type": ["agent", "session", "run", "delegation", "tool_invocation", "policy_decision", "artifact"],
            },
            "raw_default_visible": False,
        }

    def _safe_backend_status(self) -> dict[str, Any]:
        try:
            return self.backend_control.status().model_dump()
        except Exception as exc:
            return {"status": "unknown", "human_message": f"Backend control indisponivel: {exc.__class__.__name__}"}

    def _safe_tool_registry_status(self) -> dict[str, Any]:
        try:
            return self.tool_registry.status().model_dump()
        except Exception as exc:
            return {"status": "degraded", "error": exc.__class__.__name__}

    def _all_events(self, *, include_hidden: bool) -> list[AgentEvent]:
        events: list[AgentEvent] = []
        if not self.sessions.events_dir.exists():
            return events
        for path in self.sessions.events_dir.glob("*.jsonl"):
            try:
                events.extend(self.sessions.list_events(path.stem, include_hidden=include_hidden, limit=100000))
            except Exception:
                continue
        return sorted(events, key=lambda event: event.created_at, reverse=True)

    def _agent_items(self, runs: list[AgentRun], events: list[AgentEvent]) -> list[MultiAgentStatusItem]:
        items: list[MultiAgentStatusItem] = []
        sessions = self.sessions.list_sessions()
        for profile in self.profiles.list_profiles():
            agent_runs = [run for run in runs if run.agent_id == profile.agent_id]
            agent_events = [event for event in events if event.agent_id == profile.agent_id]
            selected = sorted(agent_runs, key=lambda run: run.started_at, reverse=True)[:1]
            active = next((run for run in selected if self._run_effective_status(run, agent_events) in ACTIVE_STATUSES), None)
            pending = len([run for run in agent_runs if self._run_effective_status(run, agent_events) == "pending_approval"])
            warnings = [event.human_message for event in agent_events[:5] if event.severity in {"warning", "error", "danger", "blocked"}]
            status = self._run_effective_status(active, agent_events) if active else ("idle" if not agent_runs else self._run_effective_status(selected[0], agent_events))
            items.append(MultiAgentStatusItem(
                agent_id=profile.agent_id,
                display_name=profile.display_name,
                status=status,
                session_count=len([session for session in sessions if session.agent_id == profile.agent_id]),
                run_count=len(agent_runs),
                active_run_id=active.run_id if active else None,
                pending_approvals=pending,
                warnings=warnings,
            ))
        return items

    def _dashboard_cards(
        self,
        *,
        backend_status: str,
        agents: list[MultiAgentStatusItem],
        active_runs: list[dict[str, Any]],
        active_delegations: list[dict[str, Any]],
        pending_approvals: list[dict[str, Any]],
        failures: list[dict[str, Any]],
        blocks: list[dict[str, Any]],
        consistency: StateConsistencyReport,
        policy_count: int,
        tool_count: int,
        artifact_count: int,
        self_healing_status: dict[str, Any],
    ) -> list[ObservabilityCard]:
        return [
            ObservabilityCard(card_id="multi_agent_backend", title="Backend", status=backend_status, severity="success" if backend_status in {"online", "healthy", "ok"} else "warning", summary="Estado do backend e portas de controle.", details={"backend_status": backend_status}),
            ObservabilityCard(card_id="multi_agent_agents", title="Agentes", status="ok", severity="info", summary="Agentes registrados no kernel multiagente.", count=len(agents), details={"agents": [item.model_dump() for item in agents]}),
            ObservabilityCard(card_id="multi_agent_active_runs", title="Runs ativos", status="running" if active_runs else "idle", severity="info", summary="Runs ainda em execucao ou esperando acao.", count=len(active_runs), details={"runs": active_runs[:10]}),
            ObservabilityCard(card_id="multi_agent_delegations", title="Delegacoes ativas", status="running" if active_delegations else "idle", severity="info", summary="Delegacoes entre agentes com rastreabilidade.", count=len(active_delegations), details={"delegations": active_delegations[:10]}),
            ObservabilityCard(card_id="multi_agent_approvals", title="Approvals pendentes", status="pending" if pending_approvals else "ok", severity="warning" if pending_approvals else "success", summary="Acoes que aguardam aprovacao humana.", count=len(pending_approvals), details={"approvals": pending_approvals[:10]}),
            ObservabilityCard(card_id="multi_agent_policy", title="Policy Kernel", status="ok", severity="info", summary="Decisoes de policy e auto-approvals auditaveis.", count=policy_count, details={"policy_decisions": policy_count}),
            ObservabilityCard(card_id="multi_agent_tools", title="Tool Gateway", status="ok", severity="info", summary="Invocacoes de ferramentas governadas.", count=tool_count, details={"tool_invocations": tool_count}),
            ObservabilityCard(card_id="multi_agent_artifacts", title="Artifacts", status="ok", severity="info", summary="Artifacts registrados e protegidos por token.", count=artifact_count, details={"artifact_count": artifact_count}),
            ObservabilityCard(
                card_id="multi_agent_consistency",
                title="Consistencia de estado",
                status=consistency.status,
                severity="danger" if consistency.status == "blocked" else ("warning" if consistency.status == "degraded" else "success"),
                summary="Checagens de divergencia entre runs, events, tools e delegacoes.",
                count=len(consistency.issues),
                details={"counts": consistency.counts},
            ),
            ObservabilityCard(card_id="multi_agent_self_healing", title="Self-Healing Governado", status=str(self_healing_status.get("status", "unknown")), severity="warning" if int(self_healing_status.get("candidates_open", 0) or 0) else "info", summary="Autocura auditavel baseada em candidatos, policy, approvals e validacao.", count=int(self_healing_status.get("candidates_open", 0) or 0), details=self_healing_status),
            ObservabilityCard(
                card_id="multi_agent_failures",
                title="Historico de bloqueios/falhas",
                status="historical" if failures or blocks else "ok",
                severity="warning" if failures or blocks else "success",
                summary="Falhas e bloqueios terminais preservados para diagnostico.",
                count=len(failures) + len(blocks),
                details={"failures": failures[:10], "blocks": blocks[:10]},
            ),
        ]

    def _self_healing_status(self) -> dict[str, Any]:
        try:
            from aipinho.services.self_healing.self_healing_service import SelfHealingService

            return SelfHealingService(observability=self).status().model_dump()
        except Exception as exc:
            return {"status": "degraded", "error": exc.__class__.__name__, "candidates_open": 0}

    def _dashboard_safe_actions(self) -> list[dict[str, Any]]:
        return [
            {"action_id": "refresh_multi_agent_dashboard", "label": "Atualizar dashboard", "kind": "refresh", "endpoint_ref": "/api/v1/dashboard/multi-agent", "method": "GET", "side_effect": False},
            {"action_id": "open_multi_agent_debugger", "label": "Abrir Debugger 2.0", "kind": "navigate", "endpoint_ref": "/api/v1/debugger/events", "method": "GET", "side_effect": False},
            {"action_id": "export_debug_bundle", "label": "Exportar debug bundle sanitizado", "kind": "create_support_bundle", "endpoint_ref": "/api/v1/debugger/export", "method": "POST", "side_effect": True},
        ]

    def _pending_approvals(self, runs: list[AgentRun], events: list[AgentEvent], policies: list[Any]) -> list[dict[str, Any]]:
        pending: list[dict[str, Any]] = []
        seen: set[tuple[str, str | None]] = set()
        runs_by_id = {run.run_id: run for run in runs}
        for run in runs:
            if self._run_effective_status(run, events) == "pending_approval":
                key = (run.run_id, None)
                if key not in seen:
                    pending.append({"run_id": run.run_id, "agent_id": run.agent_id, "session_id": run.session_id, "operation_type": run.operation_type, "source": "run_status"})
                    seen.add(key)
        for policy in policies:
            run = runs_by_id.get(policy.run_id)
            if (
                policy.decision == "require_approval"
                and run is not None
                and self._run_effective_status(run, events) == "pending_approval"
            ):
                key = (policy.run_id, None)
                if key in seen:
                    continue
                pending.append({"run_id": policy.run_id, "agent_id": policy.agent_id, "session_id": policy.session_id, "operation_type": policy.operation_type, "capability": policy.capability, "source": "policy_decision", "policy_decision_id": policy.policy_decision_id})
                seen.add(key)
        return pending

    def _validation_summaries(self, runs: list[AgentRun], events: list[AgentEvent]) -> list[dict[str, Any]]:
        summaries = []
        for run in runs:
            if run.validation_status:
                summaries.append({"run_id": run.run_id, "agent_id": run.agent_id, "validation_status": run.validation_status})
        for event in events:
            if event.validation_id or event.event_type.startswith("validation_"):
                summaries.append({"run_id": event.run_id, "agent_id": event.agent_id, "validation_id": event.validation_id, "status": event.status, "event_type": event.event_type})
        return summaries[:100]

    def _report_summaries(self) -> list[dict[str, Any]]:
        if not PATHS.reports_root.exists():
            return []
        paths = sorted(
            [path for path in PATHS.reports_root.rglob("*") if path.is_file() and path.suffix.lower() in {".md", ".json"}],
            key=lambda path: path.stat().st_mtime,
            reverse=True,
        )
        return [{"filename": path.name, "relative_path": str(path.relative_to(PATHS.project_root)), "size_bytes": path.stat().st_size} for path in paths[:50]]

    def _event_view(self, event: AgentEvent) -> DebuggerEventView:
        refs = {
            "tool_invocation_id": event.tool_invocation_id,
            "delegation_id": event.delegation_id,
            "approval_id": event.approval_id,
            "validation_id": event.validation_id,
        }
        if event.artifact_ids:
            refs["artifact_id"] = event.artifact_ids[-1]
        return DebuggerEventView(
            event_id=event.event_id,
            run_id=event.run_id,
            session_id=event.session_id,
            agent_id=event.agent_id,
            event_type=event.event_type,
            status=event.status,
            severity=event.severity,
            human_message=str(redact_payload(event.human_message)),
            created_at=event.created_at,
            source="agent_event",
            visible_in_timeline=event.visible_in_timeline,
            evidence_refs=event.evidence_refs,
            refs={key: value for key, value in refs.items() if value},
            payload_sanitized=redact_payload(event.payload_sanitized),
            raw_available=bool(event.raw_ref),
        )

    def _policy_event_views(self, policies: list[Any]) -> list[DebuggerEventView]:
        return [
            DebuggerEventView(
                event_id=policy.policy_decision_id,
                run_id=policy.run_id,
                session_id=policy.session_id,
                agent_id=policy.agent_id,
                event_type="policy_decision",
                status=policy.decision,
                severity="warning" if policy.decision in {"deny", "require_approval"} else "info",
                human_message=policy.human_reason,
                created_at=policy.created_at,
                source="policy_audit",
                evidence_refs=policy.evidence_refs,
                refs={
                    key: value
                    for key, value in {
                        "policy_decision_id": policy.policy_decision_id,
                        "tool_invocation_id": policy.tool_invocation_id,
                        "auto_approval_id": policy.auto_approval_id,
                    }.items()
                    if value
                },
                payload_sanitized=redact_payload({
                    "capability": policy.capability,
                    "operation_type": policy.operation_type,
                    "reason_code": policy.reason_code,
                    "approval_required": policy.approval_required,
                }),
            )
            for policy in policies
        ]

    def _tool_event_views(self, invocations: list[Any]) -> list[DebuggerEventView]:
        return [
            DebuggerEventView(
                event_id=invocation.tool_invocation_id,
                run_id=invocation.run_id,
                session_id=invocation.session_id,
                agent_id=invocation.agent_id,
                event_type="tool_invocation",
                status=invocation.status,
                severity="warning" if invocation.status in {"blocked", "failed", "approval_required"} else "info",
                human_message=invocation.output_summary_sanitized or invocation.input_summary_sanitized,
                created_at=invocation.completed_at or invocation.started_at,
                source="tool_gateway",
                evidence_refs=invocation.evidence_refs,
                refs={
                    key: value
                    for key, value in {
                        "tool_invocation_id": invocation.tool_invocation_id,
                        "policy_decision_id": invocation.policy_decision_id,
                        "approval_id": invocation.approval_id,
                    }.items()
                    if value
                },
                payload_sanitized=redact_payload({
                    "tool_name": invocation.tool_name,
                    "capability": invocation.capability,
                    "operation_type": invocation.operation_type,
                    "workspace_id": invocation.workspace_id,
                    "block_reason_code": invocation.block_reason_code,
                    "artifact_ids": invocation.artifact_ids,
                }),
                raw_available=bool(invocation.raw_ref),
            )
            for invocation in invocations
        ]

    def _self_healing_event_views(self) -> list[DebuggerEventView]:
        try:
            from aipinho.services.self_healing.self_healing_service import SelfHealingStore

            store = SelfHealingStore()
            events: list[DebuggerEventView] = []
            for candidate in store.list_candidates():
                events.append(
                    DebuggerEventView(
                        event_id=candidate.candidate_id,
                        event_type="self_healing_candidate",
                        status=candidate.status,
                        severity="warning" if candidate.risk_level in {"medium", "high"} else ("danger" if candidate.risk_level == "critical" else "info"),
                        human_message=candidate.summary,
                        created_at=candidate.updated_at,
                        source="self_healing",
                        evidence_refs=candidate.evidence_refs,
                        refs={"candidate_id": candidate.candidate_id, "entity_id": candidate.entity_id},
                        payload_sanitized=redact_payload({
                            "detector_id": candidate.detector_id,
                            "issue_type": candidate.issue_type,
                            "risk_level": candidate.risk_level,
                            "policy_decision": candidate.policy_decision,
                            "approval_required": candidate.approval_required,
                        }),
                    )
                )
            for run in store.list_runs():
                events.append(
                    DebuggerEventView(
                        event_id=run.self_healing_run_id,
                        event_type="self_healing_run",
                        status=run.status,
                        severity="warning" if run.status in {"blocked", "pending_approval", "failed"} else "info",
                        human_message=run.summary,
                        created_at=run.completed_at or run.started_at,
                        source="self_healing",
                        evidence_refs=[f"candidate:{run.candidate_id}"],
                        refs={"self_healing_run_id": run.self_healing_run_id, "candidate_id": run.candidate_id},
                        payload_sanitized=redact_payload({
                            "action_type": run.action_type,
                            "validation_status": run.validation_status,
                            "artifact_ids": run.artifact_ids,
                        }),
                    )
                )
            return events
        except Exception:
            return []

    def _refs_match(self, event_refs: dict[str, str], requested_refs: dict[str, str | None]) -> bool:
        for key, value in requested_refs.items():
            if not value:
                continue
            normalized = key if key.endswith("_id") else f"{key}_id"
            if event_refs.get(normalized) != value:
                return False
        return True

    def _after_cursor(self, events: list[DebuggerEventView], cursor: str) -> list[DebuggerEventView]:
        for index, event in enumerate(events):
            if event.event_id == cursor:
                return events[index + 1 :]
        return events

    def _dedupe_trace(self, graph: TraceGraphResponse) -> TraceGraphResponse:
        nodes = {node.node_id: node for node in graph.nodes}
        edge_keys = set()
        edges: list[TraceGraphEdge] = []
        for edge in graph.edges:
            key = (edge.source, edge.target, edge.relation)
            if key in edge_keys:
                continue
            edge_keys.add(key)
            edges.append(edge)
        return graph.model_copy(update={"nodes": list(nodes.values()), "edges": edges})

    def _events_by_run(self, events: list[AgentEvent]) -> dict[str, list[AgentEvent]]:
        by_run: dict[str, list[AgentEvent]] = {}
        for event in events:
            by_run.setdefault(event.run_id, []).append(event)
        return by_run

    def _run_effective_status(self, run: AgentRun | None, events: list[AgentEvent]) -> str:
        if run is None:
            return "idle"
        relevant = [event for event in events if event.run_id == run.run_id]
        status = run.status
        if status in TERMINAL_STATUSES:
            if status in {"completed", "completed_with_warnings"} and any(event.status == "validation_failed" for event in relevant):
                return "validation_failed"
            return status
        if run.completed_at:
            return "cancelled" if run.error_code == "stale_runtime_cleanup" else "completed_with_warnings"
        terminal_events = [event for event in relevant if event.status in TERMINAL_STATUSES]
        if terminal_events:
            latest_terminal = terminal_events[-1]
            if latest_terminal.status in {"completed", "completed_with_warnings"} and any(event.status == "validation_failed" for event in relevant):
                return "validation_failed"
            return latest_terminal.status
        precedence = {
            "blocked": 100,
            "failed": 95,
            "validation_failed": 90,
            "pending_approval": 80,
            "pending_validation": 70,
            "delegation_running": 60,
            "running": 50,
            "created": 40,
            "completed_with_warnings": 30,
            "completed": 30,
            "cancelled": 20,
        }
        for event in relevant:
            if precedence.get(event.status, 0) > precedence.get(status, 0):
                status = event.status
        return status

    def _run_summary(self, run: AgentRun) -> dict[str, Any]:
        return redact_payload({
            "run_id": run.run_id,
            "agent_id": run.agent_id,
            "session_id": run.session_id,
            "operation_type": run.operation_type,
            "status": run.status,
            "workspace_id": run.workspace_id,
            "capabilities_requested": run.capabilities_requested,
            "validation_status": run.validation_status,
            "artifact_ids": run.artifact_ids,
            "error_code": run.error_code,
            "started_at": run.started_at,
            "completed_at": run.completed_at,
        })

    def _delegation_summary(self, delegation: Any) -> dict[str, Any]:
        return redact_payload({
            "delegation_id": delegation.delegation_id,
            "parent_agent_id": delegation.parent_agent_id,
            "target_agent_id": delegation.target_agent_id,
            "parent_run_id": delegation.parent_run_id,
            "child_run_id": delegation.child_run_id,
            "operation_type": delegation.operation_type,
            "status": delegation.status,
            "risk_level": delegation.risk_level,
        })

    def _issue(self, issue_type: str, severity: str, entity_type: str, entity_id: str, summary: str, evidence_refs: list[str]) -> StateConsistencyIssue:
        return StateConsistencyIssue(
            issue_id=f"{issue_type}:{entity_id}",
            issue_type=issue_type,
            severity=severity,
            entity_type=entity_type,
            entity_id=entity_id,
            summary=summary,
            evidence_refs=evidence_refs,
            suggested_action="Abrir Debugger 2.0 e revisar o trace antes de qualquer reparo.",
        )
