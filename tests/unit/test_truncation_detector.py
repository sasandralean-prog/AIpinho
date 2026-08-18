from aipinho.services.evaluation.truncation_detector import TruncationDetector


def test_truncation_detector_flags_finish_reason_length():
    result = TruncationDetector().detect("texto", {"finish_reason": "length"})
    assert "finish_reason_length" in result["reasons"]


def test_truncation_detector_flags_incomplete_json():
    result = TruncationDetector().detect('{"findings":', {})
    assert "incomplete_json" in result["reasons"]


def test_truncation_detector_flags_unclosed_markdown_fence():
    result = TruncationDetector().detect("```json\n{}", {})
    assert "unclosed_markdown_fence" in result["reasons"]


def test_truncation_detector_flags_cut_sentence():
    result = TruncationDetector().detect("Esta resposta parece ter sido cortada no meio do caminho", {})
    assert "cut_sentence" in result["reasons"]


def test_truncation_detector_flags_empty_output():
    result = TruncationDetector().detect("", {})
    assert "empty_output" in result["reasons"]
