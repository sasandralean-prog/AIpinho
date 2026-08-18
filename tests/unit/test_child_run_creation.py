from __future__ import annotations

from pathlib import Path

from aipinho.schemas.runtime.delegation_contract import DelegationCreateRequest
from aipinho.services.external_collaboration_service import ExternalCollaborationService
from aipinho.services.external_collaboration_store import ExternalCollaborationStore
from aipinho.services.runtime.universal_task_session_service import UniversalTaskSessionService


def test_child_run_records_parent_and_delegation_ids(tmp_path: Path, task_runtime_service):
    service = ExternalCollaborationService(
        store=ExternalCollaborationStore(root=tmp_path / "external_collaboration"),
        runtime=task_runtime_service,
        universal_sessions=UniversalTaskSessionService(store=task_runtime_service.store, approvals=task_runtime_service.approvals),
    )
    payload = service.create_delegation(
        DelegationCreateRequest(provider="external_model", objective="Consulte o projeto SapoAndando")
    )
    child = task_runtime_service.store.get_run(payload["child_run_id"])
    parent = task_runtime_service.store.get_run(payload["parent_run_id"])

    assert child is not None
    assert parent is not None
    assert child.intent_map["delegation_id"] == payload["delegation_id"]
    assert child.intent_map["parent_run_id"] == parent.run_id
    assert parent.intent_map["child_run_id"] == child.run_id
