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


def test_prompt_assembly_budget_counts_final_messages_once():
    assembly = PromptAssemblyService().assemble(
        PromptAssemblyRequest(
            purpose="chat",
            role_id="speaker",
            user_message="summarize",
            output_contract_type="chat_response",
            context_items=[
                PromptContextItem(
                    source_type="file",
                    title="large",
                    content="x" * 1500,
                    priority=0.9,
                )
            ],
        )
    )
    message_chars = sum(len(message.content) for message in assembly.messages)
    context_chars = sum(len(item.content) for item in assembly.context_items)
    assert context_chars == 1500
    assert assembly.budget.used_input_chars == message_chars
    assert assembly.budget.used_input_chars != message_chars + context_chars


def test_prompt_assembly_reserves_space_for_fixed_prompt_envelope():
    items = [
        PromptContextItem(
            source_type="file",
            title=f"file-{index}",
            content="x" * 4000,
            priority=0.9,
        )
        for index in range(20)
    ]
    assembly = PromptAssemblyService().assemble(
        PromptAssemblyRequest(
            purpose="task_preview",
            role_id="supervisor",
            user_message="validate",
            output_contract_type="validation_summary",
            context_items=items,
        )
    )

    message_chars = sum(len(message.content) for message in assembly.messages)
    assert message_chars == assembly.budget.used_input_chars
    assert message_chars <= assembly.budget.max_input_chars
    assert "prompt_budget_exceeded" not in assembly.warnings
    assert (
        "context_item_truncated_for_final_prompt_budget" in assembly.warnings
        or "context_item_omitted_for_final_prompt_budget" in assembly.warnings
    )
