from __future__ import annotations

from aipinho.schemas.policy.decision_ownership import DecisionOwner, DecisionOwnershipMatrix


class DecisionOwnershipService:
    def matrix(self) -> DecisionOwnershipMatrix:
        owners = [
            DecisionOwner(decision="context_admission", owner="context_kernel", rationale="Context Kernel owns context admission, bundle building and prompt context.", ui_can_override=False),
            DecisionOwner(decision="execute_model", owner="orchestrator_policy", rationale="UI can request, policy/orchestrator decides.", ui_can_override=False),
            DecisionOwner(decision="apply_patch", owner="patch_quality_gate_and_approval", rationale="Patch apply requires preview, quality gate and explicit approval.", ui_can_override=False),
            DecisionOwner(decision="show_raw", owner="debugger_policy", rationale="Raw is hidden by default and served only on demand.", ui_can_override=False),
            DecisionOwner(decision="speaker_message", owner="speaker_truth_policy", rationale="Speaker message must cite source event.", ui_can_override=False),
            DecisionOwner(decision="skill_selection", owner="skill_router", rationale="Router selects candidates but cannot authorize execution.", ui_can_override=False),
            DecisionOwner(decision="skill_execution_allowed", owner="policy_kernel", rationale="Policy Kernel owns skill execution authorization.", ui_can_override=False),
            DecisionOwner(decision="skill_tool_access", owner="tool_policy", rationale="Tool Policy and Capability Gate own tool access.", ui_can_override=False),
            DecisionOwner(decision="skill_context_admission", owner="context_kernel", rationale="Skills consume admitted bundles and never assemble final context.", ui_can_override=False),
            DecisionOwner(decision="skill_output_valid", owner="skill_output_validator", rationale="Declared output contract and Validation Gate own output acceptance.", ui_can_override=False),
            DecisionOwner(decision="maintenance_diagnosis", owner="maintenance_plane", rationale="Maintenance Plane diagnoses from admitted evidence without mutation.", ui_can_override=False),
            DecisionOwner(decision="invariant_evaluation", owner="invariant_checker", rationale="Invariant Checker evaluates config-driven invariants read-only.", ui_can_override=False),
            DecisionOwner(decision="repair_proposal", owner="repair_planner", rationale="Repair Planner proposes; Policy Kernel remains execution authority.", ui_can_override=False),
            DecisionOwner(decision="repair_execution_allowed", owner="policy_kernel", rationale="Policy, capability, approval and validation gates authorize any future execution.", ui_can_override=False),
            DecisionOwner(decision="maintenance_patch_preview", owner="patch_planning_pipeline", rationale="Patch Planning owns governed diff generation; Maintenance only hands off.", ui_can_override=False),
            DecisionOwner(decision="maintenance_final_status", owner="validation_gate", rationale="Validation Gate owns final status after any future approved repair.", ui_can_override=False),
            DecisionOwner(decision="replay_capture", owner="replay_harness", rationale="Replay Harness captures sanitized snapshots without executing.", ui_can_override=False),
            DecisionOwner(decision="replay_sanitization", owner="replay_sanitizer", rationale="Replay Sanitizer owns raw and secret redaction.", ui_can_override=False),
            DecisionOwner(decision="regression_expectation", owner="regression_harness", rationale="Regression Harness owns golden expectation comparison.", ui_can_override=False),
            DecisionOwner(decision="regression_result", owner="regression_runner", rationale="Regression Runner records dry-run comparison results only.", ui_can_override=False),
            DecisionOwner(decision="regression_promotion", owner="regression_case_manager", rationale="Promotion requires approval and validation.", ui_can_override=False),
        ]
        return DecisionOwnershipMatrix(status="ok", owners=owners)
