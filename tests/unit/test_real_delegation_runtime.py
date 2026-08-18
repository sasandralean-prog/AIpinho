from __future__ import annotations

from pathlib import Path

from aipinho.schemas.runtime.delegation_contract import DelegationCreateRequest
from aipinho.services.external_collaboration_service import ExternalCollaborationService
from aipinho.services.external_collaboration_store import ExternalCollaborationStore
from aipinho.services.runtime.universal_task_session_service import UniversalTaskSessionService


def _service(tmp_path: Path, task_runtime_service) -> ExternalCollaborationService:
    return ExternalCollaborationService(
        store=ExternalCollaborationStore(root=tmp_path / "external_collaboration"),
        runtime=task_runtime_service,
        universal_sessions=UniversalTaskSessionService(
            store=task_runtime_service.store,
            approvals=task_runtime_service.approvals,
        ),
    )


def test_simple_math_uses_direct_response_without_delegation(tmp_path: Path, task_runtime_service):
    payload = _service(tmp_path, task_runtime_service).create_delegation(
        DelegationCreateRequest(provider="external_model", objective="2+2")
    )

    assert payload["mode"] == "direct_response"
    assert payload["delegation_id"] is None
    assert payload["child_run_id"] is None


def test_explicit_ask_aipinho_creates_delegation_contract_and_child_run(tmp_path: Path, task_runtime_service):
    payload = _service(tmp_path, task_runtime_service).create_delegation(
        DelegationCreateRequest(provider="external_model", objective="Pergunte a AIpinho quanto e 2+2")
    )

    assert payload["mode"] == "delegated"
    assert payload["delegation_id"].startswith("delegation_")
    assert payload["child_run_id"].startswith("task_run_")
    assert payload["delegation"]["parent_run_id"] != payload["delegation"]["child_run_id"]
    assert payload["parent_session"]["status"] == "WAITING_DELEGATION"
    assert payload["child_session"]["task_run_id"] == payload["child_run_id"]
