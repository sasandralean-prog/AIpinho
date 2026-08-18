from aipinho.services.roles.role_fallback_service import RoleFallbackService


def test_role_fallback_deterministic_summary():
    fb = RoleFallbackService().deterministic_output("supervisor")
    assert fb.fallback_used is True
    assert "deterministica" in fb.message.lower()


def test_role_fallback_safe_empty_findings():
    fb = RoleFallbackService().safe_empty_findings()
    assert "findings" in fb.message


def test_role_fallback_skip_optional():
    fb = RoleFallbackService().skip_optional_pass("missing")
    assert fb.skip_pass is True
