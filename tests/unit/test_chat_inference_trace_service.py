from aipinho.services.chat.chat_inference_trace_service import ChatInferenceTraceService


def test_chat_inference_trace_visibility_is_explicit():
    service = ChatInferenceTraceService()
    item = service.item("gate", "blocked", "policy")
    assert service.visible([item], include=False) == []
    assert service.visible([item], include=True)[0].stage == "gate"
