from aipinho.services.roles.role_model_binding_service import RoleModelBindingService
from aipinho.services.roles.role_model_status_service import RoleModelStatusService


def test_role_model_contract_exposes_text_and_governed_multimodal_roles():
    bindings = RoleModelBindingService()
    role_ids = {binding.role_id for binding in bindings.list_bindings()}

    assert {"coder", "planner", "speaker", "interpreter", "patch_quality_reviewer"}.issubset(role_ids)
    vision = bindings.get_binding("vision_analyst")
    assert vision is not None
    assert vision.metadata["pipeline_only"] is True
    assert vision.metadata["tool_calling_enabled"] is False
    assert vision.metadata["workspace_write_enabled"] is False
    assert bindings.get_disabled("embedding") is not None


def test_role_model_status_contract_allows_governed_chat_inference_but_blocks_tools_and_write():
    status = RoleModelStatusService().status()

    assert status["enabled"] is True
    assert status["chat_auto_role_inference"] is True
    assert status["tool_calling_enabled"] is False
    assert status["workspace_write_enabled"] is False
    assert status["large_models_manual_only"] is True
