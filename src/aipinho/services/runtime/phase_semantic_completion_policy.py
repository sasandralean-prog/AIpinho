from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class PhaseCompletionDecision:
    status: str
    safe_to_report_success: bool
    reason_code: str | None
    validation_status: str
    phase_contract_status: str
    artifact_sufficiency_status: str
    safe_for_limited_discovery: bool = False
    partial_artifact_accepted: bool = False
    expected_outputs: list[str] = field(default_factory=list)
    fulfilled_outputs: list[str] = field(default_factory=list)
    missing_outputs: list[str] = field(default_factory=list)
    limited_outputs: list[str] = field(default_factory=list)
    limiting_findings: list[str] = field(default_factory=list)
    blocking_findings: list[str] = field(default_factory=list)
    limitations: list[str] = field(default_factory=list)
    allowed_claims: list[str] = field(default_factory=list)
    forbidden_claims: list[str] = field(default_factory=list)
    required_disclosures: list[str] = field(default_factory=list)
    phase_dependency: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def validation_patch(self) -> dict[str, Any]:
        patch = {
            "status": self.validation_status,
            "phase_contract_status": self.phase_contract_status,
            "artifact_sufficiency_status": self.artifact_sufficiency_status,
            "safe_to_report_success": self.safe_to_report_success,
            "reason_code": self.reason_code,
            "blocking_findings": list(self.blocking_findings),
            "limiting_findings": list(self.limiting_findings),
            "limited_outputs": list(self.limited_outputs),
            "safe_for_limited_discovery": self.safe_for_limited_discovery,
            "phase_semantic_completion_policy": self.metadata,
        }
        return {key: value for key, value in patch.items() if value not in (None, [], {})}


