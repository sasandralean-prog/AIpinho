from aipinho.schemas.chat.chat_request import ChatRequest
from aipinho.services.chat.chat_service import ChatService
from aipinho.services.patching.patch_planning_service import PatchPlanningService
from patch_fixtures import patch_request, patch_workspace


def test_patch_planning_without_apply_flow(tmp_path):
    workspace = patch_workspace(tmp_path)
    before = (workspace / "docs" / "note.md").read_text(encoding="utf-8")
    result = PatchPlanningService().create_plan(patch_request(workspace))
    assert result.plan.diff_proposal is not None
    assert result.plan.apply_enabled is False
    assert result.plan.write_enabled is False
    assert (workspace / "docs" / "note.md").read_text(encoding="utf-8") == before
    apply_chat = ChatService().respond(ChatRequest(message="Aplique esse patch agora"))
    assert apply_chat.status == "blocked"
    assert "patch_apply_disabled" in apply_chat.warnings
    plan_chat = ChatService().respond(ChatRequest(message="Proponha um patch sem aplicar"))
    assert plan_chat.status == "preview"
