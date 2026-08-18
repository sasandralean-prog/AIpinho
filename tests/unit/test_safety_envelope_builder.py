from aipinho.services.prompts.safety_envelope_builder import SafetyEnvelopeBuilder


def test_safety_envelope_blocks_raw_debug_and_real_inference_claims():
    envelope = SafetyEnvelopeBuilder().build(purpose="chat", policy_decision={"status": "ok"}, role_id="speaker")
    joined = "\n".join(envelope.rules).lower()
    assert "raw debug" in joined
    assert "real inference" in joined
    assert envelope.real_inference is False


def test_safety_envelope_records_policy_denial():
    envelope = SafetyEnvelopeBuilder().build(purpose="chat", policy_decision={"status": "denied"}, role_id="speaker")
    assert "policy_denied_envelope" in envelope.warnings
    assert envelope.policy_status == "denied"
