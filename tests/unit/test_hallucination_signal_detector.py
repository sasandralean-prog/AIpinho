from aipinho.services.evaluation.hallucination_signal_detector import HallucinationSignalDetector


def test_hallucination_signal_detector_flags_unseen_file_claim():
    signals = HallucinationSignalDetector().detect("Arquivo src/foo/bar.py resolve.", [{"path": "src/known.py"}])
    assert any(item.code == "claims_unseen_files" for item in signals)


def test_hallucination_signal_detector_flags_unavailable_feature_claim():
    signals = HallucinationSignalDetector().detect("O sistema ja faz RAG real e memoria persistente.", [], {"rag": "disabled"})
    assert any(item.code == "claims_unavailable_features" for item in signals)


def test_hallucination_signal_detector_flags_unsupported_numbers():
    signals = HallucinationSignalDetector().detect("Foram analisados 1234 arquivos.", [])
    assert any(item.code == "unsupported_specific_numbers" for item in signals)


def test_hallucination_signal_detector_flags_architecture_without_evidence():
    signals = HallucinationSignalDetector().detect("A arquitetura possui cinco camadas.", [])
    assert any(item.code == "unsupported_architecture_claim" for item in signals)
