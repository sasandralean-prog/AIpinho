from aipinho.schemas.chat.manual_chat_inference_request import ManualChatInferenceRequest
from aipinho.services.chat.chat_manual_inference_audit_service import ChatManualInferenceAuditService


def test_manual_chat_audit_does_not_persist_full_prompt_or_output(tmp_path):
    service = ChatManualInferenceAuditService(config={"audit": {"enabled": False, "persist_full_prompt": False, "persist_full_output": False, "persist_sanitized_preview": True}})
    event = service.record(event_type="test", request=ManualChatInferenceRequest(message="token=abc123"), warnings=[])
    assert event["prompt_preview"] == "[REDACTED]"
    assert "message" not in event
