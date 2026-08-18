from aipinho.schemas.prompts.prompt_assembly import PromptAssemblyRequest
from aipinho.schemas.prompts.prompt_context_item import PromptContextItem
from aipinho.services.prompts.prompt_assembly_service import PromptAssemblyService


def test_prompt_assembly_builds_chat_prompt_without_invocation():
    preview = PromptAssemblyService().preview(
        PromptAssemblyRequest(
            purpose="chat",
            role_id="speaker",
            user_message="O que voce consegue fazer?",
            output_contract_type="chat_response",
            include_trace=True,
        )
    )
    assert preview.invokes_model is False
    assert preview.side_effects is False
    assert preview.model_request.model_id == "stub.default"
    assert any(message.role == "system" for message in preview.model_request.messages)
    assert any("Output contract" in message.content for message in preview.model_request.messages)


def test_prompt_assembly_project_report_preserves_evidence_context():
    assembly = PromptAssemblyService().assemble(
        PromptAssemblyRequest(
            purpose="project_report",
            role_id="reporter",
            user_message="Resuma o projeto",
            output_contract_type="markdown_report",
            evidence=[{"kind": "file", "path": "README.md", "summary": "Project overview"}],
            context_items=[PromptContextItem(source_type="file", title="README", content="AIpinho docs", priority=0.7)],
        )
    )
    assert assembly.purpose == "project_report"
    assert assembly.output_contract.contract_type == "markdown_report"
    assert assembly.context_items
