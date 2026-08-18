from pathlib import Path

from aipinho.schemas.chat.chat_request import ChatContext, ChatRequest
from aipinho.services.approvals.approval_service import ApprovalService
from aipinho.services.approvals.approval_store import ApprovalStore
from aipinho.services.governance.lifecycle.canonical_public_chat_service import CanonicalPublicChatService
from aipinho.services.orchestration.task_draft_store import TaskDraftStore
from aipinho.services.orchestration.task_preview_service import TaskPreviewService
from aipinho.services.orchestration.task_preview_store import TaskPreviewStore


def test_canonical_lifecycle_trace_contains_contract_policy_plan_approval(tmp_path: Path) -> None:
    draft_store = TaskDraftStore(tmp_path / "drafts")
    preview_service = TaskPreviewService(store=TaskPreviewStore(tmp_path / "previews"), draft_store=draft_store)
    approvals = ApprovalService(store=ApprovalStore(tmp_path / "approvals"), preview_service=preview_service, draft_store=draft_store)
    service = CanonicalPublicChatService(draft_store=draft_store, preview_service=preview_service, approval_service=approvals)

    response = service.respond(
        ChatRequest(
            message=r"Crie uma pasta chamada TraceApp dentro de C:\Users\rafae\Documents\AIpinhoTestes.",
            context=ChatContext(surface="api"),
        ),
        source_channel="api_chat",
    )

    trace_stages = {item["stage"] for item in response.governance_lifecycle["trace"]}
    assert {"intent", "policy", "plan", "approval", "completion", "approval_persisted"}.issubset(trace_stages)
    assert response.governance_lifecycle["policy"]["permission"] == "ask"
    assert response.governance_lifecycle["execution_plan"]["executable"] is True
    assert response.governance_lifecycle["approval_gate"]["status"] == "pending_approval"
