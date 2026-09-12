from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone
from typing import Any

from aipinho.schemas.runtime.phase_dependency_evaluation import (
    DependencyRequirementCheck,
    DownstreamPhaseRequirements,
    LimitationAssessment,
    PhaseDependencyAdmission,
    PhaseDependencyEvaluation,
    PhaseDependencySnapshot,
)
from aipinho.services.semantics.limitation_compatibility_resolver_service import (
    LimitationCompatibilityResolverService,
)


class PhaseDependencyEvaluationService:
    """Evaluates and binds upstream evidence before a downstream phase starts."""

    def __init__(
        self,
        *,
        limitation_resolver: LimitationCompatibilityResolverService | None = None,
    ) -> None:
        self.limitation_resolver = (
            limitation_resolver or LimitationCompatibilityResolverService()
        )

    def evaluate(
        self,
        *,
        snapshot: PhaseDependencySnapshot,
        requirements: DownstreamPhaseRequirements,
        consumer_task_run_id: str,
        consumer_operation_id: str,
        consumer_operation_type: str,
    ) -> PhaseDependencyEvaluation:
        checks: list[DependencyRequirementCheck] = []
        assessments: list[LimitationAssessment] = []
        constraints = list(requirements.base_constraints)
        constraints.extend(f"prohibit_effect:{item}" for item in requirements.prohibited_effects)
        constraints.extend(f"disclose_limitation:{item}" for item in snapshot.required_disclosures)
        risk_constraints = self._unique([*requirements.risk_constraints, *snapshot.risk_constraints])
        constraints.extend(f"risk_constraint:{item}" for item in risk_constraints)
        blocking: list[str] = []
        unknown: list[str] = []

        compiled_requirement_reason = self._compiled_requirement_reason(requirements)
        if compiled_requirement_reason:
            unknown.append(compiled_requirement_reason)

        self._check_binding(snapshot.dependency_id, "dependency_id", unknown)
        self._check_binding(snapshot.producer_task_run_id, "producer_task_run_id", unknown)
        self._check_binding(snapshot.producer_operation_id or "", "producer_operation_id", unknown)
        self._check_binding(snapshot.producer_phase_id, "producer_phase_id", unknown)
        self._check_binding(snapshot.upstream_result_ref, "upstream_result_ref", unknown)
        self._check_binding(consumer_task_run_id, "consumer_task_run_id", unknown)
        self._check_binding(consumer_operation_id, "consumer_operation_id", unknown)
        self._check_binding(consumer_operation_type, "consumer_operation_type", unknown)
        self._check_binding(requirements.consumer_phase_id, "consumer_phase_id", unknown)
        self._check_value(
            checks,
            blocking,
            name="consumer_operation_type",
            expected=[requirements.operation_type],
            observed=consumer_operation_type,
            blocked_reason="PHASE_DEPENDENCY_DOWNSTREAM_OPERATION_MISMATCH",
        )

        self._check_value(
            checks,
            blocking,
            name="dependency_status",
            expected=requirements.allowed_dependency_statuses,
            observed=snapshot.dependency_status,
            blocked_reason="PHASE_DEPENDENCY_NOT_SATISFIED",
        )
        if requirements.evidence_required and not snapshot.evidence_refs:
            unknown.append("PHASE_DEPENDENCY_EVIDENCE_REQUIRED")
            checks.append(
                DependencyRequirementCheck(
                    requirement="evidence_refs",
                    expected=["non_empty"],
                    observed=[],
                    status="unknown",
                    reason_code="PHASE_DEPENDENCY_EVIDENCE_REQUIRED",
                )
            )

        for required_use in requirements.required_downstream_uses:
            allowed = required_use in snapshot.allowed_downstream_uses
            reason = None if allowed else "PHASE_DEPENDENCY_DOWNSTREAM_USE_NOT_ALLOWED"
            checks.append(
                DependencyRequirementCheck(
                    requirement=f"allowed_downstream_use:{required_use}",
                    expected=[True],
                    observed=allowed,
                    status="satisfied" if allowed else "blocked",
                    reason_code=reason,
                )
            )
            if not allowed:
                blocking.append(str(reason))
            if required_use in snapshot.forbidden_downstream_uses:
                blocking.append("PHASE_DEPENDENCY_DOWNSTREAM_USE_FORBIDDEN")

        for name, expected in requirements.required_use_safety.items():
            self._check_mapping_value(
                checks,
                blocking,
                unknown,
                mapping=snapshot.use_safety,
                namespace="use_safety",
                name=name,
                expected=expected,
            )
        for name, expected in requirements.required_semantic_properties.items():
            self._check_mapping_value(
                checks,
                blocking,
                unknown,
                mapping=snapshot.semantic_properties,
                namespace="semantic_property",
                name=name,
                expected=expected,
            )

        unclassified_limitations = [
            limitation
            for limitation in snapshot.limitations
            if limitation not in requirements.limitation_compatibility
        ]
        semantic_limitation_resolution = self.limitation_resolver.resolve(
            requirements=requirements,
            snapshot=snapshot,
            limitations=unclassified_limitations,
        )
        if (
            unclassified_limitations
            and semantic_limitation_resolution.get("status") == "insufficient_evidence"
        ):
            unknown.append(
                str(
                    semantic_limitation_resolution.get("reason_code")
                    or "PHASE_DEPENDENCY_LIMITATION_COMPATIBILITY_UNKNOWN"
                )
            )
        semantic_assessments = dict(
            semantic_limitation_resolution.get("assessments") or {}
        )

        for limitation in snapshot.limitations:
            impact = requirements.limitation_compatibility.get(limitation)
            source = "downstream_contract"
            limitation_constraints: list[str] = []
            if impact is None:
                semantic_assessment = semantic_assessments.get(limitation)
                if isinstance(semantic_assessment, dict):
                    impact = str(semantic_assessment.get("impact") or "UNKNOWN")
                    source = "semantic_reasoner"
                    limitation_constraints = [
                        str(item)
                        for item in semantic_assessment.get("constraints") or []
                        if str(item)
                    ]
                else:
                    impact = "UNKNOWN"
                    source = "unclassified"
            if impact == "COMPATIBLE_WITH_CONSTRAINT":
                limitation_constraints = self._unique(
                    [
                        *limitation_constraints,
                        f"disclose_limitation:{limitation}",
                    ]
                )
                constraints.extend(limitation_constraints)
            elif impact == "INCOMPATIBLE":
                blocking.append("PHASE_DEPENDENCY_LIMITATION_INCOMPATIBLE")
            elif impact == "UNKNOWN":
                unknown.append("PHASE_DEPENDENCY_LIMITATION_COMPATIBILITY_UNKNOWN")
            assessments.append(
                LimitationAssessment(
                    limitation=limitation,
                    impact=impact,  # type: ignore[arg-type]
                    source=source,  # type: ignore[arg-type]
                    constraints=limitation_constraints,
                )
            )

        constraints.extend(f"forbid_claim:{item}" for item in snapshot.forbidden_claims)
        reason_codes = self._unique([*blocking, *unknown])
        if blocking:
            decision = "BLOCKED"
            evaluation_status = "completed"
        elif unknown:
            decision = "INSUFFICIENT_EVIDENCE"
            evaluation_status = "incomplete"
        elif constraints or snapshot.dependency_status == "satisfied_with_limitations":
            decision = "ADMITTED_WITH_CONSTRAINTS"
            evaluation_status = "completed"
            reason_codes = ["PHASE_DEPENDENCY_ADMITTED_WITH_CONSTRAINTS"]
        else:
            decision = "ADMITTED"
            evaluation_status = "completed"
            reason_codes = ["PHASE_DEPENDENCY_ADMITTED"]

        evaluated_at = datetime.now(timezone.utc)
        evaluation = PhaseDependencyEvaluation(
            dependency_id=snapshot.dependency_id,
            producer_task_run_id=snapshot.producer_task_run_id,
            producer_operation_id=snapshot.producer_operation_id,
            consumer_task_run_id=consumer_task_run_id,
            consumer_operation_id=consumer_operation_id,
            consumer_operation_type=consumer_operation_type,
            producer_phase_id=snapshot.producer_phase_id,
            consumer_phase_id=requirements.consumer_phase_id,
            upstream_result_ref=snapshot.upstream_result_ref,
            downstream_contract_id=requirements.contract_id,
            downstream_contract_version=requirements.contract_version,
            requirements_sha256=self.requirements_sha256(requirements),
            dependency_status=snapshot.dependency_status,
            evaluation_status=evaluation_status,  # type: ignore[arg-type]
            decision=decision,  # type: ignore[arg-type]
            reason_codes=reason_codes,
            requirement_checks=checks,
            limitation_assessments=assessments,
            missing_truth=self._unique(snapshot.missing_truth),
            risk_constraints=risk_constraints,
            constraints=self._unique(constraints),
            evidence_refs=self._unique(snapshot.evidence_refs),
            evaluated_at=evaluated_at.isoformat(),
            expires_at=(evaluated_at + timedelta(seconds=max(1, requirements.authorization_ttl_seconds))).isoformat(),
        )
        evaluation.authority_sha256 = self._model_sha256(evaluation, exclude={"authority_sha256"})
        return evaluation

    def authorize(
        self,
        *,
        evaluation: PhaseDependencyEvaluation,
        requirements: DownstreamPhaseRequirements,
        consumer_task_run_id: str,
        consumer_operation_id: str,
        consumer_operation_type: str,
        producer_task_run_id: str,
        producer_operation_id: str | None,
        dependency_id: str,
        producer_phase_id: str,
        consumer_phase_id: str,
        consumed_evaluation_ids: set[str] | None = None,
        now: datetime | None = None,
    ) -> PhaseDependencyAdmission:
        reason = self._authorization_failure(
            evaluation=evaluation,
            requirements=requirements,
            consumer_task_run_id=consumer_task_run_id,
            consumer_operation_id=consumer_operation_id,
            consumer_operation_type=consumer_operation_type,
            producer_task_run_id=producer_task_run_id,
            producer_operation_id=producer_operation_id,
            dependency_id=dependency_id,
            producer_phase_id=producer_phase_id,
            consumer_phase_id=consumer_phase_id,
            consumed_evaluation_ids=consumed_evaluation_ids if consumed_evaluation_ids is not None else set(),
            now=now or datetime.now(timezone.utc),
        )
        authorized = reason is None and evaluation.decision in {"ADMITTED", "ADMITTED_WITH_CONSTRAINTS"}
        if reason is None and not authorized:
            reason = evaluation.reason_codes[0] if evaluation.reason_codes else "PHASE_DEPENDENCY_NOT_ADMITTED"
        admission = PhaseDependencyAdmission(
            evaluation_id=evaluation.evaluation_id,
            dependency_id=evaluation.dependency_id,
            producer_task_run_id=evaluation.producer_task_run_id,
            producer_operation_id=evaluation.producer_operation_id,
            consumer_task_run_id=evaluation.consumer_task_run_id,
            consumer_operation_id=evaluation.consumer_operation_id,
            consumer_operation_type=evaluation.consumer_operation_type,
            producer_phase_id=evaluation.producer_phase_id,
            consumer_phase_id=evaluation.consumer_phase_id,
            downstream_contract_id=evaluation.downstream_contract_id,
            requirements_sha256=evaluation.requirements_sha256,
            evaluation_authority_sha256=evaluation.authority_sha256,
            authorized=authorized,
            decision=evaluation.decision,
            reason_code=reason or (
                "PHASE_DEPENDENCY_ADMITTED_WITH_CONSTRAINTS"
                if evaluation.decision == "ADMITTED_WITH_CONSTRAINTS"
                else "PHASE_DEPENDENCY_ADMITTED"
            ),
            missing_truth=list(evaluation.missing_truth),
            risk_constraints=list(evaluation.risk_constraints),
            constraints=list(evaluation.constraints) if authorized else [],
            evidence_refs=list(evaluation.evidence_refs) if authorized else [],
            expires_at=evaluation.expires_at,
        )
        admission.authority_sha256 = self._model_sha256(admission, exclude={"authority_sha256"})
        if authorized and consumed_evaluation_ids is not None:
            consumed_evaluation_ids.add(evaluation.evaluation_id)
        return admission

    def validate_admission(
        self,
        admission: PhaseDependencyAdmission,
        *,
        evaluation: PhaseDependencyEvaluation,
        requirements: DownstreamPhaseRequirements,
        consumer_task_run_id: str,
        consumer_operation_id: str,
        consumer_operation_type: str,
        producer_task_run_id: str,
        producer_operation_id: str | None,
        dependency_id: str,
        producer_phase_id: str,
        consumer_phase_id: str,
    ) -> tuple[bool, str | None]:
        if admission.authority_sha256 != self._model_sha256(admission, exclude={"authority_sha256"}):
            return False, "PHASE_DEPENDENCY_ADMISSION_TAMPERED"
        if evaluation.authority_sha256 != self._model_sha256(evaluation, exclude={"authority_sha256"}):
            return False, "PHASE_DEPENDENCY_EVALUATION_TAMPERED"
        if admission.evaluation_id != evaluation.evaluation_id or admission.evaluation_authority_sha256 != evaluation.authority_sha256:
            return False, "PHASE_DEPENDENCY_EVALUATION_BINDING_MISMATCH"
        if self._parse_time(admission.expires_at) <= datetime.now(timezone.utc):
            return False, "PHASE_DEPENDENCY_ADMISSION_STALE"
        expected = {
            "consumer_task_run_id": consumer_task_run_id,
            "consumer_operation_id": consumer_operation_id,
            "consumer_operation_type": consumer_operation_type,
            "producer_task_run_id": producer_task_run_id,
            "producer_operation_id": producer_operation_id,
            "dependency_id": dependency_id,
            "producer_phase_id": producer_phase_id,
            "consumer_phase_id": consumer_phase_id,
            "downstream_contract_id": requirements.contract_id,
            "requirements_sha256": self.requirements_sha256(requirements),
        }
        for name, value in expected.items():
            if getattr(admission, name) != value:
                return False, "PHASE_DEPENDENCY_ADMISSION_BINDING_MISMATCH"
        if not admission.authorized:
            return False, admission.reason_code
        return True, None

    def requirements_sha256(self, requirements: DownstreamPhaseRequirements) -> str:
        return self._model_sha256(requirements)

    def _compiled_requirement_reason(self, requirements: DownstreamPhaseRequirements) -> str | None:
        if not requirements.authority_source.startswith("compiled_task_semantics"):
            return None
        if not all(
            (
                requirements.source_plan_id,
                requirements.source_execution_id,
                requirements.source_semantics_sha256,
                requirements.frozen_at,
            )
        ):
            return "PHASE_DEPENDENCY_COMPILED_REQUIREMENTS_SOURCE_BINDING_REQUIRED"
        present = {item.requirement for item in requirements.requirement_provenance}
        required = {"operation_type", "allowed_dependency_statuses", "evidence_required"}
        required.update(f"required_downstream_use:{item}" for item in requirements.required_downstream_uses)
        required.update(f"required_use_safety:{item}" for item in requirements.required_use_safety)
        required.update(f"required_semantic_property:{item}" for item in requirements.required_semantic_properties)
        required.update(f"required_capability:{item}" for item in requirements.required_capabilities)
        required.update(f"limitation_compatibility:{item}" for item in requirements.limitation_compatibility)
        required.update(f"base_constraint:{item}" for item in requirements.base_constraints)
        required.update(f"risk_constraint:{item}" for item in requirements.risk_constraints)
        required.update(f"prohibited_effect:{item}" for item in requirements.prohibited_effects)
        if not required.issubset(present):
            return "PHASE_DEPENDENCY_COMPILED_REQUIREMENTS_PROVENANCE_REQUIRED"
        return None

    def _authorization_failure(
        self,
        *,
        evaluation: PhaseDependencyEvaluation,
        requirements: DownstreamPhaseRequirements,
        consumer_task_run_id: str,
        consumer_operation_id: str,
        consumer_operation_type: str,
        producer_task_run_id: str,
        producer_operation_id: str | None,
        dependency_id: str,
        producer_phase_id: str,
        consumer_phase_id: str,
        consumed_evaluation_ids: set[str],
        now: datetime,
    ) -> str | None:
        if evaluation.authority_sha256 != self._model_sha256(evaluation, exclude={"authority_sha256"}):
            return "PHASE_DEPENDENCY_EVALUATION_TAMPERED"
        if evaluation.evaluation_status != "completed":
            return "PHASE_DEPENDENCY_EVALUATION_INCOMPLETE"
        if evaluation.evaluation_id in consumed_evaluation_ids:
            return "PHASE_DEPENDENCY_EVALUATION_REPLAYED"
        if self._parse_time(evaluation.expires_at) <= now:
            return "PHASE_DEPENDENCY_EVALUATION_STALE"
        expected = {
            "consumer_task_run_id": consumer_task_run_id,
            "consumer_operation_id": consumer_operation_id,
            "consumer_operation_type": consumer_operation_type,
            "producer_task_run_id": producer_task_run_id,
            "producer_operation_id": producer_operation_id,
            "dependency_id": dependency_id,
            "producer_phase_id": producer_phase_id,
            "consumer_phase_id": consumer_phase_id,
            "downstream_contract_id": requirements.contract_id,
            "downstream_contract_version": requirements.contract_version,
            "requirements_sha256": self.requirements_sha256(requirements),
        }
        for name, value in expected.items():
            if getattr(evaluation, name) != value:
                return "PHASE_DEPENDENCY_EVALUATION_BINDING_MISMATCH"
        return None

    def _check_mapping_value(
        self,
        checks: list[DependencyRequirementCheck],
        blocking: list[str],
        unknown: list[str],
        *,
        mapping: dict[str, Any],
        namespace: str,
        name: str,
        expected: list[Any],
    ) -> None:
        if name not in mapping:
            reason = (
                "PHASE_DEPENDENCY_REQUIRED_USE_SAFETY_UNKNOWN"
                if namespace == "use_safety"
                else "PHASE_DEPENDENCY_REQUIRED_SEMANTIC_PROPERTY_UNKNOWN"
            )
            unknown.append(reason)
            checks.append(
                DependencyRequirementCheck(
                    requirement=f"{namespace}:{name}",
                    expected=expected,
                    observed=None,
                    status="unknown",
                    reason_code=reason,
                )
            )
            return
        reason = (
            "PHASE_DEPENDENCY_REQUIRED_USE_SAFETY_UNSATISFIED"
            if namespace == "use_safety"
            else "PHASE_DEPENDENCY_REQUIRED_SEMANTIC_PROPERTY_UNSATISFIED"
        )
        self._check_value(
            checks,
            blocking,
            name=f"{namespace}:{name}",
            expected=expected,
            observed=mapping[name],
            blocked_reason=reason,
        )

    def _check_value(
        self,
        checks: list[DependencyRequirementCheck],
        blocking: list[str],
        *,
        name: str,
        expected: list[Any],
        observed: Any,
        blocked_reason: str,
    ) -> None:
        satisfied = observed in expected
        checks.append(
            DependencyRequirementCheck(
                requirement=name,
                expected=expected,
                observed=observed,
                status="satisfied" if satisfied else "blocked",
                reason_code=None if satisfied else blocked_reason,
            )
        )
        if not satisfied:
            blocking.append(blocked_reason)

    def _check_binding(self, value: str, name: str, unknown: list[str]) -> None:
        if not str(value or "").strip():
            unknown.append(f"PHASE_DEPENDENCY_BINDING_MISSING:{name}")

    def _model_sha256(self, value: Any, *, exclude: set[str] | None = None) -> str:
        payload = value.model_dump(mode="json", exclude=exclude or set()) if hasattr(value, "model_dump") else value
        encoded = json.dumps(payload, sort_keys=True, ensure_ascii=True, separators=(",", ":")).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

    def _parse_time(self, value: str) -> datetime:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)

    def _unique(self, values: list[str]) -> list[str]:
        return list(dict.fromkeys(str(item) for item in values if str(item)))
