from __future__ import annotations

import hashlib
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

        deterministic = self._resolve_from_governed_use_safety(
            requirements=requirements,
            snapshot=snapshot,
            limitations=targets,
        )
        if deterministic is not None:
            return deterministic

        binding_by_id = self._limitation_bindings(targets)
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
                    "limitation_bindings": [
                        {
                            "limitation_id": limitation_id,
                            "description": limitation,
                        }
                        for limitation_id, limitation in binding_by_id.items()
                    ],
                    "missing_truth": list(snapshot.missing_truth),
                    "allowed_downstream_uses": list(snapshot.allowed_downstream_uses),
                    "forbidden_downstream_uses": list(snapshot.forbidden_downstream_uses),
                    "forbidden_claims": list(snapshot.forbidden_claims),
                    "use_safety": dict(snapshot.use_safety),
                    "semantic_properties": dict(snapshot.semantic_properties),
                },
                "allowed_impacts": sorted(_ALLOWED_IMPACTS),
                "output_schema": {
                    "assessments": {
                        "type": "list",
                        "item": {
                            "limitation_id": {
                                "type": "string",
                                "enum": list(binding_by_id),
                            },
                            "impact": {
                                "type": "string",
                                "enum": sorted(_ALLOWED_IMPACTS),
                            },
                            "constraints": "list[string]",
                            "rationale": "non_empty_string",
                        },
                        "required_count": len(binding_by_id),
                    },
                    "confidence": "number_between_0_and_1",
                    "rationale": "non_empty_string",
                },
                "rules": [
                    "Assess every supplied limitation_id exactly once.",
                    "Copy limitation_id exactly from upstream_context.limitation_bindings; never use a description or schema placeholder as the identifier.",
                    "impact must be exactly one value from allowed_impacts.",
                    "constraints MUST be [] unless impact is exactly COMPATIBLE_WITH_CONSTRAINT.",
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
        seen_binding_ids: set[str] = set()
        for item in raw_assessments:
            if not isinstance(item, dict):
                return self._invalid(proposal, "LIMITATION_COMPATIBILITY_ASSESSMENT_INVALID")
            limitation_id = str(item.get("limitation_id") or "").strip()
            impact = str(item.get("impact") or "")
            constraints = item.get("constraints")
            rationale = str(item.get("rationale") or "").strip()
            limitation = binding_by_id.get(limitation_id)
            if limitation is None or limitation_id in seen_binding_ids:
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
            seen_binding_ids.add(limitation_id)
            assessments[limitation] = {
                "impact": impact,
                "constraints": list(dict.fromkeys(constraints)),
                "rationale": rationale,
            }

        if seen_binding_ids != set(binding_by_id):
            return self._invalid(proposal, "LIMITATION_COMPATIBILITY_COVERAGE_REQUIRED")

        return {
            "status": "accepted",
            "assessments": assessments,
            "confidence": confidence,
            "rationale": str(candidate.get("rationale") or ""),
            "provenance": self._provenance(proposal),
        }

    def _resolve_from_governed_use_safety(
        self,
        *,
        requirements: DownstreamPhaseRequirements,
        snapshot: PhaseDependencySnapshot,
        limitations: list[str],
    ) -> dict[str, Any] | None:
        """Use explicit producer safety for a matching generic consumer class.

        This is not inference and grants no authority. It only interprets an
        already-governed upstream safety statement against frozen downstream
        requirements. Missing safety still falls through to fail-closed
        semantic interpretation.
        """
        prohibited = set(requirements.prohibited_effects)
        capabilities = set(requirements.required_capabilities)
        readonly_analysis = (
            "read_workspace" in capabilities
            and "workspace_mutation" in prohibited
            and "destructive_action" in prohibited
        )
        if not readonly_analysis:
            return None
        safety = snapshot.use_safety.get("safe_for_downstream_static_analysis")
        if safety not in {True, False, "true_with_limitations"}:
            return None
        if safety is False:
            impact = "INCOMPATIBLE"
            constraints: list[str] = []
            rationale = "Producer explicitly marks downstream static analysis unsafe."
        elif safety == "true_with_limitations":
            impact = "COMPATIBLE_WITH_CONSTRAINT"
            constraints = []
            rationale = "Producer explicitly allows downstream static analysis with disclosed limitations."
        else:
            impact = "COMPATIBLE"
            constraints = []
            rationale = "Producer explicitly allows downstream static analysis."
        return {
            "status": "accepted",
            "assessments": {
                limitation: {
                    "impact": impact,
                    "constraints": list(constraints),
                    "rationale": rationale,
                    "source": "upstream_disclosure",
                }
                for limitation in limitations
            },
            "confidence": 1.0,
            "rationale": rationale,
            "provenance": {
                "authority": "deterministic_semantic_gate",
                "source": "producer_use_safety",
                "use_safety_key": "safe_for_downstream_static_analysis",
                "observed_value": safety,
            },
        }

    @staticmethod
    def _limitation_bindings(limitations: list[str]) -> dict[str, str]:
        bindings: dict[str, str] = {}
        for limitation in limitations:
            digest = hashlib.sha256(limitation.encode("utf-8")).hexdigest()
            width = 12
            limitation_id = f"lim_{digest[:width]}"
            while (
                limitation_id in bindings
                and bindings[limitation_id] != limitation
            ):
                width += 4
                limitation_id = f"lim_{digest[:width]}"
            bindings[limitation_id] = limitation
        return bindings

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
