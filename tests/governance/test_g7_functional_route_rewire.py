from pathlib import Path

from aipinho.schemas.chat.chat_request import ChatContext, ChatRequest
from aipinho.services.approvals.approval_service import ApprovalService
from aipinho.services.approvals.approval_store import ApprovalStore
from aipinho.services.chat.chat_service import ChatService
from aipinho.services.governance.lifecycle.canonical_public_chat_service import CanonicalPublicChatService
from aipinho.services.orchestration.task_draft_store import TaskDraftStore
from aipinho.services.orchestration.task_preview_service import TaskPreviewService
from aipinho.services.orchestration.task_preview_store import TaskPreviewStore


def _service(tmp_path: Path) -> CanonicalPublicChatService:
    draft_store = TaskDraftStore(tmp_path / "drafts")
    preview_service = TaskPreviewService(store=TaskPreviewStore(tmp_path / "previews"), draft_store=draft_store)
    approval_service = ApprovalService(
        store=ApprovalStore(tmp_path / "approvals"),
        preview_service=preview_service,
        draft_store=draft_store,
    )
    return CanonicalPublicChatService(
        draft_store=draft_store,
        preview_service=preview_service,
        approval_service=approval_service,
    )


def test_g7_side_effect_prompt_creates_canonical_approval_without_legacy_chat(monkeypatch, tmp_path: Path) -> None:
    def fail_legacy(*_args, **_kwargs):
        raise AssertionError("legacy ChatService.respond must not own side-effect routing")

    monkeypatch.setattr(ChatService, "respond", fail_legacy)
    response = _service(tmp_path).respond(
        ChatRequest(
            message=r"Crie uma pasta chamada AIpinhoStudioMobile dentro de C:\Users\rafae\Documents\AIpinhoTestes.",
            context=ChatContext(surface="api"),
        ),
        source_channel="api_chat",
    )

    assert response.status == "pending_approval"
    assert response.approval_id and response.approval_id.startswith("approval_")
    assert response.preview_id and response.preview_id.startswith("preview_")
    assert response.task_draft_id and response.task_draft_id.startswith("draft_")
    assert response.governance_lifecycle["intent"]["intent_type"] == "project_bootstrap"
    assert response.governance_lifecycle["approval_gate"]["approval_id"] == response.approval_id
    assert "create_directory" in response.actions


def test_g7_readonly_negative_constraints_do_not_call_permission_grant_or_legacy_chat(monkeypatch, tmp_path: Path) -> None:
    def fail_legacy(*_args, **_kwargs):
        raise AssertionError("legacy ChatService.respond must not classify explicit read-only planning")

    monkeypatch.setattr(ChatService, "respond", fail_legacy)
    response = _service(tmp_path).respond(
        ChatRequest(
            message=(
                "Objetivo: somente planejamento textual. Isto NAO e pedido para criar grant, "
                "NAO e escrita, NAO e ConfigChangeRequest. Classifique este pedido como product_planning_readonly."
            ),
            context=ChatContext(surface="api"),
        ),
        source_channel="api_chat",
    )

    assert response.status == "ok"
    assert response.operation_type == "product_planning_readonly"
    assert response.approval_id is None
    assert response.task_draft_id is None
    assert response.governance_lifecycle["intent"]["intent_type"] == "product_planning_readonly"
    assert response.governance_lifecycle["intent"]["negative_constraints"]["write_forbidden"] is True


def test_g7_workspace_permission_query_uses_canonical_readonly_handler(monkeypatch, tmp_path: Path) -> None:
    def fail_legacy(*_args, **_kwargs):
        raise AssertionError("legacy ChatService.respond must not answer workspace registry query")

    monkeypatch.setattr(ChatService, "respond", fail_legacy)
    response = _service(tmp_path).respond(
        ChatRequest(message="Pode listar os workspaces aprovados para escrita?", context=ChatContext(surface="api")),
        source_channel="api_chat",
    )

    assert response.status == "ok"
    assert response.operation_type == "workspace_permission_list"
    assert "Permissoes atuais da AIpinho" in response.message
    assert response.governance_lifecycle["intent"]["intent_type"] == "workspace_permission_list"
