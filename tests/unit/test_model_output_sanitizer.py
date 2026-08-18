from aipinho.services.models.model_output_sanitizer import ModelOutputSanitizer


def test_model_output_sanitizer_redacts_secret_like_text():
    text = "token=abc123 sk-1234567890SECRET bearer abc.def"
    sanitized = ModelOutputSanitizer().sanitize(text)
    assert "abc123" not in sanitized
    assert "sk-1234567890SECRET" not in sanitized
    assert "bearer abc.def" not in sanitized.lower()


def test_model_output_sanitizer_caps_size():
    sanitized = ModelOutputSanitizer().sanitize("abcdef", max_chars=3)
    assert sanitized.startswith("abc")
    assert "TRUNCATED" in sanitized


def test_model_output_sanitizer_extracts_llama_cli_completion():
    prompt = "system: rules\n\nuser: Quanto e 2+2?"
    raw = f"Loading model...\n\n> {prompt}\n\n4\n\n[ Prompt: 1.0 t/s | Generation: 1.0 t/s ]\n\nExiting...\n"
    sanitized = ModelOutputSanitizer().extract_llama_cli_completion(raw, prompt=prompt)
    assert sanitized == "4"


def test_model_output_sanitizer_extracts_fenced_json_after_role_echo():
    prompt = "system: rules\n\nuser: Return JSON only."
    raw = (
        "system: rules\n\n"
        "user: Return JSON only.\n\n"
        "```json\n"
        "{\n"
        '  "replacement": "print(1)\\n",\n'
        '  "rationale": "bounded change"\n'
        "}\n"
    )
    sanitized = ModelOutputSanitizer().extract_llama_cli_completion(raw, prompt=prompt)
    assert sanitized.startswith("```json")
    assert '"replacement": "print(1)\\n"' in sanitized


def test_model_output_sanitizer_strips_reasoning_content():
    sanitized = ModelOutputSanitizer().strip_reasoning_content("[Start thinking]\ninternal\n[End thinking]\n4")
    assert sanitized == "4"


def test_model_output_sanitizer_blocks_unclosed_reasoning_content():
    sanitized = ModelOutputSanitizer().strip_reasoning_content("[Start thinking]\ninternal")
    assert sanitized == ""
