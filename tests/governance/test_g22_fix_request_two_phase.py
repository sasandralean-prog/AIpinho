from aipinho.schemas.chat.chat_request import ChatContext, ChatRequest
from aipinho.services.governance.lifecycle.canonical_public_chat_service import CanonicalPublicChatService


def test_fix_request_runs_discovery_first() -> None:
    response = CanonicalPublicChatService().respond(
        ChatRequest(
            message=r"Analise e corrija os problemas no projeto em C:\Users\rafae\Documents\AIpinhoTestes\App.",
            context=ChatContext(surface="api"),
        ),
        source_channel="api_chat",
    )

    assert response.operation_type == "workspace_fix_request"
    assert response.approval_id is None
    assert response.task_draft_id is None
    assert "WORKSPACE_DISCOVERY_REQUIRED" in response.message
    assert response.policy["write_approval_created"] is False


def test_diagnostic_write_requires_analysis_ref_when_approval_requested() -> None:
    snapshot = CanonicalPublicChatService().lifecycle.evaluate(
        user_text="Analise e corrija os problemas.",
        source_channel="unit",
        requested_actions=["apply_patch"],
        operation_type="patch_request",
        explicit_policy_decisions=["ask"],
        executable_plan_ref="plan_patch",
        workspace_path=r"C:\Users\rafae\Documents\AIpinhoTestes\App",
        target_paths=[r"C:\Users\rafae\Documents\AIpinhoTestes\App\main.py"],
        context_ref="ctx",
        discovery_ref="discovery_1",
        expected_outputs=["patch_result", "validation_result"],
        validation_plan={"checks": ["diff_matches_preview"]},
        rollback_plan={"strategy": "reverse_patch"},
        plan_payload={"patch_plan": {"files_to_modify": [{"path": r"C:\Users\rafae\Documents\AIpinhoTestes\App\main.py"}]}},
    )

    assert snapshot.approval_gate.can_create_approval is False
    assert snapshot.approval_gate.reason_code.value == "APPROVAL_NOT_CREATED_NO_ANALYSIS_REF"
