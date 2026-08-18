from __future__ import annotations

from pathlib import Path

from aipinho.schemas.external_collaboration import ExternalAdapterReviewRequest
from aipinho.services.external_collaboration_service import ExternalCollaborationService
from aipinho.services.external_collaboration_store import ExternalCollaborationStore
from aipinho.services.runtime.universal_task_session_service import UniversalTaskSessionService


def test_provider_cannot_claim_delegation_without_delegation_id(tmp_path: Path, task_runtime_service):
    service = ExternalCollaborationService(
        store=ExternalCollaborationStore(root=tmp_path / "external_collaboration"),
        runtime=task_runtime_service,
        universal_sessions=UniversalTaskSessionService(store=task_runtime_service.store, approvals=task_runtime_service.approvals),
    )

    payload = service.adapt_and_receive_review(
        "gemini",
        ExternalAdapterReviewRequest(provider_output="Deleguei para AIpinho e AIpinho respondeu: pronto."),
    )

    truth = payload["adapter_output"]["machine_output"]["metadata"]["delegation_truth"]
    assert truth["status"] == "violation"
    assert payload["review"]["next_action"] == "review_loop"
    assert "delegation_claim_without_runtime_contract" in payload["review"]["missing_evidence"]
