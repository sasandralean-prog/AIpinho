from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient

from aipinho.app_factory import create_app
from aipinho.schemas.agents.ownership import WorkspaceLockCreateRequest, WriteConflictCheckRequest
from aipinho.schemas.approvals.approval_request import ApprovalRequest
from aipinho.schemas.common.actor import Actor
from aipinho.services.agents.workspace_lock_service import WorkspaceLockService, WorkspaceLockStore
from aipinho.services.approvals.approval_service import ApprovalService
from aipinho.services.approvals.approval_store import ApprovalStore


client = TestClient(create_app())


def test_workspace_lock_created_and_blocks_other_agent_write(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("AIPINHO_WORKSPACE_LOCK_ROOT", str(tmp_path / "locks"))
    workspace = str(tmp_path / "workspace")
    target_file = str(tmp_path / "workspace" / "src" / "main.py")

    created = client.post(
        "/api/v1/locks",
        json={
            "workspace": workspace,
            "owner_agent": "codex_agent",
            "owner_task_id": "run_codex",
            "locked_paths": [target_file],
            "reason": "write task",
            "ttl_seconds": 600,
        },
    )

    assert created.status_code == 200
    lock = created.json()["lock"]
    assert lock["status"] == "active"

    conflict = client.post(
        "/api/v1/locks/check-write",
        json={
            "workspace": workspace,
            "actor_agent": "aipinho",
            "owner_task_id": "run_aipinho",
            "target_paths": [target_file],
            "operation_type": "patch",
        },
    )

    decision = conflict.json()["decision"]
    assert conflict.status_code == 200
    assert decision["allowed"] is False
    assert decision["reason_code"] == "workspace_locked_by_other_agent"


def test_workspace_lock_release_allows_future_write(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("AIPINHO_WORKSPACE_LOCK_ROOT", str(tmp_path / "locks"))
    workspace = str(tmp_path / "workspace")
    lock = client.post(
        "/api/v1/locks",
        json={"workspace": workspace, "owner_agent": "aipinho", "owner_task_id": "run_a"},
    ).json()["lock"]

    released = client.post(f"/api/v1/locks/{lock['lock_id']}/release", json={"actor_agent": "user", "reason": "done"})
    check = client.post(
        "/api/v1/locks/check-write",
        json={"workspace": workspace, "actor_agent": "codex_agent", "owner_task_id": "run_b"},
    )

    assert released.json()["lock"]["status"] == "released"
    assert check.json()["decision"]["allowed"] is True


def test_workspace_lock_expires_and_stops_blocking_write(tmp_path) -> None:
    service = WorkspaceLockService(WorkspaceLockStore(tmp_path / "locks"))
    workspace = str(tmp_path / "workspace")
    lock = service.create(WorkspaceLockCreateRequest(workspace=workspace, owner_agent="aipinho", owner_task_id="run_a"))
    expired = lock.model_copy(update={"expires_at": (datetime.now(timezone.utc) - timedelta(seconds=5)).isoformat()})
    service.store.save(expired)

    listed = service.list(include_inactive=True)
    decision = service.check_write_conflict(
        WriteConflictCheckRequest(
            workspace=workspace,
            actor_agent="codex_agent",
            owner_task_id="run_b",
        )
    )

    assert listed[0].status == "expired"
    assert decision.allowed is True


def test_hop_guard_blocks_recursion_and_max_hops() -> None:
    recursion = client.post(
        "/api/v1/locks/check-hop",
        json={"source_agent": "aipinho", "target_agent": "lucio", "lineage": ["lucio"], "max_agent_hops": 2},
    ).json()["decision"]
    max_hops = client.post(
        "/api/v1/locks/check-hop",
        json={"source_agent": "aipinho", "target_agent": "gemini_executor", "lineage": ["user", "lucio"], "max_agent_hops": 1},
    ).json()["decision"]

    assert recursion["allowed"] is False
    assert recursion["reason_code"] == "recursion_blocked"
    assert max_hops["allowed"] is False
    assert max_hops["reason_code"] == "max_agent_hops_exceeded"


def test_readonly_analysis_does_not_create_write_lock(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("AIPINHO_WORKSPACE_LOCK_ROOT", str(tmp_path / "locks"))

    locks = client.get("/api/v1/locks").json()["locks"]

    assert locks == []


def test_artifact_provenance_and_revalidate(tmp_path) -> None:
    bridge_task_id = f"bridge_{uuid4().hex}"
    created = client.post(
        "/api/v1/artifacts",
        json={
            "source_agent": "aipinho",
            "filename": f"artifact_{uuid4().hex}.md",
            "content": "body",
            "bridge_task_id": bridge_task_id,
            "owner_task_id": "run_artifact",
            "provenance": {
                "executor_agent": "aipinho",
                "workspace": str(tmp_path),
                "source_files": ["README.md"],
            },
        },
    ).json()["artifact"]

    provenance = client.get(f"/api/v1/artifacts/{created['artifact_id']}/provenance").json()["provenance"]
    revalidated = client.post(f"/api/v1/artifacts/{created['artifact_id']}/revalidate").json()["artifact"]

    assert provenance["source_agent"] == "aipinho"
    assert provenance["executor_agent"] == "aipinho"
    assert provenance["bridge_task_id"] == bridge_task_id
    assert revalidated["status"] == "ready"


def test_stale_artifact_revalidation_marks_missing(tmp_path) -> None:
    created = client.post(
        "/api/v1/artifacts",
        json={
            "source_agent": "aipinho",
            "filename": f"missing_{uuid4().hex}.md",
            "content": "body",
            "owner_task_id": "run_missing",
        },
    ).json()["artifact"]
    path = created.get("local_path")
    if path:
        Path(path).unlink(missing_ok=True)

    revalidated = client.post(f"/api/v1/artifacts/{created['artifact_id']}/revalidate").json()["artifact"]

    assert revalidated["status"] == "missing"
    assert revalidated["validation_status"] == "missing"
    assert revalidated["error_reason"] == "artifact_file_missing"


def test_approval_deny_emits_event(tmp_path) -> None:
    store = ApprovalStore(tmp_path / "approvals")
    now = datetime.now(timezone.utc).isoformat()
    approval = ApprovalRequest(
        approval_id=f"approval_{uuid4().hex}",
        preview_id="preview_test",
        draft_id="draft_test",
        status="pending",
        actions_requested=["write_file"],
        approval_scope="future_artifact_write",
        reason="test",
        risk_level="low",
        policy_snapshot={},
        expires_at=(datetime.now(timezone.utc) + timedelta(minutes=10)).isoformat(),
        created_at=now,
        updated_at=now,
        created_by=Actor(type="system", id="test"),
        execution_status="not_executed",
    )
    store.save(approval)

    ApprovalService(store=store).reject(approval.approval_id, reason="deny from sprint test")

    events = store.list_events(approval.approval_id)
    assert store.get(approval.approval_id).status == "rejected"
    assert "approval_rejected" in {event.event_type for event in events}


def test_bridge_status_endpoint_is_lightweight() -> None:
    status = client.get("/api/v1/agent-bridge/status")

    assert status.status_code == 200
    payload = status.json()
    assert payload["status"] == "ok"
    assert isinstance(payload["agents"], list)
    assert payload["raw_default_visible"] is False
