from aipinho.services.models.inference_runtime_limiter import InferenceRuntimeLimiter


def test_inference_runtime_limiter_blocks_max_input_chars():
    service = InferenceRuntimeLimiter(config={"limits": {"max_input_chars": 10, "max_output_tokens": 10, "default_output_tokens": 5, "timeout_seconds": 1, "max_stdout_chars": 10, "max_stderr_chars": 10}, "safety": {"block_empty_prompt": True, "block_prompt_without_safety_envelope": True, "block_prompt_without_output_contract": True}})
    result = service.validate_request(input_chars=20, output_tokens=5, has_safety_envelope=True, has_output_contract=True)
    assert result["allowed"] is False
    assert "max_input_chars_exceeded" in result["blocked_reasons"]


def test_inference_runtime_limiter_requires_timeout_and_contracts():
    service = InferenceRuntimeLimiter(config={"limits": {"max_input_chars": 10, "max_output_tokens": 10, "default_output_tokens": 5, "timeout_seconds": 0, "max_stdout_chars": 10, "max_stderr_chars": 10}, "safety": {"block_empty_prompt": True, "block_prompt_without_safety_envelope": True, "block_prompt_without_output_contract": True}})
    result = service.validate_request(input_chars=1, output_tokens=5, has_safety_envelope=False, has_output_contract=False)
    assert "timeout_required" in result["blocked_reasons"]
    assert "missing_safety_envelope" in result["blocked_reasons"]
    assert "missing_output_contract" in result["blocked_reasons"]
