from aipinho.services.rag.integration.context_sensitivity_gate import ContextSensitivityGate
from tests.unit.rag_memory_test_helpers import admitted_retrieval


def item(text):
    context_item = admitted_retrieval(text="safe context").admitted_items[0]
    context_item.content = text
    return context_item


def test_blocks_api_key_token_password_and_raw_log():
    gate = ContextSensitivityGate()
    assert gate.validate(item("api_key=abcd1234"))["valid"] is False
    assert gate.validate(item("token=abcd1234"))["valid"] is False
    assert gate.validate(item("password=abcd1234"))["valid"] is False
    raw = item("normal")
    raw.source_type = "raw_logs"
    assert gate.validate(raw)["valid"] is False


def test_redaction_removes_secret_value():
    redacted = ContextSensitivityGate().redact("token=abcd1234")
    assert "abcd1234" not in redacted
