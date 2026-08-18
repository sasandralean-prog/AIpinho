from aipinho.services.rag.vector.rag_sensitivity_gate import RAGSensitivityGate


def test_rag_sensitivity_gate_blocks_raw_logs_and_secret_patterns():
    gate = RAGSensitivityGate()

    assert gate.check("plain governed documentation")["status"] == "ok"
    assert "secret_or_sensitive_content_blocked" in gate.check("password: hidden")["blocked_reasons"]
    assert "raw_log_ingestion_blocked" in gate.check("raw log payload")["blocked_reasons"]
