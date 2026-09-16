from __future__ import annotations

from types import SimpleNamespace

from aipinho.schemas.chat.chat_request import ChatRequest
from aipinho.services.governance.lifecycle.canonical_public_chat_service import CanonicalPublicChatService


class _CapturingDraftStore:
    def __init__(self) -> None:
        self.saved = None

    def save(self, draft):
        self.saved = draft
        return draft


class _FakePreviewService:
    def create_preview_from_draft(self, draft_id: str):
        return SimpleNamespace(preview_id=f"preview_for_{draft_id}")


class _FakeApprovalService:
    def create_approval_for_preview(self, preview_id: str, **_kwargs):
        return SimpleNamespace(approval_id=f"approval_for_{preview_id}")


def test_executable_preview_draft_preserves_canonical_semantic_intent_graph() -> None:
    draft_store = _CapturingDraftStore()
    service = CanonicalPublicChatService(
        draft_store=draft_store,
        preview_service=_FakePreviewService(),
        approval_service=_FakeApprovalService(),
    )
    request = ChatRequest(
        message=(
            r"Aplique o patch no arquivo C:\\Work\\App\\player.kt e valide a correcao. "
            "Nao altere arquivos fora do workspace."
        ),
        session_id="semantic_draft_session",
    )
    snapshot = service.lifecycle.evaluate(
        user_text=request.message,
        source_channel="unit",
        session_id=request.session_id,
        workspace_path=r"C:\\Work\\App",
    )
    metadata = {
        "primary_target_path": r"C:\\Work\\App\\player.kt",
        "target_paths": [r"C:\\Work\\App\\player.kt"],
        "requested_actions": ["apply_patch"],
        "operation_type": "patch_request",
        "concrete_file_operations": [
            {"action": "apply_patch", "target_path": r"C:\\Work\\App\\player.kt"}
        ],
        "project_generation_plan": {},
        "patch_plan": {
            "diff_ref": "diff_test",
            "files_to_modify": [
                {
                    "path": r"C:\\Work\\App\\player.kt",
                    "diff_ref": "diff_test",
                }
            ],
        },
        "execution_intent": {},
        "executable_patch_plan": {},
        "execution_preview": {},
        "shell_plan": {},
        "source_message_id": "source_test",
        "context_ref": "context_test",
        "discovery_ref": "discovery_test",
        "analysis_ref": "analysis_test",
        "validation_plan": {"checks": ["diff_matches_preview"]},
        "rollback_plan": {"strategy": "reverse_patch"},
        "capabilities_required": ["patch_apply", "write_workspace"],
        "workspace_path": r"C:\\Work\\App",
        "executable_plan_ref": "canonical_plan_test:patch_plan",
        "expected_outputs": ["patch_result", "validation_result"],
    }

    draft, _preview, _approval = service._persist_executable_preview(
        request,
        snapshot,
        metadata,
    )

    assert draft_store.saved is draft
    assert draft.intent_map["intent_type"] == snapshot.intent.intent_type
    assert draft.intent_map["operation_type"] == snapshot.intent.operation_type
    assert draft.intent_map["requires_task"] == snapshot.intent.requires_task
    assert draft.intent_map["negative_constraints"] == snapshot.intent.negative_constraints
    assert draft.intent_map["semantic_intent_graph"] == snapshot.intent.semantic_intent_graph.model_dump(mode="json")
    assert draft.intent_map["canonical_lifecycle_id"] == snapshot.lifecycle_id
    assert draft.intent_map["canonical_operation_id"] == snapshot.operation_contract.operation_id
    assert draft.intent_map["requested_actions"] == ["apply_patch"]
    assert draft.intent_map["workspace"]["path"] == r"C:\\Work\\App"
