from aipinho.services.events.event_render_policy_service import EventRenderPolicyService
def test_hidden_event_is_blocked_by_default():
    d=EventRenderPolicyService().decide({"event_id":"e","event_type":"route_called","visibility":"hidden"}); assert "visibility_hidden_hidden_by_default" in d.reasons
