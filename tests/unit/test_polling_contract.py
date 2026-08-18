from __future__ import annotations

from pathlib import Path

from aipinho.schemas.runtime.delegation_contract import DelegationCreateRequest
from aipinho.services.external_collaboration_service import ExternalCollaborationService
from aipinho.services.external_collaboration_store import ExternalCollaborationStore
from aipinho.services.runtime.universal_task_session_service import UniversalTaskSessionService


def test_delegation_polling_uses_universal_task_session(tmp_path: Path, task_runtime_service):
    service = ExternalCollaborationService(
        store=ExternalCollaborationStore(root=tmp_path / "external_collaboration"),
        runtime=task_runtime_service,
        universal_sessions=UniversalTaskSessionService(store=task_runtime_service.store, approvals=task_runtime_service.approvals),
    )
    created = service.create_delegation(
        DelegationCreateRequest(provider="external_model", objective="Pergunte a AIpinho sobre o projeto")
    )

    polled = service.poll_delegation(created["delegation_id"])

    assert polled is not None
    assert polled["source"] == "universal_task_session"
    assert polled["delegation"]["polling_count"] == 1
    assert polled["child_session"]["task_run_id"] == created["child_run_id"]
