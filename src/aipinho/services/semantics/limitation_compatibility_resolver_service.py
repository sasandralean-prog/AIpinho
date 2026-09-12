from __future__ import annotations

from typing import Any

from aipinho.schemas.runtime.phase_dependency_evaluation import (
    DownstreamPhaseRequirements,
    PhaseDependencySnapshot,
)
from aipinho.services.semantics.contract_bound_semantic_reasoner import (
    ContractBoundSemanticReasoner,
)


_ALLOWED_IMPACTS = {
    "COMPATIBLE",
    "COMPATIBLE_WITH_CONSTRAINT",
    "INCOMPATIBLE",
    "NOT_APPLICABLE",
    "UNKNOWN",
}


class LimitationCompatibilityResolverService:
    """Interpret upstream limitations against frozen downstream requirements."""

    def __init__(
        self,
        *,
        reasoner: ContractBoundSemanticReasoner | None = None,
        minimum_confidence: float = 0.65,
    ) -> None:
        self.reasoner = reasoner
        self.minimum_confidence = max(0.0, min(1.0, minimum_confidence))

    def resolve(
        self,
        *,
        requirements: DownstreamPhaseRequirements,
        snapshot: PhaseDependencySnapshot,
        limitations: list[str],
    ) -> dict[str, Any]:
        targets = list(dict.fromkeys(str(item) for item in limitations if str(item)))
        if not targets:
            return {"status": "not_required", "assessments": {}, "provenance": {}}

        reasoner = self.reasoner or ContractBoundSemanticReasoner()
        self.reasoner = reasoner
        proposal = reasoner.propose_json(
            semantic_goal=(
                "Assess whether each upstream limitation is compatible with the "
                "already-frozen downstream semantic requirements. Do not change "
                "requirements and do not authorize execution."
            ),
            payload={
                "frozen_downstream_requirements": requirements.model_dump(mode="json"),
                "upstream_context": {
                    "limitations": targets,
                    "missing_truth": list(snapshot.missing_truth),
                    "allowed_downstream_uses": list(snapshot.allowed_downstream_uses),
                    "forbidden_downstream_uses": list(snapshot.forbidden_downstream_uses),
                    "forbidden_claims": list(snapshot.forbidden_claims),
                    "use_safety": dict(snapshot.use_safety),
                    "semantic_properties": dict(snapshot.semantic_properties),
                },
                "allowed_impacts": sorted(_ALLOWED_IMPACTS),
                "output_schema": {
                    "assessments": [
                        {
                            "limitation": "exact_input_limitation",
                            "impact": "allowed_impact",
                            "constraints": "list[string]",
                            "rationale": "non_empty_string",
                        }
                    ],
                    "confidence": "number_between_0_and_1",
                    "rationale": "non_empty_string",
                },
                "rules": [
                    "Assess every limitation exactly once.",
                    "UNKNOWN is required when evidence is insufficient.",
                    "A compatible result cannot override an unsatisfied explicit requirement.",
                    "Constraints may only restrict downstream behavior.",
                ],
            },
            allowed_fields=["assessments", "confidence", "rationale"],
            required_fields=["assessments", "confidence", "rationale"],
            role_id="semantic_interpreter",
            max_tokens=1100,
        )
        if proposal.get("status") != "candidate":
            return {
                "status": "insufficient_evidence",
                "reason_code": str(
                    proposal.get("reason_code")
                    or "LIMITATION_COMPATIBILITY_INTERPRETATION_UNAVAILABLE"
                ),
                "assessments": {},
                "provenance": self._provenance(proposal),
            }

        candidate = proposal.get("candidate") or {}
        try:
            confidence = float(candidate.get("confidence"))
        except (TypeError, ValueError):
            confidence = -1.0
        if not 0.0 <= confidence <= 1.0:
            return self._invalid(proposal, "LIMITATION_COMPATIBILITY_CONFIDENCE_INVALID")
        if confidence < self.minimum_confidence:
            return self._invalid(
                proposal,
                "LIMITATION_COMPATIBILITY_CONFIDENCE_INSUFFICIENT",
            )

        raw_assessments = candidate.get("assessments")
        if not isinstance(raw_assessments, list):
            return self._invalid(proposal, "LIMITATION_COMPATIBILITY_ASSESSMENTS_INVALID")

        assessments: dict[str, dict[str, Any]] = {}
        for item in raw_assessments:
            if not isinstance(item, dict):
                return self._invalid(proposal, "LIMITATION_COMPATIBILITY_ASSESSMENT_INVALID")
            limitation = str(item.get("limitation") or "")
            impact = str(item.get("impact") or "")
            constraints = item.get("constraints")
            rationale = str(item.get("rationale") or "").strip()
            if limitation not in targets or limitation in assessments:
                return self._invalid(proposal, "LIMITATION_COMPATIBILITY_BINDING_INVALID")
            if impact not in _ALLOWED_IMPACTS:
                return self._invalid(proposal, "LIMITATION_COMPATIBILITY_IMPACT_INVALID")
            if not isinstance(constraints, list) or any(
                not isinstance(value, str) or not value.strip()
                for value in constraints
            ):
                return self._invalid(proposal, "LIMITATION_COMPATIBILITY_CONSTRAINT_INVALID")
            if impact != "COMPATIBLE_WITH_CONSTRAINT" and constraints:
                return self._invalid(proposal, "LIMITATION_COMPATIBILITY_CONSTRAINT_SCOPE_INVALID")
            if not rationale:
                return self._invalid(proposal, "LIMITATION_COMPATIBILITY_RATIONALE_REQUIRED")
            assessments[limitation] = {
                "impact": impact,
                "constraints": list(dict.fromkeys(constraints)),
                "rationale": rationale,
            }

        if set(assessments) != set(targets):
            return self._invalid(proposal, "LIMITATION_COMPATIBILITY_COVERAGE_REQUIRED")

        return {
            "status": "accepted",
            "assessments": assessments,
            "confidence": confidence,
            "rationale": str(candidate.get("rationale") or ""),
            "provenance": self._provenance(proposal),
        }

    def _invalid(self, proposal: dict[str, Any], reason: str) -> dict[str, Any]:
        return {
            "status": "insufficient_evidence",
            "reason_code": reason,
            "assessments": {},
            "provenance": self._provenance(proposal),
        }

    def _provenance(self, proposal: dict[str, Any]) -> dict[str, Any]:
        return {
            "model_id": proposal.get("model_id"),
            "response_id": proposal.get("response_id"),
            "real_inference": proposal.get("real_inference"),
            "evaluation_status": proposal.get("evaluation_status"),
            "warnings": list(proposal.get("warnings") or []),
            "authority": "deterministic_semantic_gate",
        }
