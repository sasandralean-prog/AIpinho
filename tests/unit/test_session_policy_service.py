from aipinho.services.session.session_policy_service import SessionPolicyService


def test_session_policy_loads_safe_defaults():
    policy = SessionPolicyService().load()
    assert policy.status()["status"] == "ok"
    assert policy.store_raw_user_message() is False
    assert policy.forbidden_root_as_active_workspace() is False
    assert policy.max_recent_messages() > 0
    assert policy.max_message_chars() > 0