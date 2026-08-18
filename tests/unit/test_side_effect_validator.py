from aipinho.services.validation.side_effect_validator import SideEffectValidator


def test_side_effect_validator_detects_write_patch_shell_git_and_memory():
    payload = {"events": [{"action": "write_files"}, {"action": "apply_patch"}, {"action": "run_command"}, {"action": "git_push"}, {"action": "memory_write"}]}
    findings = SideEffectValidator().validate(payload)
    codes = {item.code for item in findings}
    assert "side_effect_violation" in codes
    assert "patch_detected" in codes
    assert "shell_detected" in codes


def test_side_effect_validator_allows_internal_runtime_metadata():
    findings = SideEffectValidator().validate({"path": "data/runtime/validations/result.json", "status": "saved"})
    assert findings == []


def test_side_effect_validator_does_not_treat_planned_action_as_executed_effect():
    payload = {
        "plan": {
            "steps": [
                {
                    "step_type": "execute_patch_pipeline",
                    "action": "apply_patch",
                    "status": "completed",
                    "output_summary": {
                        "status": "no_changes_needed",
                        "reason_code": "validated_state_already_satisfies_request",
                    },
                }
            ]
        },
        "events": [{"type": "step_completed", "status": "completed"}],
    }

    assert SideEffectValidator().validate(payload) == []
