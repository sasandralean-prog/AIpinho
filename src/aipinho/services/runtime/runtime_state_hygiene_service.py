from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import uuid4

from aipinho.core.paths import PATHS
from aipinho.schemas.agents.contracts import AgentEventCreateRequest, AgentRun, AgentRunUpdateRequest, AgentSessionUpdateRequest
from aipinho.schemas.agents.delegation import DelegationResult
from aipinho.schemas.events.contracts import utc_now_iso
from aipinho.services.agents.agent_delegation_store import AgentDelegationStore
from aipinho.services.agents.agent_event_bus import EVENT_STATUS_BY_TYPE
from aipinho.services.agents.agent_session_kernel_service import AgentSessionKernelService
from aipinho.services.agents.agent_session_store import AgentSessionStore


ACTIVE_STATUSES = {"created", "running", "pending_approval", "pending_validation", "delegation_running", "waiting_child_run", "applying"}
TERMINAL_STATUSES = {"completed", "completed_with_warnings", "failed", "blocked", "cancelled", "validation_failed"}
DELEGATION_ACTIVE_STATUSES = {"created", "policy_checking", "accepted", "approval_required", "running"}


class RuntimeStateHygieneService:
    """Audited runtime hygiene for stale sessions/runs without evidence deletion."""

    def __init__(
        self,
        store: AgentSessionStore | None = None,
        kernel: AgentSessionKernelService | None = None,
        delegations: AgentDelegationStore | None = None,
    ) -> None:
        self.store = store or AgentSessionStore()
        self.kernel = kernel or AgentSessionKernelService(store=self.store)
        self.delegations = delegations or AgentDelegationStore()
        self.root = PATHS.project_root / "data" / "runtime" / "hygiene"

    def preview(self, *, max_age_hours: int = 24, limit: int = 200, kinds: list[str] | None = None) -> dict[str, Any]:
        preview_id = f"cleanup_preview_{uuid4().hex}"
        cutoff = datetime.now(timezone.utc) - timedelta(hours=max(1, max_age_hours))
        selected_kinds = self._selected_kinds(kinds)
        candidates: list[dict[str, Any]] = []
        if "run" in selected_kinds:
            for run in self.store.list_runs():
                run_events = self.store.list_events(run.run_id, limit=100000, include_hidden=True)
                effective_status = self._effective_run_status(run, run_events)
                latest_event = run_events[-1] if run_events else None
                last_activity = (latest_event.created_at if latest_event else None) or run.completed_at or run.started_at
                activity_dt = self._parse_dt(last_activity)
                stale = activity_dt is not None and activity_dt < cutoff
                started_dt = self._parse_dt(run.started_at)
                creation_only = len(run_events) <= 1 and (latest_event is None or latest_event.event_type == "agent_run_created")
                stale_by_creation_only = creation_only and started_dt is not None and started_dt < cutoff
                stale_reasons: list[str] = []
                if effective_status in ACTIVE_STATUSES and (stale or stale_by_creation_only):
                    stale_reasons.append("active_run_without_recent_event")
                if effective_status in ACTIVE_STATUSES and run.completed_at:
                    stale_reasons.append("active_run_has_completed_at_without_terminal_status")
                if effective_status in ACTIVE_STATUSES and not run_events:
                    stale_reasons.append("active_run_without_events")
                if stale_reasons:
                    candidates.append(
                        {
                            "kind": "run",
                            "id": run.run_id,
                            "agent_id": run.agent_id,
                            "session_id": run.session_id,
                            "current_status": run.status,
                            "effective_status": effective_status,
                            "proposed_action": "mark_cancelled_stale",
                            "reason": ",".join(stale_reasons),
                            "started_at": run.started_at,
                            "updated_at": last_activity,
                            "last_event": latest_event.event_type if latest_event else None,
                            "event_count": len(run_events),
                        }
                    )
                if len(candidates) >= limit:
                    break
        if "session" in selected_kinds:
            for session in self.store.list_sessions(include_deleted=True):
                updated = self._parse_dt(session.updated_at)
                stale = updated is not None and updated < cutoff
                if stale and not session.archived:
                    candidates.append(
                        {
                            "kind": "session",
                            "id": session.session_id,
                            "agent_id": session.agent_id,
                            "current_status": "active",
                            "proposed_action": "archive_session",
                            "reason": "session_older_than_retention_window",
                            "updated_at": session.updated_at,
                        }
                    )
                if len(candidates) >= limit:
                    break
        runs_by_id = {run.run_id for run in self.store.list_runs()}
        if "delegation" in selected_kinds:
            for delegation in self.delegations.list_requests():
                missing_parent = delegation.parent_run_id not in runs_by_id
                missing_child = bool(delegation.child_run_id and delegation.child_run_id not in runs_by_id)
                if delegation.status in DELEGATION_ACTIVE_STATUSES and (missing_parent or missing_child):
                    candidates.append(
                        {
                            "kind": "delegation",
                            "id": delegation.delegation_id,
                            "parent_agent_id": delegation.parent_agent_id,
                            "target_agent_id": delegation.target_agent_id,
                            "current_status": delegation.status,
                            "proposed_action": "cancel_orphan_delegation",
                            "reason": "active_delegation_references_missing_run",
                            "missing_parent_run": missing_parent,
                            "missing_child_run": missing_child,
                        }
                    )
                if len(candidates) >= limit:
                    break
        payload = {
            "preview_id": preview_id,
            "status": "ok",
            "max_age_hours": max_age_hours,
            "kinds": sorted(selected_kinds),
            "candidate_count": len(candidates),
            "candidates": candidates,
            "safe_apply": True,
            "deletes_evidence": False,
            "created_at": utc_now_iso(),
        }
        self._write_preview(preview_id, payload)
        return payload

    def apply(self, preview_id: str) -> dict[str, Any]:
        preview = self._read_preview(preview_id)
        applied: list[dict[str, Any]] = []
        for candidate in preview.get("candidates", []):
            kind = candidate.get("kind")
            item_id = str(candidate.get("id") or "")
            if kind == "run":
                run = self.store.get_run(item_id)
                if run:
                    run_events = self.store.list_events(run.run_id, limit=100000, include_hidden=True)
                    effective_status = self._effective_run_status(run, run_events)
                    if effective_status in ACTIVE_STATUSES:
                        updated = self.kernel.update_run(
                            run.run_id,
                            AgentRunUpdateRequest(
                                status="cancelled",
                                completed_at=utc_now_iso(),
                                error_code="stale_runtime_cleanup",
                                metadata_sanitized={
                                    **run.metadata_sanitized,
                                    "hygiene_preview_id": preview_id,
                                    "previous_status": run.status,
                                    "previous_effective_status": effective_status,
                                    "stale_reason": candidate.get("reason"),
                                },
                            ),
                        )
                        if updated is not None:
                            self.kernel.add_event(
                                updated.run_id,
                                AgentEventCreateRequest(
                                    event_type="run_marked_stale",
                                    status="cancelled",
                                    severity="warning",
                                    human_message="Run antigo marcado como stale para liberar slot de execucao.",
                                    payload_sanitized={"hygiene_preview_id": preview_id, "previous_effective_status": effective_status, "reason": candidate.get("reason")},
                                ),
                            )
                            self.kernel.add_event(
                                updated.run_id,
                                AgentEventCreateRequest(
                                    event_type="run_slot_released",
                                    status="cancelled",
                                    severity="info",
                                    human_message="Slot de execucao liberado apos reconciliacao de run stale.",
                                    payload_sanitized={"hygiene_preview_id": preview_id},
                                ),
                            )
                        applied.append({"kind": "run", "id": run.run_id, "action": "mark_cancelled_stale"})
            elif kind == "session":
                session = self.store.get_session(str(candidate.get("agent_id") or ""), item_id, include_deleted=True)
                if session and not session.archived:
                    self.kernel.update_session(
                        session.agent_id,
                        session.session_id,
                        AgentSessionUpdateRequest(archived=True, metadata_sanitized={**session.metadata_sanitized, "hygiene_preview_id": preview_id}),
                    )
                    applied.append({"kind": "session", "id": session.session_id, "action": "archive_session"})
            elif kind == "delegation":
                delegation = self.delegations.get_request(item_id)
                if delegation and delegation.status in DELEGATION_ACTIVE_STATUSES:
                    updated = self.delegations.save_request(
                        delegation.model_copy(
                            update={
                                "status": "cancelled",
                                "metadata_sanitized": {
                                    **delegation.metadata_sanitized,
                                    "hygiene_preview_id": preview_id,
                                    "previous_status": delegation.status,
                                    "reason": "active_delegation_references_missing_run",
                                },
                            }
                        )
                    )
                    self.delegations.save_result(
                        DelegationResult(
                            delegation_id=updated.delegation_id,
                            parent_run_id=updated.parent_run_id,
                            child_run_id=updated.child_run_id,
                            parent_agent_id=updated.parent_agent_id,
                            target_agent_id=updated.target_agent_id,
                            status="cancelled",
                            summary="Delegacao ativa orfa reconciliada pelo runtime hygiene.",
                            reason_code="orphan_delegation_cleanup",
                            completed_at=utc_now_iso(),
                            evidence_refs=[f"delegation:{updated.delegation_id}", f"hygiene_preview:{preview_id}"],
                        )
                    )
                    applied.append({"kind": "delegation", "id": updated.delegation_id, "action": "cancel_orphan_delegation"})
        result = {
            "status": "ok",
            "preview_id": preview_id,
            "applied_count": len(applied),
            "applied": applied,
            "deletes_evidence": False,
            "applied_at": utc_now_iso(),
        }
        path = self.root / "applied" / f"{preview_id}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self._json(result), encoding="utf-8")
        return result

    def status(self) -> dict[str, Any]:
        return {
            "status": "ok",
            "service": "runtime_state_hygiene",
            "preview_before_apply": True,
            "deletes_evidence": False,
            "reconciles_orphan_delegations": True,
            "supports_candidate_kind_filter": True,
            "queue_health_endpoint": "/api/v1/runtime/hygiene/queue-health",
            "hygiene_root": str(self.root),
        }

    def queue_health(self, *, max_age_hours: int = 1, worker_pool_capacity: int = 8) -> dict[str, Any]:
        cutoff = datetime.now(timezone.utc) - timedelta(hours=max(1, max_age_hours))
        runs = self.store.list_runs()
        events_by_run = {run.run_id: self.store.list_events(run.run_id, limit=100000, include_hidden=True) for run in runs}
        active_runs = [run for run in runs if self._effective_run_status(run, events_by_run.get(run.run_id, [])) in ACTIVE_STATUSES]
        queued_runs = [run for run in runs if self._effective_run_status(run, events_by_run.get(run.run_id, [])) == "created"]
        stale_run_ids: set[str] = set()
        for run in active_runs:
            events = events_by_run.get(run.run_id, [])
            latest_event = events[-1] if events else None
            last_activity = (latest_event.created_at if latest_event else None) or run.completed_at or run.started_at
            activity_dt = self._parse_dt(last_activity)
            started_dt = self._parse_dt(run.started_at)
            creation_only = len(events) <= 1 and (latest_event is None or latest_event.event_type == "agent_run_created")
            stale_by_creation_only = creation_only and started_dt is not None and started_dt < cutoff
            if run.completed_at or not events or stale_by_creation_only or (activity_dt is not None and activity_dt < cutoff):
                stale_run_ids.add(run.run_id)
        active_sessions = [session for session in self.store.list_sessions(include_deleted=True) if not session.deleted and not session.archived]
        pending_approvals = [run for run in active_runs if self._effective_run_status(run, events_by_run.get(run.run_id, [])) == "pending_approval"]
        available_slots = max(0, int(worker_pool_capacity) - len([run for run in active_runs if run.run_id not in stale_run_ids]))
        dispatcher_status = "saturated" if available_slots <= 0 else "available"
        if stale_run_ids:
            dispatcher_status = "stale_runs_detected"
        return {
            "status": "ok",
            "active_runs": len(active_runs),
            "queued_runs": len(queued_runs),
            "stale_runs": len(stale_run_ids),
            "pending_approvals": len(pending_approvals),
            "active_sessions": len(active_sessions),
            "dispatcher_status": dispatcher_status,
            "worker_pool_capacity": int(worker_pool_capacity),
            "worker_pool_available_slots": available_slots,
            "stale_run_ids": sorted(stale_run_ids)[:50],
            "backpressure_required": dispatcher_status in {"saturated", "stale_runs_detected"},
            "reason_code": "stale_runs_detected" if stale_run_ids else ("active_run_limit_reached" if available_slots <= 0 else None),
        }


    def _effective_run_status(self, run: AgentRun, events: list[Any]) -> str:
        status = run.status
        if status in TERMINAL_STATUSES:
            return status
        if run.completed_at:
            return "cancelled" if run.error_code == "stale_runtime_cleanup" else "completed_with_warnings"
        terminal_events = [event for event in events if event.status in TERMINAL_STATUSES or EVENT_STATUS_BY_TYPE.get(event.event_type) in TERMINAL_STATUSES]
        if terminal_events:
            latest = terminal_events[-1]
            return latest.status if latest.status in TERMINAL_STATUSES else EVENT_STATUS_BY_TYPE.get(latest.event_type, status)
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
        for event in events:
            event_status = event.status or EVENT_STATUS_BY_TYPE.get(event.event_type)
            if precedence.get(event_status, 0) > precedence.get(status, 0):
                status = event_status
        return status

    def _selected_kinds(self, kinds: list[str] | None) -> set[str]:
        allowed = {"run", "session", "delegation"}
        if not kinds:
            return set(allowed)
        selected = {str(kind).strip().lower() for kind in kinds if str(kind).strip()}
        invalid = selected - allowed
        if invalid:
            raise ValueError(f"invalid_hygiene_candidate_kind:{','.join(sorted(invalid))}")
        return selected or set(allowed)

    def _write_preview(self, preview_id: str, payload: dict[str, Any]) -> None:
        path = self.root / "previews" / f"{preview_id}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self._json(payload), encoding="utf-8")

    def _read_preview(self, preview_id: str) -> dict[str, Any]:
        path = self.root / "previews" / f"{preview_id}.json"
        if not path.exists():
            raise FileNotFoundError(preview_id)
        import json

        return json.loads(path.read_text(encoding="utf-8"))

    def _json(self, payload: dict[str, Any]) -> str:
        import json

        return json.dumps(payload, indent=2, ensure_ascii=True)

    def _parse_dt(self, value: str | None) -> datetime | None:
        if not value:
            return None
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
