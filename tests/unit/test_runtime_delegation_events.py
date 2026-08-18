from __future__ import annotations

from pathlib import Path

from aipinho.schemas.runtime.delegation_contract import DelegationCreateRequest
from aipinho.services.external_collaboration_service import ExternalCollaborationService
from aipinho.services.external_collaboration_store import ExternalCollaborationStore
from aipinho.services.runtime.universal_task_session_service import UniversalTaskSessionService


def test_delegation_runtime_emits_auditable_events(tmp_path: Path, task_runtime_service):
    service = ExternalCollaborationService(
        store=ExternalCollaborationStore(root=tmp_path / "external_collaboration"),
        runtime=task_runtime_service,
        universal_sessions=UniversalTaskSessionService(store=task_runtime_service.store, approvals=task_runtime_service.approvals),
    )
    payload = service.create_delegation(
        DelegationCreateRequest(provider="external_model", objective="Consulte o projeto SapoAndando pela AIpinho")
    )
    service.poll_delegation(payload["delegation_id"])

    events = [event.type for event in task_runtime_service.store.get_events(payload["parent_run_id"])]

    assert "delegation_created" in events
    assert "delegation_started" in events
    assert "delegation_forwarded" in events
    assert "delegation_polling" in events
