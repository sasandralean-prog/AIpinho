from __future__ import annotations

from aipinho.schemas.interaction.contracts import ChatMessageRecord
from aipinho.services.chat.blocked_policy_response_service import BlockedPolicyResponseService
from aipinho.services.chat.chat_operation_router_service import ChatOperationDecision
from aipinho.services.chat.chat_persistence_gate_service import ChatPersistenceGateService
from aipinho.services.chat.permission_status_response_service import PermissionStatusResponseService
from aipinho.services.mobile_view_models.chat_timeline_presenter import ChatTimelinePresenter


def test_policy_block_is_structured_before_task_creation() -> None:
    response = BlockedPolicyResponseService().build(
        session_id="chat_test",
        operation_id="chatop_test",
        operation_type="readonly_analysis_with_artifact_output",
        policy_name="workspace_policy",
        block_reason_code="workspace_not_registered",
        human_reason="O workspace nao esta registrado.",
        safe_alternatives=["Escolha um workspace registrado."],
        requested_capability="read_workspace",
        requested_action="analyze",
    )

    assert response.status == "blocked"
    assert response.task_id is None
    assert response.policy_block is not None
    assert response.policy_block.operation_id == "chatop_test"
    assert response.policy_block.event_id
    assert response.policy_block.trace_id


def test_policy_block_metadata_drives_mobile_blocked_presentation() -> None:
    response = BlockedPolicyResponseService().build(
        session_id="chat_test",
        operation_id="chatop_test",
        operation_type="artifact_request",
        policy_name="artifact_policy",
        block_reason_code="artifact_export_blocked",
        human_reason="A exportacao foi bloqueada.",
        safe_alternatives=["Revise a validacao."],
    )
    decision = ChatOperationDecision(
        operation_id="chatop_test",
        operation_type="artifact_request",
        message_type="blocked_policy_message",
        confidence=1.0,
    )
    metadata = ChatPersistenceGateService().metadata(response, decision)
    message = ChatMessageRecord(
        session_id="chat_test",
        role="assistant",
        content=response.message,
        metadata=metadata,
    )

    presentation = ChatTimelinePresenter().present(session_id="chat_test", messages=[message], cards=[])

    assert presentation.messages[0].safety_label == "Bloqueado"
    assert "Operacao: artifact_request" in presentation.state_lines


def test_structured_runtime_block_metadata_preserves_stage_and_validation() -> None:
    response = BlockedPolicyResponseService().build(
        session_id="chat_test",
        operation_id="chatop_runtime_block",
        operation_type="readonly_analysis_with_artifact_output",
        task_id="task_run_test",
        policy_name="validation_gate",
        block_reason_code="validation_failed",
        human_reason="A validacao falhou.",
        safe_alternatives=["Consulte os checks de validacao."],
        blocked_stage="validation_failed",
        validation_status="failed",
        validation_id="validation_test",
        artifact_output_status="not_created",
    )
    decision = ChatOperationDecision(
        operation_id="chatop_runtime_block",
        operation_type="readonly_analysis_with_artifact_output",
        message_type="blocked_policy_message",
        confidence=1.0,
    )

    metadata = ChatPersistenceGateService().metadata(response, decision)

    assert metadata["status"] == "blocked"
    assert metadata["blocked_stage"] == "validation_failed"
    assert metadata["validation_status"] == "failed"
    assert metadata["validation_id"] == "validation_test"
    assert metadata["artifact_output_status"] == "not_created"


def test_permission_introspection_separates_capabilities_actions_and_preconditions() -> None:
    response = PermissionStatusResponseService().respond(session_id="chat_test")

    assert response.status == "ok"
    assert "registered_capabilities" in response.policy
    assert "currently_allowed_actions" in response.policy
    assert "currently_blocked_actions" in response.policy
    assert "required_preconditions" in response.policy
    assert r"C:\Users\rafae" not in response.message
    assert r"C:\Users\[REDACTED]" in response.message
