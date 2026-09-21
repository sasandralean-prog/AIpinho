from aipinho.services.evaluation.retry_policy_service import RetryPolicyService


def test_retry_policy_retries_invalid_json():
    decision = RetryPolicyService().decide(["invalid_json"])
    assert decision.should_retry is True
    assert decision.strategy == "ask_for_json_only"


def test_retry_policy_retries_truncation():
    decision = RetryPolicyService().decide(["truncation"], truncation_detected=True)
    assert decision.should_retry is True
    assert decision.strategy == "reduce_output_scope"


def test_retry_policy_retries_missing_nested_required_field():
    decision = RetryPolicyService().decide(
        ["missing_required_field:assessments[0].rationale"]
    )
    assert decision.should_retry is True
    assert decision.strategy == "ask_for_missing_fields"


def test_retry_policy_retries_schema_enum_mismatch():
    decision = RetryPolicyService().decide(
        ["schema_enum_mismatch:assessments[0].impact"]
    )
    assert decision.should_retry is True
    assert decision.strategy == "repair_output_contract"


def test_retry_policy_does_not_retry_critical_safety():
    decision = RetryPolicyService().decide(["critical_safety_violation"])
    assert decision.should_retry is False


def test_retry_policy_respects_max_retries():
    decision = RetryPolicyService().decide(["invalid_json"], attempts=1)
    assert decision.should_retry is False

