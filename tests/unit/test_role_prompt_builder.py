from aipinho.services.prompts.role_prompt_builder import RolePromptBuilder


def test_role_prompt_builder_uses_configured_template():
    message, warnings = RolePromptBuilder().build_role_message("speaker")
    assert warnings == []
    assert message.role == "developer"
    assert "resposta humana" in message.content.lower()


def test_role_prompt_builder_unknown_role_degrades_safely():
    message, warnings = RolePromptBuilder().build_role_message("unknown_role")
    assert "unknown_role_template" in warnings
    assert message.metadata["status"] == "degraded"
