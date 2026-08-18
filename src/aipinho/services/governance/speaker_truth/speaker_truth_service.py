from __future__ import annotations

from aipinho.schemas.governance.lifecycle import CanonicalSpeakerTruth, GovernanceLifecycleReasonCode, GovernanceLifecycleSnapshot
from aipinho.schemas.runtime.runtime_truth import RuntimeTruth


class CanonicalSpeakerTruthService:
    SUCCESS_CLAIMS = ["executed", "implemented", "created", "modified", "applied", "validated", "completed"]

    def evaluate(self, snapshot: GovernanceLifecycleSnapshot, runtime_truth: RuntimeTruth | None = None) -> CanonicalSpeakerTruth:
        if runtime_truth is not None:
            return self.from_runtime_truth(runtime_truth)
        disclosures: list[str] = []
        forbidden: list[str] = []
        if snapshot.approval_gate.required and snapshot.approval_gate.status != "approved":
            disclosures.append("approval_pending_or_not_granted")
            forbidden.extend(self.SUCCESS_CLAIMS)
        if snapshot.execution_plan.blocked_reason != GovernanceLifecycleReasonCode.NONE and not snapshot.execution_plan.executable:
            disclosures.append(snapshot.execution_plan.blocked_reason.value)
            forbidden.extend(self.SUCCESS_CLAIMS)
        if not snapshot.completion.safe_to_report_success:
            if snapshot.completion.missing_outputs:
                disclosures.append("missing_outputs:" + ",".join(snapshot.completion.missing_outputs))
            forbidden.extend(self.SUCCESS_CLAIMS)
        can_claim = not forbidden and snapshot.completion.safe_to_report_success
        return CanonicalSpeakerTruth(
            can_claim_success=can_claim,
            message_status="success" if can_claim else ("blocked" if forbidden else "neutral"),
            required_disclosures=list(dict.fromkeys(disclosures)),
            forbidden_claims=list(dict.fromkeys(forbidden)),
            reason_code=GovernanceLifecycleReasonCode.NONE if can_claim else GovernanceLifecycleReasonCode.SPEAKER_TRUTH_BLOCKED,
        )

    def from_runtime_truth(self, truth: RuntimeTruth) -> CanonicalSpeakerTruth:
        disclosures: list[str] = []
        forbidden: list[str] = []
        if truth.contradictions:
            disclosures.extend(f"contradiction:{item}" for item in truth.contradictions)
        if truth.missing_evidence:
            disclosures.extend(f"missing_evidence:{item}" for item in truth.missing_evidence)
        if not truth.safe_to_report_success:
            forbidden.extend(self.SUCCESS_CLAIMS)
        can_claim = truth.safe_to_report_success and not truth.contradictions and not truth.missing_evidence
        if not can_claim and truth.reason_code:
            disclosures.append(truth.reason_code)
        return CanonicalSpeakerTruth(
            can_claim_success=can_claim,
            message_status="success" if can_claim else "blocked",
            required_disclosures=list(dict.fromkeys(disclosures)),
            forbidden_claims=list(dict.fromkeys(forbidden)),
            reason_code=GovernanceLifecycleReasonCode.NONE if can_claim else GovernanceLifecycleReasonCode.SPEAKER_TRUTH_BLOCKED,
        )
