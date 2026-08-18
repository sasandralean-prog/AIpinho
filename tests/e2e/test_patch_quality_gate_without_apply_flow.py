from aipinho.schemas.chat.chat_request import ChatRequest
from aipinho.services.chat.chat_service import ChatService
from aipinho.services.patching.patch_planning_service import PatchPlanningService
from aipinho.services.patching.quality.patch_quality_gate_service import PatchQualityGateService
from patch_fixtures import patch_request, patch_workspace


def test_patch_quality_gate_without_apply_flow(tmp_path):
    workspace = patch_workspace(tmp_path)
    before = (workspace / "docs" / "note.md").read_text(encoding="utf-8")
    plan = PatchPlanningService().create_plan(patch_request(workspace)).plan
    quality = PatchQualityGateService().validate_plan(plan.plan_id)
    assert quality is not None
    assert quality.apply_enabled is False
    assert quality.write_enabled is False
    assert (workspace / "docs" / "note.md").read_text(encoding="utf-8") == before
    chat = ChatService().respond(ChatRequest(message="Valide se esse diff de patch e seguro antes de aplicar"))
    assert chat.status == "preview"
    assert "patch_quality_gate_required" in chat.warnings
    apply_chat = ChatService().respond(ChatRequest(message="Aplique esse patch agora"))
    assert apply_chat.status == "blocked"
    assert "patch_quality_gate_required" in apply_chat.warnings
