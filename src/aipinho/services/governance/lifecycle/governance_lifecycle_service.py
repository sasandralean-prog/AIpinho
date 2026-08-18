from __future__ import annotations

from typing import Any
from uuid import uuid4

from aipinho.schemas.governance.lifecycle import (
    CanonicalOperationContract,
    CanonicalPermission,
    CanonicalValidationVerdict,
    ContextGateDecision,
    GovernanceLifecycleReasonCode,
    GovernanceLifecycleSnapshot,
    GovernanceLifecycleState,
    PreviewQualityDecision,
    PreviewKind,
)
from aipinho.services.governance.approval.canonical_approval_service import CanonicalApprovalService
from aipinho.services.governance.completion.completion_resolver import CanonicalCompletionResolver
from aipinho.services.governance.context.context_discovery_gate import ContextDiscoveryGate
from aipinho.services.governance.policy.effective_policy_decision_service import EffectivePolicyDecisionService
from aipinho.services.governance.preview_quality.approval_preview_quality_gate import ApprovalPreviewQualityGate
from aipinho.services.governance.runtime.canonical_runtime_service import CanonicalRuntimeService
from aipinho.services.governance.speaker_truth.speaker_truth_service import CanonicalSpeakerTruthService
from aipinho.services.semantic_runtime.semantic_intent_resolution_service import SemanticIntentResolutionService


