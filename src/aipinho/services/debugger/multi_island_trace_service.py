from __future__ import annotations

import json
from typing import Any

from aipinho.schemas.artifacts.artifact_generation import ArtifactRequest
from aipinho.schemas.debugger.multi_island_trace import MultiIslandTrace, TraceEvent, TraceExportRequest
from aipinho.schemas.events.contracts import utc_now_iso
from aipinho.services.agents.agent_delegation_store import AgentDelegationStore
from aipinho.services.agents.agent_session_store import AgentSessionStore
from aipinho.services.agents.agent_tool_invocation_store import AgentToolInvocationStore
from aipinho.services.agents.workspace_lock_service import WorkspaceLockService
from aipinho.services.artifacts.artifact_generator_service import ArtifactGeneratorService
from aipinho.services.artifacts.artifact_runtime_service import ArtifactRuntimeService
from aipinho.services.events.event_core import redact_payload


TERMINAL_FINAL_EVENT_TYPES = {"final_answer"}


class MultiIslandTraceService:
    def __init__(
        self,
        *,
        sessions: AgentSessionStore | None = None,
        delegations: AgentDelegationStore | None = None,
        tools: AgentToolInvocationStore | None = None,
        artifacts: ArtifactRuntimeService | None = None,
        locks: WorkspaceLockService | None = None,
        generator: ArtifactGeneratorService | None = None,
    ) -> None:
        self.sessions = sessions or AgentSessionStore()
        self.delegations = delegations or AgentDelegationStore()
        self.tools = tools or AgentToolInvocationStore()
        self.artifacts = artifacts or ArtifactRuntimeService()
        self.locks = locks or WorkspaceLockService()
        self.generator = generator or ArtifactGeneratorService()

    def recent(self, *, limit: int = 50) -> list[MultiIslandTrace]:
        runs = self.sessions.list_runs()[: max(1, min(limit, 200))]
        return [self.by_run(run.run_id) for run in runs]

    def by_agent(self, agent_id: str, *, limit: int = 50) -> list[MultiIslandTrace]:
        return [self.by_run(run.run_id) for run in self.sessions.list_runs(agent_id=agent_id)[: max(1, min(limit, 200))]]

    def by_run(self, run_id: str) -> MultiIslandTrace:
        run = self.sessions.get_run(run_id)
        if run is None:
            raise FileNotFoundError(run_id)
        delegation = self.delegations.get_request(run.delegation_id) if run.delegation_id else self._delegation_for_run(run.run_id)
        bridge_id = run.delegation_id or self._bridge_for_run(run.run_id)
        related_events = self._run_events(run.run_id)
        if delegation and delegation.child_run_id:
            related_events.extend(self._run_events(delegation.child_run_id))
        artifacts = self._artifacts_for(run_id=run.run_id, bridge_task_id=bridge_id)
        final = self._terminal_final_answer(related_events)
        return MultiIslandTrace(
            trace_id=run.run_id,
            user_session_id=run.session_id,
            source_agent=delegation.parent_agent_id if delegation else run.agent_id,
            target_agent=delegation.target_agent_id if delegation else run.agent_id,
            bridge_task_id=bridge_id,
            task_id=run.run_id,
            run_id=run.run_id,
            workspace=run.workspace_id,
            intent_type=str(run.metadata_sanitized.get("intent_type") or ""),
            operation_type=run.operation_type,
            mode=str(run.metadata_sanitized.get("execution_mode") or run.metadata_sanitized.get("source_mode") or ""),
            status=run.status,
            created_at=run.started_at,
            updated_at=run.completed_at or utc_now_iso(),
            events=self._trace_events(run.run_id, related_events),
            artifacts=artifacts,
            approvals=[],
            locks=[lock.model_dump() for lock in self.locks.by_workspace(run.workspace_id)] if run.workspace_id else [],
            errors=[event.human_message for event in related_events if event.severity in {"error", "critical", "danger", "blocked"}],
            final_answer=final,
        )

    def by_bridge_task(self, bridge_task_id: str) -> MultiIslandTrace:
        delegation = self.delegations.get_request(bridge_task_id)
        if delegation is None:
            raise FileNotFoundError(bridge_task_id)
        return self.by_run(delegation.parent_run_id)

    def by_artifact(self, artifact_id: str) -> MultiIslandTrace:
        artifact = self.artifacts.get(artifact_id)
        if artifact is None:
            raise FileNotFoundError(artifact_id)
        bridge = artifact.get("bridge_task_id")
        run_id = artifact.get("owner_task_id") or artifact.get("run_id") or artifact.get("task_id")
        if bridge:
            return self.by_bridge_task(str(bridge))
        if run_id:
            return self.by_run(str(run_id))
        trace = MultiIslandTrace(
            trace_id=f"artifact:{artifact_id}",
            source_agent=str(artifact.get("source_agent") or "unknown"),
            status=str(artifact.get("status") or "unknown"),
            artifacts=[artifact],
            events=[
                TraceEvent(
                    event_id=f"artifact_event:{artifact_id}",
                    trace_id=f"artifact:{artifact_id}",
                    source="artifact_registry",
                    type="artifact_ready" if artifact.get("status") == "ready" else "artifact_failed",
                    text=f"Artifact {artifact.get('filename') or artifact_id}",
                    artifact_refs=[artifact_id],
                    payload_sanitized=redact_payload(artifact),
                )
            ],
        )
        return trace

    def export(self, trace_id: str, request: TraceExportRequest):
        trace = self.by_run(trace_id)
        payload = trace.model_dump()
        if request.format == "json":
            content = json.dumps(redact_payload(payload), ensure_ascii=True, indent=2)
            filename = f"{trace_id}_trace_report.json"
            artifact_type = "json_export"
        else:
            content = self._markdown(trace)
            filename = f"{trace_id}_trace_report.md"
            artifact_type = "markdown_report"
        return self.generator.generate(
            ArtifactRequest(
                source_agent="debugger",
                owner_task_id=trace.run_id,
                bridge_task_id=trace.bridge_task_id,
                artifact_type=artifact_type,
                requested_filename=filename,
                content_source="inline",
                content_inline=content,
                metadata={"trace_id": trace.trace_id, "format": request.format},
            )
        )

    def _run_events(self, run_id: str):
        return self.sessions.list_events(run_id, include_hidden=True, limit=100000)

    def _bridge_for_run(self, run_id: str) -> str | None:
        for item in self.delegations.list_requests():
            if item.parent_run_id == run_id or item.child_run_id == run_id:
                return item.delegation_id
        return None

    def _delegation_for_run(self, run_id: str):
        for item in self.delegations.list_requests():
            if item.parent_run_id == run_id or item.child_run_id == run_id:
                return item
        return None

    def _artifacts_for(self, *, run_id: str, bridge_task_id: str | None) -> list[dict[str, Any]]:
        rows = self._artifact_lookup_rows(run_id, limit=100)
        if bridge_task_id:
            rows.extend(self.artifacts.by_bridge_task(bridge_task_id, limit=100))
        seen: dict[str, dict[str, Any]] = {}
        for row in rows:
            artifact_id = str(row.get("artifact_id") or "")
            if artifact_id:
                seen[artifact_id] = row
        return list(seen.values())

    def _artifact_lookup_rows(self, task_id: str, *, limit: int) -> list[dict[str, Any]]:
        lookup = self.artifacts.by_task(task_id, limit=limit)
        if isinstance(lookup, list):
            return lookup
        return list(getattr(lookup, "artifacts", []) or [])

    def _trace_events(self, trace_id: str, events) -> list[TraceEvent]:
        return [
            TraceEvent(
                event_id=event.event_id,
                trace_id=trace_id,
                timestamp=event.created_at,
                source=event.agent_id,
                type=self._event_type(event.event_type),
                text=event.human_message,
                severity=self._severity(event.severity),
                raw_ref=event.raw_ref,
                artifact_refs=event.artifact_ids,
                tool_invocation_id=event.tool_invocation_id,
                policy_ref=(event.payload_sanitized or {}).get("policy_decision_id"),
                approval_ref=event.approval_id,
                payload_sanitized=redact_payload(event.payload_sanitized),
            )
            for event in events
        ]

    def _event_type(self, event_type: str) -> str:
        mapping = {
            "codex_delegated_to_aipinho": "delegation_created",
            "agent_run_created": "task_created",
            "artifact_created": "artifact_ready",
            "artifact_zip_created": "artifact_ready",
        }
        return mapping.get(event_type, event_type)

    def _severity(self, severity: str) -> str:
        if severity in {"debug", "info", "warning", "error", "critical"}:
            return severity
        if severity in {"danger", "blocked"}:
            return "error"
        return "info"

    def _terminal_final_answer(self, events) -> str | None:
        finals = [event.human_message for event in events if event.event_type in TERMINAL_FINAL_EVENT_TYPES]
        return finals[-1] if finals else None

    def _markdown(self, trace: MultiIslandTrace) -> str:
        lines = [
            f"# Trace {trace.trace_id}",
            "",
            f"- Status: {trace.status}",
            f"- Source agent: {trace.source_agent}",
            f"- Target agent: {trace.target_agent}",
            f"- Bridge task: {trace.bridge_task_id or 'none'}",
            f"- Run: {trace.run_id or 'none'}",
            f"- Workspace: {trace.workspace or 'none'}",
            "",
            "## Events",
        ]
        for event in trace.events:
            lines.append(f"- [{event.severity}] {event.type}: {event.text}")
        lines.extend(["", "## Artifacts"])
        for artifact in trace.artifacts:
            lines.append(f"- {artifact.get('artifact_id')}: {artifact.get('filename')} ({artifact.get('status')})")
        if trace.final_answer:
            lines.extend(["", "## Final Answer", trace.final_answer])
        return "\n".join(lines) + "\n"
