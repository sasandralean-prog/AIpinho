from __future__ import annotations

from fastapi import APIRouter, HTTPException

from aipinho.services.agents.agent_delegation_service import AgentDelegationService
from aipinho.services.agents.agent_profile_registry_service import AgentProfileRegistryService
from aipinho.services.agents.agent_session_store import AgentSessionStore
from aipinho.services.agents.workspace_lock_service import WorkspaceLockService
from aipinho.services.approvals.approval_service import ApprovalService
from aipinho.services.artifacts.artifact_runtime_service import ArtifactRuntimeService
from aipinho.schemas.events.contracts import utc_now_iso

router = APIRouter(prefix="/api/v1/agent-bridge", tags=["agent-bridge"])


ACTIVE_BRIDGE_STATUSES = {"created", "accepted", "running", "approval_required"}
ACTIVE_RUN_STATUSES = {
    "created",
    "running",
    "pending_approval",
    "pending_validation",
    "delegation_running",
    "waiting_child_run",
    "applying",
    "preview_created",
}


def _delegation_summary(item) -> dict[str, object]:
    return {
        "bridge_task_id": item.delegation_id,
        "delegation_id": item.delegation_id,
        "source_agent": item.parent_agent_id,
        "target_agent": item.target_agent_id,
        "status": item.status,
        "workspace": item.workspace_id,
        "prompt_summary": item.user_goal[:240],
        "created_at": item.created_at,
        "updated_at": item.updated_at,
        "owner_task_id": item.child_run_id,
        "parent_run_id": item.parent_run_id,
        "child_run_id": item.child_run_id,
    }


@router.get("/status")
def bridge_status() -> dict[str, object]:
    profiles = AgentProfileRegistryService().list_profiles()
    store = AgentSessionStore()
    sessions = store.list_sessions()
    runs = store.list_runs()
    active_runs = [run for run in runs if run.status in ACTIVE_RUN_STATUSES]
    active_delegations = [
        item
        for item in AgentDelegationService().store.list_requests()
        if item.status in ACTIVE_BRIDGE_STATUSES
    ]
    pending_approvals = ApprovalService().list_approvals(status="pending", limit=200)
    artifacts = ArtifactRuntimeService().list_all(limit=50)
    locks = WorkspaceLockService().list()
    agents = []
    for profile in profiles:
        profile_sessions = [session for session in sessions if session.agent_id == profile.agent_id]
        profile_active_runs = [run for run in active_runs if run.agent_id == profile.agent_id]
        profile_artifacts = [
            item
            for item in artifacts
            if item.get("source_agent_id") == profile.agent_id
            or item.get("metadata", {}).get("source_agent_id") == profile.agent_id
        ]
        latest_timestamps = [session.updated_at for session in profile_sessions]
        latest_timestamps.extend(run.started_at for run in profile_active_runs)
        agents.append(
            {
                "agent_id": profile.agent_id,
                "display_name": profile.display_name,
                "provider": profile.provider,
                "status": "active" if profile_active_runs else "idle",
                "enabled": profile.enabled,
                "can_delegate_to_aipinho": profile.supports_delegation,
                "can_execute_directly": profile.supports_autorun or "execute" in profile.capabilities,
                "can_generate_artifacts": "create_artifact" in profile.capabilities
                or "artifact_generation" in profile.capabilities,
                "active_tasks": len(profile_active_runs),
                "recent_artifacts": len(profile_artifacts),
                "session_count": len(profile_sessions),
                "last_activity": max(latest_timestamps) if latest_timestamps else None,
                "implementation_status": profile.implementation_status,
            }
        )
    return {
        "status": "ok",
        "generated_at": utc_now_iso(),
        "agents": agents,
        "active_bridge_tasks": len(active_delegations),
        "pending_approvals": len(pending_approvals),
        "recent_artifacts": len(artifacts),
        "active_locks": len(locks),
        "warnings": [],
        "raw_default_visible": False,
    }


@router.get("/active")
def bridge_active(limit: int = 100) -> dict[str, object]:
    rows = [
        _delegation_summary(item)
        for item in AgentDelegationService().store.list_requests()
        if item.status in ACTIVE_BRIDGE_STATUSES
    ][: max(1, min(limit, 500))]
    return {"status": "ok", "bridge_tasks": rows}


@router.get("/tasks/{bridge_task_id}/details")
def bridge_task_details(bridge_task_id: str) -> dict[str, object]:
    service = AgentDelegationService()
    try:
        response = service.get_delegation(bridge_task_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="bridge_task_not_found") from exc
    delegation = response.delegation
    parent_events = service.kernel.list_run_events(delegation.parent_run_id, include_hidden=True)
    events = [event for event in parent_events if event.delegation_id == bridge_task_id]
    if delegation.child_run_id:
        events.extend(event for event in service.kernel.list_run_events(delegation.child_run_id, include_hidden=True) if event.delegation_id == bridge_task_id)
    artifacts = ArtifactRuntimeService().by_bridge_task(bridge_task_id, limit=100)
    ownership = WorkspaceLockService().ownership_for_bridge(
        source_agent=delegation.parent_agent_id,
        target_agent=delegation.target_agent_id,
        bridge_task_id=delegation.delegation_id,
        owner_task_id=delegation.child_run_id,
        workspace=delegation.workspace_id,
    )
    locks = WorkspaceLockService().by_workspace(delegation.workspace_id or "") if delegation.workspace_id else []
    return {
        "status": "ok",
        "bridge_task": _delegation_summary(delegation),
        "delegation": delegation.model_dump(),
        "policy_decision": response.policy_decision.model_dump() if response.policy_decision else None,
        "result": response.result.model_dump() if response.result else None,
        "events": [event.model_dump() for event in events],
        "artifacts": artifacts,
        "ownership": ownership.model_dump(),
        "locks": [lock.model_dump() for lock in locks],
    }


@router.post("/tasks/{bridge_task_id}/cancel")
def bridge_task_cancel(bridge_task_id: str) -> dict[str, object]:
    try:
        response = AgentDelegationService().cancel(bridge_task_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="bridge_task_not_found") from exc
    return {"status": "ok", "bridge_task": response.delegation.model_dump(), "result": response.result.model_dump() if response.result else None}