class GovernanceLifecycleService:
    """Canonical source of truth for governed operational state.

    This service consolidates established concepts into a single lifecycle
    snapshot. Routes and legacy services should consume the snapshot instead of
    deriving final status independently.
    """

    def __init__(self) -> None:
        self.intent_resolution = SemanticIntentResolutionService()
        self.policy_service = EffectivePolicyDecisionService()
        self.runtime_service = CanonicalRuntimeService()
        self.context_gate = ContextDiscoveryGate()
        self.preview_quality_gate = ApprovalPreviewQualityGate()
        self.approval_service = CanonicalApprovalService()
        self.completion_resolver = CanonicalCompletionResolver()
        self.speaker_truth = CanonicalSpeakerTruthService()
        self.side_effect_actions = {
            "run_command",
            "run_tests",
            "apply_patch",
            "write_file",
            "write_files",
            "create_file",
            "create_directory",
            "modify_file",
            "delete",
            "delete_file",
            "move",
            "move_file",
            "format",
            "install",
            "build",
            "clean",
            "grant_shell",
            "grant_write",
            "project_generation",
        }

    def evaluate(
        self,
        *,
        user_text: str,
        source_channel: str = "unknown",
        session_id: str | None = None,
        requested_actions: list[str] | None = None,
        operation_type: str | None = None,
        contract_type: str | None = None,
        runtime_profile: str | None = None,
        target_paths: list[str] | None = None,
        workspace_path: str | None = None,
        explicit_policy_decisions: list[object] | None = None,
        executable_plan_ref: str | None = None,
        plan_kind: str | None = None,
        expected_outputs: list[str] | None = None,
        source_message_id: str | None = None,
        context_ref: str | None = None,
        discovery_ref: str | None = None,
        analysis_ref: str | None = None,
        validation_plan: dict[str, Any] | list[Any] | None = None,
        rollback_plan: dict[str, Any] | list[Any] | None = None,
        plan_payload: dict[str, Any] | None = None,
        outputs: dict[str, Any] | None = None,
        proposed_completion_status: str = "not_run",
    ) -> GovernanceLifecycleSnapshot:
        intent = self.intent_resolution.resolve(user_text, source_channel=source_channel)
        op_type = operation_type or intent.operation_type
        actions = list(dict.fromkeys(requested_actions or self._default_actions_for_operation(op_type)))
        if self._readonly_hard_override(intent):
            readonly_expected_outputs = list(expected_outputs or [])
            artifact_outputs_requested = (
                bool(readonly_expected_outputs)
                and any(
                    str(item).startswith("artifact")
                    or str(item) in {"validation_result", "project_analysis_report"}
                    for item in readonly_expected_outputs
                )
                and not (getattr(intent, "negative_constraints", {}) or {}).get("artifact_forbidden")
            )
            actions = []
            target_paths = []
            if artifact_outputs_requested:
                op_type = operation_type or intent.operation_type or "workspace_analysis_readonly"
                contract_type = contract_type or "analysis_readonly"
                runtime_profile = runtime_profile or "readonly_analysis"
                expected_outputs = readonly_expected_outputs
            else:
                op_type = intent.operation_type or "product_planning_readonly"
                contract_type = op_type
                runtime_profile = op_type
                executable_plan_ref = None
                expected_outputs = []
        contract = CanonicalOperationContract(
            operation_id=f"op_{uuid4().hex}",
            session_id=session_id,
            source_channel=source_channel,
            intent_type=intent.intent_type,
            operation_type=op_type,
            contract_type=contract_type or self._default_contract_type(op_type, actions),
            runtime_profile=runtime_profile or self._default_runtime_profile(op_type, actions),
            requested_actions=actions,
            target_paths=list(dict.fromkeys(target_paths or [])),
            workspace_path=workspace_path,
            risk_level="medium" if actions else "low",
            trace=[{"stage": "canonical_contract", "source": "GovernanceLifecycleService"}],
        )
        policy = self.policy_service.resolve(contract, explicit_decisions=explicit_policy_decisions)
        plan = self.runtime_service.build_plan(
            contract,
            executable_plan_ref=executable_plan_ref,
            plan_kind=plan_kind,
            expected_outputs=expected_outputs,
            target_paths=target_paths,
            plan_payload=plan_payload,
        )
        if self._allowed_side_effect_without_plan(policy, contract, plan):
            policy = policy.model_copy(
                update={
                    "permission": CanonicalPermission.DENIED,
                    "allowed_actions": [],
                    "ask_actions": [],
                    "denied_actions": list(contract.requested_actions),
                    "requires_approval": False,
                    "reason_code": GovernanceLifecycleReasonCode.MISSING_EXECUTABLE_PLAN,
                    "reason": "Side-effect operation cannot be allowed without an executable plan.",
                    "trace": [
                        *policy.trace,
                        {
                            "stage": "canonical_policy",
                            "decision": "downgraded_allowed_without_executable_plan",
                            "actions": list(contract.requested_actions),
                        },
                    ],
                }
            )
        if policy.permission == CanonicalPermission.ASK:
            context_gate = self.context_gate.evaluate(
                user_text=user_text,
                intent=intent,
                contract=contract,
                source_message_id=source_message_id,
                context_ref=context_ref,
                discovery_ref=discovery_ref,
                analysis_ref=analysis_ref,
                executable_plan_ref=plan.executable_plan_ref,
                expected_outputs=plan.expected_outputs,
                validation_plan=validation_plan,
            )
            if not context_gate.can_create_write_approval:
                plan = plan.model_copy(
                    update={
                        "preview_kind": PreviewKind.PLAN_ONLY,
                        "executable": False,
                        "executable_plan_ref": None,
                        "blocked_reason": context_gate.reason_code,
                        "trace": [
                            *plan.trace,
                            {"stage": "context_discovery_gate", "status": context_gate.status, "missing": context_gate.missing_requirements},
                        ],
                    }
                )
            preview_quality = self.preview_quality_gate.evaluate(
                contract=contract,
                plan=plan,
                context_gate=context_gate,
                plan_payload=plan_payload,
                validation_plan=validation_plan,
                rollback_plan=rollback_plan,
            )
            if not preview_quality.can_create_approval:
                plan = plan.model_copy(
                    update={
                        "preview_kind": PreviewKind.PLAN_ONLY,
                        "executable": False,
                        "executable_plan_ref": None,
                        "blocked_reason": preview_quality.reason_code,
                        "trace": [
                            *plan.trace,
                            {"stage": "preview_quality_gate", "status": preview_quality.status, "missing": preview_quality.missing_requirements},
                        ],
                    }
                )
        else:
            context_gate = ContextGateDecision(status="not_required", can_create_write_approval=True)
            preview_quality = PreviewQualityDecision(status="not_required", can_create_approval=True)
        approval = self.approval_service.evaluate(policy, plan)
        completion = self.completion_resolver.resolve(plan.expected_outputs, outputs, proposed_status=proposed_completion_status)
        validation = self._validation_verdict(outputs)
        snapshot = GovernanceLifecycleSnapshot(
            state=self._state(policy, plan, approval, completion),
            reason_code=self._reason(policy, plan, approval, completion),
            intent=intent,
            operation_contract=contract,
            policy=policy,
            context_gate=context_gate,
            execution_plan=plan,
            preview_quality=preview_quality,
            approval_gate=approval,
            validation=validation,
            completion=completion,
            trace=[
                {"stage": "intent", "intent_type": intent.intent_type, "operation_type": intent.operation_type},
                {"stage": "policy", "permission": policy.permission.value, "reason_code": policy.reason_code.value},
                {"stage": "context_gate", "status": context_gate.status, "reason_code": context_gate.reason_code.value},
                {"stage": "plan", "preview_kind": plan.preview_kind.value, "executable": plan.executable},
                {"stage": "preview_quality", "status": preview_quality.status, "reason_code": preview_quality.reason_code.value},
                {"stage": "approval", "status": approval.status},
                {"stage": "completion", "status": completion.status},
            ],
        )
        snapshot.speaker_truth = self.speaker_truth.evaluate(snapshot)
        return snapshot

    def _validation_verdict(self, outputs: dict[str, Any] | None) -> CanonicalValidationVerdict:
        validation = (outputs or {}).get("validation_result") if isinstance(outputs, dict) else None
        if not isinstance(validation, dict):
            return CanonicalValidationVerdict()
        status = str(validation.get("status") or "not_run")
        missing_outputs = (
            [str(item) for item in validation.get("missing_outputs") if str(item).strip()]
            if isinstance(validation.get("missing_outputs"), list)
            else []
        )
        evidence_refs = (
            [str(item) for item in validation.get("evidence_refs") if str(item).strip()]
            if isinstance(validation.get("evidence_refs"), list)
            else []
        )
        return CanonicalValidationVerdict(
            status=status,
            safe_to_continue=status in {"passed", "passed_with_warnings", "ok"} and not missing_outputs,
            missing_outputs=missing_outputs,
            evidence_refs=evidence_refs,
        )

    def _state(self, policy, plan, approval, completion) -> GovernanceLifecycleState:
        if policy.permission == CanonicalPermission.DENIED:
            return GovernanceLifecycleState.BLOCKED
        if policy.permission in {CanonicalPermission.INVALID, CanonicalPermission.EXPIRED, CanonicalPermission.STALE}:
            return GovernanceLifecycleState.BLOCKED
        if policy.permission == CanonicalPermission.NEEDS_CLARIFICATION:
            return GovernanceLifecycleState.BLOCKED
        if approval.required:
            if approval.can_create_approval:
                return GovernanceLifecycleState.PENDING_APPROVAL
            return GovernanceLifecycleState.PLAN_ONLY_PREVIEW
        if plan.preview_kind == PreviewKind.PLAN_ONLY and not plan.executable:
            return GovernanceLifecycleState.PLAN_ONLY_PREVIEW
        if completion.safe_to_report_success:
            return GovernanceLifecycleState.COMPLETED
        if completion.status in {"failed", "blocked"}:
            return GovernanceLifecycleState.BLOCKED
        return GovernanceLifecycleState.EXECUTABLE_PREVIEW if plan.executable else GovernanceLifecycleState.POLICY_RESOLVED

    def _reason(self, policy, plan, approval, completion) -> GovernanceLifecycleReasonCode:
        for value in (policy.reason_code, approval.reason_code, plan.blocked_reason, completion.reason_code):
            if value != GovernanceLifecycleReasonCode.NONE:
                return value
        return GovernanceLifecycleReasonCode.NONE

    def _readonly_hard_override(self, intent) -> bool:
        if not getattr(intent, "readonly", False):
            return False
        negative = getattr(intent, "negative_constraints", {}) or {}
        return bool(
            negative.get("write_forbidden")
            or negative.get("shell_forbidden")
            or negative.get("patch_forbidden")
            or negative.get("artifact_forbidden")
            or negative.get("approval_forbidden")
            or negative.get("execution_forbidden")
            or intent.operation_type in {
                "product_planning_readonly",
                "workspace_analysis_readonly",
                "readonly_analysis",
            }
        )

    def _allowed_side_effect_without_plan(self, policy, contract, plan) -> bool:
        if policy.permission != CanonicalPermission.ALLOWED:
            return False
        if not set(contract.requested_actions).intersection(self.side_effect_actions):
            return False
        return not bool(plan.executable and plan.executable_plan_ref)

    def _default_actions_for_operation(self, operation_type: str) -> list[str]:
        if operation_type in {"project_generation", "project_bootstrap"}:
            return ["write_files"]
        if operation_type in {"workspace_fix_request", "analysis_readonly", "readonly_analysis", "workspace_analysis_readonly", "capability_truth"}:
            return []
        if operation_type in {"patch_request", "patch_apply"}:
            return ["apply_patch"]
        if operation_type in {"filesystem_write", "filesystem_create_directory"}:
            return ["create_file"]
        return []

    def _default_contract_type(self, operation_type: str, actions: list[str]) -> str:
        if operation_type in {"project_generation", "project_bootstrap"}:
            return "project_generation"
        if operation_type in {"analysis_readonly", "readonly_analysis", "workspace_analysis_readonly"}:
            return "analysis_readonly"
        if operation_type in {"workspace_fix_request", "capability_truth"}:
            return operation_type
        if "apply_patch" in actions:
            return "patch_request"
        if actions:
            return "filesystem_write"
        return operation_type or "conversation"

    def _default_runtime_profile(self, operation_type: str, actions: list[str]) -> str:
        if operation_type in {"project_generation", "project_bootstrap"}:
            return "project_generation"
        if operation_type in {"analysis_readonly", "readonly_analysis", "workspace_analysis_readonly"}:
            return "readonly_analysis"
        if operation_type in {"workspace_fix_request", "capability_truth"}:
            return operation_type
        if "apply_patch" in actions:
            return "patch"
        if actions:
            return "write_file"
        return operation_type or "conversation"
