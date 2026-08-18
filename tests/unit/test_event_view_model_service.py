from aipinho.services.events.event_render_policy_service import EventRenderPolicyService
def test_unknown_event_is_not_normal():
    d=EventRenderPolicyService().decide({"event_id":"e","event_type":"unknown","visibility":"public"}); assert d.render_status=="blocked"