class PhaseSemanticCompletionPolicy:
    """Evaluates phase completion from semantic artifact sufficiency.

    This policy intentionally consumes already-governed artifact summaries and
    validation projections. It does not observe files, infer metadata, or decide
    success from artifact names.
    """

    STALE_TIMEOUT_CODES = {"TASKRUN_LIFECYCLE_TIMEOUT"}

    def __init__(
        self,
        *,
        partial_inventory_allowed: bool = False,
        minimum_evidence_bound_rows: int = 1,
    ) -> None:
        self.partial_inventory_allowed = partial_inventory_allowed
        self.minimum_evidence_bound_rows = max(1, int(minimum_evidence_bound_rows))

    def evaluate(
        self,
        *,
        phase_id: str,
        phase_kind: str,
        runtime_status: str,
        validation: dict[str, Any],
        artifacts: list[dict[str, Any]],
    ) -> PhaseCompletionDecision:
        expected = list(validation.get("expected_outputs") or [])
        fulfilled = list(validation.get("fulfilled_outputs") or [])
        missing = list(validation.get("missing_outputs") or [])
        validation_status = str(validation.get("status") or "")
        if runtime_status == "cancelled":
            return self._terminal_non_success(
                status="blocked",
                validation_status="blocked",
                reason_code=str(validation.get("reason_code") or "PHASE_EXECUTION_CANCELLED"),
                expected=expected,
                fulfilled=fulfilled,
                missing=missing,
                phase_kind=phase_kind,
            )
        if runtime_status == "failed":
            return self._terminal_non_success(
                status="failed",
                validation_status="failed",
                reason_code=str(validation.get("reason_code") or "PHASE_EXECUTION_FAILED"),
                expected=expected,
                fulfilled=fulfilled,
                missing=missing,
                phase_kind=phase_kind,
            )
        partial_inventory = self._evidence_bound_partial_inventory(artifacts)
        if partial_inventory:
            return self._partial_inventory_decision(
                phase_id=phase_id,
                phase_kind=phase_kind,
                validation=validation,
                expected=expected,
                fulfilled=fulfilled,
                missing=missing,
                artifact=partial_inventory,
            )
        if runtime_status == "completed" and validation_status in {"passed", "passed_with_limitations"} and not missing:
            limited = validation_status == "passed_with_limitations"
            return PhaseCompletionDecision(
                status="completed_with_limitations" if limited else "completed",
                safe_to_report_success=not limited,
                reason_code=str(validation.get("reason_code") or "") or None,
                validation_status=validation_status,
                phase_contract_status="satisfied_with_limitations" if limited else "satisfied",
                artifact_sufficiency_status="satisfied_with_limitations" if limited else "satisfied",
                expected_outputs=expected,
                fulfilled_outputs=fulfilled,
                missing_outputs=[],
                limited_outputs=list(validation.get("limited_outputs") or []),
                limiting_findings=list(validation.get("limiting_findings") or []),
                limitations=list(validation.get("limitations") or []),
                allowed_claims=["phase_completed_with_limitations"] if limited else ["phase_completed"],
                forbidden_claims=self._forbidden_claims(),
                phase_dependency={
                    "status": "satisfied_with_limitations" if limited else "satisfied",
                    "upstream_phase_id": phase_id,
                    "reason_codes": [str(validation.get("reason_code"))] if validation.get("reason_code") else [],
                },
                metadata={
                    "phase_id": phase_id,
                    "phase_kind": phase_kind,
                    "partial_allowed": self.partial_inventory_allowed,
                },
            )
        reason_code = self._semantic_reason(validation, artifacts) or "PHASE_REQUIRED_ARTIFACTS_INSUFFICIENT"
        return self._terminal_non_success(
            status="blocked",
            validation_status="blocked",
            reason_code=reason_code,
            expected=expected,
            fulfilled=fulfilled,
            missing=missing,
            phase_kind=phase_kind,
        )

    def _partial_inventory_decision(
        self,
        *,
        phase_id: str,
        phase_kind: str,
        validation: dict[str, Any],
        expected: list[str],
        fulfilled: list[str],
        missing: list[str],
        artifact: dict[str, Any],
    ) -> PhaseCompletionDecision:
        selected_rows = self._int_field(artifact, "selected_rows")
        bound_rows = self._int_field(artifact, "bound_rows")
        evidence_refs = self._int_field(artifact, "evidence_ref_count")
        coverage = self._row_evidence_coverage(artifact)
        safe_for_limited = (
            bound_rows >= self.minimum_evidence_bound_rows
            and evidence_refs >= self.minimum_evidence_bound_rows
            and coverage == "satisfied"
        )
        limitations = list(dict.fromkeys([
            "partial_media_corpus_inventory",
            "media_metadata_not_configured_or_not_observed",
            "relationship_truth_not_validated",
            *[str(item) for item in self._field(artifact, "limitations", default=[]) or []],
        ]))
        limited_outputs = list(dict.fromkeys([
            *fulfilled,
            "partial_media_corpus_inventory",
        ]))
        if self.partial_inventory_allowed and safe_for_limited:
            reason_code = "PHASE1_DISCOVERY_COMPLETED_WITH_LIMITED_INVENTORY"
            return PhaseCompletionDecision(
                status="completed_with_limitations",
                safe_to_report_success=True,
                reason_code=reason_code,
                validation_status="passed_with_limitations",
                phase_contract_status="satisfied_with_limitations",
                artifact_sufficiency_status="partial_accepted",
                safe_for_limited_discovery=True,
                partial_artifact_accepted=True,
                expected_outputs=expected,
                fulfilled_outputs=list(dict.fromkeys([*fulfilled, "artifact:partial_media_corpus_inventory"])),
                missing_outputs=[],
                limited_outputs=limited_outputs,
                limiting_findings=["MUSIC_INVENTORY_PARTIAL_EVIDENCE"],
                limitations=limitations,
                allowed_claims=[
                    "phase_1_discovery_completed_with_limitations",
                    f"partial_inventory_rows_available:{bound_rows}",
                ],
                forbidden_claims=self._forbidden_claims(),
                required_disclosures=limitations,
                phase_dependency={
                    "status": "satisfied_with_limitations",
                    "upstream_phase_id": phase_id,
                    "artifact_contract_status": "partial",
                    "artifact_safe_to_use": False,
                    "artifact_limited_safe_to_use": True,
                    "allowed_downstream_uses": ["limited_discovery_evidence"],
                    "forbidden_downstream_claims": self._forbidden_claims(),
                    "reason_codes": [reason_code, "MUSIC_INVENTORY_PARTIAL_EVIDENCE"],
                },
                metadata=self._metadata(
                    phase_id=phase_id,
                    phase_kind=phase_kind,
                    artifact=artifact,
                    selected_rows=selected_rows,
                    bound_rows=bound_rows,
                    evidence_refs=evidence_refs,
                    safe_for_limited=safe_for_limited,
                ),
            )
        artifact_reason = str(self._field(artifact, "reason_code") or "")
        sufficiency = self._field(artifact, "inventory_sufficiency_summary", default={})
        if not isinstance(sufficiency, dict):
            schema = self._field(artifact, "schema_coverage", default={})
            sufficiency = (schema or {}).get("inventory_sufficiency_summary") if isinstance(schema, dict) else {}
        sufficiency_reason = str((sufficiency or {}).get("reason_code") or "")
        reason_code = sufficiency_reason or (
            artifact_reason
            if artifact_reason and artifact_reason != "MUSIC_INVENTORY_PARTIAL_EVIDENCE"
            else "MUSIC_INVENTORY_PARTIAL_NOT_ACCEPTED_BY_PHASE_CONTRACT"
        )
        blocking = list(dict.fromkeys([
            reason_code,
            "PHASE1_REQUIRED_ARTIFACT_NOT_SAFE_TO_USE",
            *[item for item in missing if item not in self.STALE_TIMEOUT_CODES],
        ]))
        return PhaseCompletionDecision(
            status="blocked",
            safe_to_report_success=False,
            reason_code=reason_code,
            validation_status="blocked",
            phase_contract_status="blocked",
            artifact_sufficiency_status="partial_rejected_by_phase_contract",
            safe_for_limited_discovery=safe_for_limited,
            partial_artifact_accepted=False,
            expected_outputs=expected,
            fulfilled_outputs=fulfilled,
            missing_outputs=blocking,
            limited_outputs=limited_outputs,
            limiting_findings=["MUSIC_INVENTORY_PARTIAL_EVIDENCE"],
            blocking_findings=blocking,
            limitations=limitations,
            allowed_claims=[
                f"partial_inventory_rows_available:{bound_rows}",
                "phase_1_blocked_by_partial_inventory_policy",
            ],
            forbidden_claims=self._forbidden_claims(),
            required_disclosures=limitations,
            phase_dependency={
                "status": "blocked",
                "upstream_phase_id": phase_id,
                "artifact_contract_status": "partial",
                "artifact_safe_to_use": False,
                "artifact_limited_safe_to_use": safe_for_limited,
                "allowed_downstream_uses": ["diagnostic_only"] if safe_for_limited else [],
                "forbidden_downstream_claims": self._forbidden_claims(),
                "reason_codes": [reason_code, "MUSIC_INVENTORY_PARTIAL_EVIDENCE"],
            },
            metadata=self._metadata(
                phase_id=phase_id,
                phase_kind=phase_kind,
                artifact=artifact,
                selected_rows=selected_rows,
                bound_rows=bound_rows,
                evidence_refs=evidence_refs,
                safe_for_limited=safe_for_limited,
            ),
        )

    def _terminal_non_success(
        self,
        *,
        status: str,
        validation_status: str,
        reason_code: str,
        expected: list[str],
        fulfilled: list[str],
        missing: list[str],
        phase_kind: str,
    ) -> PhaseCompletionDecision:
        clean_missing = [item for item in missing if item not in self.STALE_TIMEOUT_CODES]
        blocking = list(dict.fromkeys([reason_code, *clean_missing]))
        return PhaseCompletionDecision(
            status=status,
            safe_to_report_success=False,
            reason_code=reason_code,
            validation_status=validation_status,
            phase_contract_status="blocked" if status == "blocked" else status,
            artifact_sufficiency_status="insufficient",
            expected_outputs=expected,
            fulfilled_outputs=fulfilled,
            missing_outputs=blocking,
            blocking_findings=blocking,
            limitations=["phase_semantic_completion_not_satisfied"],
            forbidden_claims=self._forbidden_claims(),
            phase_dependency={"status": "blocked", "reason_codes": blocking, "phase_kind": phase_kind},
            metadata={
                "phase_kind": phase_kind,
                "partial_allowed": self.partial_inventory_allowed,
                "minimum_evidence_bound_rows": self.minimum_evidence_bound_rows,
            },
        )

    def _evidence_bound_partial_inventory(self, artifacts: list[dict[str, Any]]) -> dict[str, Any] | None:
        for artifact in artifacts:
            if not isinstance(artifact, dict):
                continue
            semantic_status = str(self._field(artifact, "semantic_contract_status") or "").casefold()
            reason_code = str(self._field(artifact, "reason_code") or "")
            if semantic_status == "partial" or reason_code == "MUSIC_INVENTORY_PARTIAL_EVIDENCE":
                if self._int_field(artifact, "bound_rows") > 0 and self._int_field(artifact, "evidence_ref_count") > 0:
                    return artifact
        return None

    def _semantic_reason(self, validation: dict[str, Any], artifacts: list[dict[str, Any]]) -> str | None:
        for key in ("reason_code", "phase_contract_reason_code"):
            reason = validation.get(key)
            if reason and str(reason) not in self.STALE_TIMEOUT_CODES:
                return str(reason)
        for artifact in artifacts:
            reason = self._field(artifact, "reason_code")
            if reason and str(reason) not in self.STALE_TIMEOUT_CODES:
                return str(reason)
        for item in validation.get("missing_outputs") or []:
            if str(item) not in self.STALE_TIMEOUT_CODES:
                return str(item)
        return None

    def _metadata(
        self,
        *,
        phase_id: str,
        phase_kind: str,
        artifact: dict[str, Any],
        selected_rows: int,
        bound_rows: int,
        evidence_refs: int,
        safe_for_limited: bool,
    ) -> dict[str, Any]:
        return {
            "policy_id": "phase_semantic_completion_policy",
            "phase_id": phase_id,
            "phase_kind": phase_kind,
            "partial_allowed": self.partial_inventory_allowed,
            "minimum_required_rows": self.minimum_evidence_bound_rows,
            "requires_full_corpus_coverage": True,
            "requires_metadata_observed": True,
            "requires_relationship_truth": False,
            "allows_not_configured_metadata": False,
            "allows_relationship_candidates_only": True,
            "artifact_semantic_contract_status": self._field(artifact, "semantic_contract_status"),
            "artifact_reason_code": self._field(artifact, "reason_code"),
            "artifact_safe_to_use": bool(self._field(artifact, "safe_to_use")),
            "safe_for_limited_discovery": safe_for_limited,
            "selected_rows": selected_rows,
            "bound_rows": bound_rows,
            "evidence_ref_count": evidence_refs,
            "row_evidence_coverage_status": self._row_evidence_coverage(artifact),
            "inventory_sufficiency_summary": self._field(artifact, "inventory_sufficiency_summary", default={})
            or (
                self._field(artifact, "schema_coverage", default={}).get("inventory_sufficiency_summary", {})
                if isinstance(self._field(artifact, "schema_coverage", default={}), dict)
                else {}
            ),
        }

    def _forbidden_claims(self) -> list[str]:
        return [
            "full_inventory",
            "full_corpus_coverage",
            "full_media_metadata",
            "all_songs_inventoried",
            "relationships_validated",
            "firetest_ready",
            "phase_2_safe_without_dependency_evaluation",
        ]

    def _row_evidence_coverage(self, artifact: dict[str, Any]) -> str:
        coverage = self._field(artifact, "row_evidence_coverage", default={})
        if isinstance(coverage, dict):
            return str(coverage.get("status") or "")
        return str(coverage or "")

    def _int_field(self, artifact: dict[str, Any], key: str) -> int:
        try:
            return int(self._field(artifact, key) or 0)
        except Exception:
            return 0

    def _field(self, artifact: dict[str, Any], key: str, default: Any = None) -> Any:
        if key in artifact:
            return artifact.get(key)
        metadata = artifact.get("metadata") if isinstance(artifact.get("metadata"), dict) else {}
        return metadata.get(key, default)
