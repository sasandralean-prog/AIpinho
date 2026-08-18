from __future__ import annotations

from aipinho.services.governance.live_alignment_conflict_detector import LiveAlignmentConflictDetector


def _ids(conflicts: list[dict]) -> set[str]:
    return {str(item["conflict_id"]) for item in conflicts}


def test_route_has_single_canonical_owner():
    detector = LiveAlignmentConflictDetector()
    conflicts = detector.detect(
        {
            "routes": [
                {
                    "endpoint": "/api/v1/chat",
                    "owner": "governance_lifecycle",
                    "classification": "LIVE_CANONICAL",
                    "actions": ["conversation"],
                }
            ]
        }
    )

    assert "route_missing_owner" not in _ids(conflicts)
    assert "side_effect_route_not_canonical" not in _ids(conflicts)


def test_effective_config_conflict_detector():
    detector = LiveAlignmentConflictDetector()
    conflicts = detector.detect(
        {
            "effective_configs": [
                {
                    "component": "write_policy",
                    "config_files": ["config/a.yaml", "config/b.yaml"],
                    "conflicting_values": {"write_files": ["ask", "denied"]},
                }
            ]
        }
    )

    assert "effective_config_conflict" in _ids(conflicts)


def test_intent_to_multitask_contract_matrix():
    detector = LiveAlignmentConflictDetector()
    conflicts = detector.detect(
        {
            "intent_contracts": [
                {
                    "prompt_class": "planning_readonly",
                    "intent_type": "product_planning_readonly",
                    "operation_type": "product_planning_readonly",
                    "runtime_profile": None,
                    "read_only": True,
                    "actions": ["write_files"],
                }
            ]
        }
    )

    assert "readonly_intent_has_write_action" in _ids(conflicts)


def test_role_model_health_truth():
    detector = LiveAlignmentConflictDetector()
    conflicts = detector.detect(
        {
            "roles": [
                {
                    "role_id": "coder",
                    "requires_real_model": True,
                    "model_configured": True,
                    "real_inference": False,
                    "health": "healthy",
                }
            ]
        }
    )

    assert "role_health_claims_real_without_inference" in _ids(conflicts)


def test_fallback_disclosure_required():
    detector = LiveAlignmentConflictDetector()
    conflicts = detector.detect(
        {"roles": [{"role_id": "speaker", "fallback_possible": True, "fallback_disclosure_required": False}]}
    )

    assert "fallback_without_disclosure" in _ids(conflicts)


def test_stub_cannot_claim_real():
    detector = LiveAlignmentConflictDetector()
    conflicts = detector.detect({"roles": [{"role_id": "router", "stub_used": True, "claims_real": True}]})

    assert "stub_claims_real" in _ids(conflicts)


def test_tool_policy_contract_alignment():
    detector = LiveAlignmentConflictDetector()
    conflicts = detector.detect(
        {
            "tools": [
                {
                    "tool_id": "file_write",
                    "action": "write_files",
                    "side_effect": True,
                    "through_gateway": True,
                    "contract_action_missing": True,
                }
            ]
        }
    )

    assert "tool_missing_policy_action" in _ids(conflicts)
    assert "tool_missing_contract_action" in _ids(conflicts)


def test_approval_requires_executable_plan_ref():
    detector = LiveAlignmentConflictDetector()
    conflicts = detector.detect({"approvals": [{"approval_id": "approval_1", "status": "pending"}]})

    assert "approval_missing_draft_id" in _ids(conflicts)
    assert "approval_missing_executable_plan_ref" in _ids(conflicts)


def test_speaker_truth_requires_evidence():
    detector = LiveAlignmentConflictDetector()
    conflicts = detector.detect({"speaker_truth": [{"response_id": "msg_1", "claims_success": True}]})

    assert "speaker_success_without_evidence" in _ids(conflicts)


def test_pipeline_path_declared_or_degraded():
    detector = LiveAlignmentConflictDetector()
    conflicts = detector.detect({"qa": {"pipeline_status": "partial"}})

    assert "pipeline_path_not_fully_certified" in _ids(conflicts)
    assert any(item["blocking"] is False for item in conflicts)


def test_mobile_launcher_visual_qa_declared_or_degraded():
    detector = LiveAlignmentConflictDetector()
    conflicts = detector.detect({"qa": {"mobile_launcher_visual_status": "partial"}})

    assert "mobile_launcher_visual_qa_partial" in _ids(conflicts)


def test_artifact_required_means_artifact_registered():
    detector = LiveAlignmentConflictDetector()
    conflicts = detector.detect({"artifacts": [{"artifact_id": "artifact_1", "required": True, "registered": False}]})

    assert "artifact_required_not_registered" in _ids(conflicts)


def test_multirole_patch_flow_governed():
    detector = LiveAlignmentConflictDetector()
    conflicts = detector.detect(
        {
            "routes": [
                {
                    "endpoint": "/api/v1/patch/apply",
                    "owner": "patch_apply",
                    "classification": "LIVE_LEGACY_BLOCKED",
                    "actions": ["apply_patch"],
                    "side_effects_possible": True,
                }
            ]
        }
    )

    assert "side_effect_route_not_canonical" in _ids(conflicts)


def test_tool_gateway_blocks_noncanonical_write():
    detector = LiveAlignmentConflictDetector()
    conflicts = detector.detect(
        {
            "tools": [
                {
                    "tool_id": "direct_write",
                    "action": "write_files",
                    "policy_action": "write_files",
                    "side_effect": True,
                    "through_gateway": False,
                }
            ]
        }
    )

    assert "side_effect_tool_bypasses_gateway" in _ids(conflicts)


def test_runtime_detects_sanitized_taskrun_source():
    detector = LiveAlignmentConflictDetector()
    conflicts = detector.detect(
        {
            "runtime": [
                {
                    "run_id": "task_run_1",
                    "executable_source": "task_run_sanitized",
                    "omitted_placeholder_written": True,
                }
            ]
        }
    )

    assert "runtime_uses_sanitized_taskrun_source" in _ids(conflicts)
    assert "omitted_placeholder_written" in _ids(conflicts)


def test_validation_missing_outputs_cannot_pass():
    detector = LiveAlignmentConflictDetector()
    conflicts = detector.detect(
        {"validation": [{"validation_id": "validation_1", "status": "passed", "missing_required_outputs": ["patch"]}]}
    )

    assert "validation_passed_with_missing_outputs" in _ids(conflicts)
