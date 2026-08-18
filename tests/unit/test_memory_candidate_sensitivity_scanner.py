from aipinho.services.memory.memory_candidate_sensitivity_scanner import MemoryCandidateSensitivityScanner


def test_secret_raw_log_and_large_content_block():
    scanner = MemoryCandidateSensitivityScanner()
    assert scanner.scan("api_key=abcdef12345").status == "blocked"
    assert scanner.scan("Traceback (most recent call last)").status == "blocked"
    assert scanner.scan("\n".join(str(i) for i in range(100))).status == "blocked"
