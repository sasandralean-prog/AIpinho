
from aipinho.services.legacy_rag.legacy_core import LegacyClassificationService


def test_legacy_rag_classifies_policy_and_deprecated_signals():
    service = LegacyClassificationService()
    categories = service.categories_for("Quality Gate blocked a deprecated /v1 route in legacy runtime")
    assert "policy_lesson" in categories
    assert "legacy_route_reference" in categories
    assert "/v1" in service.deprecated_signals("route /v1/chat")
