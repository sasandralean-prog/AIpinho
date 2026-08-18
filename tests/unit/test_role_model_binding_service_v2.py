from aipinho.services.roles.role_model_binding_service import RoleModelBindingService


def test_role_model_binding_default_coding_model_is_qwen_coder_7b():
    service = RoleModelBindingService()

    coder = service.get_binding("coder")

    assert coder is not None
    assert coder.enabled is True
    assert coder.primary_model == "qwen2_5_coder_7b_q4_k_m"
    assert coder.is_default_coding_role is True
    assert "code" in coder.allowed_capabilities


def test_multimodal_roles_are_enabled_after_sprint30():
    service = RoleModelBindingService()

    vision = service.get_binding("vision_analyst")
    assert vision is not None
    assert vision.enabled is True
    assert vision.metadata["pipeline_only"] is True
    assert vision.metadata["tool_calling_enabled"] is False
    assert service.get_disabled("embedding") is not None
    assert service.status()["status"] == "ok"
