from __future__ import annotations

import re
from typing import Any

from aipinho.services.semantics.contract_bound_semantic_reasoner import (
    ContractBoundSemanticReasoner,
)
from aipinho.services.semantics.semantic_reasoning_playbook_service import (
    SemanticReasoningPlaybookService,
)


class SemanticDemandInterpreterService:
    """Interpret ambiguous downstream truth/use demand without granting authority."""

    def __init__(
        self,
        *,
        reasoner: ContractBoundSemanticReasoner | None = None,
        playbook: SemanticReasoningPlaybookService | None = None,
        minimum_confidence: float = 0.65,
    ) -> None:
        self.reasoner = reasoner
        self.playbook = playbook or SemanticReasoningPlaybookService()
        self.minimum_confidence = max(0.0, min(1.0, minimum_confidence))

    def interpret(
        self,
        *,
        source_payload: dict[str, Any],
        semantic_graph: dict[str, Any],
    ) -> dict[str, Any]:
        if not bool(semantic_graph.get("knowledge_output")):
            return {
                "status": "not_required",
                "reason_code": None,
                "accepted_requirements": {},
                "provenance": {},
            }

        reasoner = self.reasoner or ContractBoundSemanticReasoner()
        self.reasoner = reasoner
        reasoning_context = self.playbook.build(source_payload=source_payload)
        governed_vocabulary = dict(
            reasoning_context.get("governed_vocabulary") or {}
        )
        proposal = reasoner.propose_json(
            semantic_goal=(
                "Determine the minimum upstream semantic guarantees required by "
                "this downstream operation. Knowledge output does not by itself "
                "mean every upstream claim must be full truth."
            ),
            payload={
                "semantic_reasoning_context": reasoning_context,
                "output_schema": {
                    "truth_claim_required": "boolean",
                    "required_downstream_uses": "list[string]",
                    "required_use_safety": "object[string,list[scalar]]",
                    "required_semantic_properties": "object[string,list[scalar]]",
                    "base_constraints": "list[string]",
                    "risk_constraints": "list[string]",
                    "confidence": "number_between_0_and_1",
                    "rationale": "non_empty_string",
                },
                "instruction": (
                    "Apply the playbook to current_task_semantics. Examples and "
                    "counterexamples are illustrative only and MUST NOT be copied. "
                    "Select identifiers only from governed_vocabulary. If the "
                    "vocabulary has no identifier for a concept, leave that field "
                    "empty and lower confidence rather than inventing one."
                ),
            },
            allowed_fields=[
                "truth_claim_required",
                "required_downstream_uses",
                "required_use_safety",
                "required_semantic_properties",
                "base_constraints",
                "risk_constraints",
                "confidence",
                "rationale",
            ],
            required_fields=[
                "truth_claim_required",
                "required_downstream_uses",
                "required_use_safety",
                "required_semantic_properties",
                "base_constraints",
                "risk_constraints",
                "confidence",
                "rationale",
            ],
            role_id="semantic_interpreter",
            max_tokens=900,
        )
        if proposal.get("status") != "candidate":
            return {
                "status": "insufficient_evidence",
                "reason_code": str(
                    proposal.get("reason_code")
                    or "SEMANTIC_DEMAND_INTERPRETATION_UNAVAILABLE"
                ),
                "accepted_requirements": {},
                "provenance": self._proposal_provenance(proposal),
            }

        candidate = proposal.get("candidate") or {}
        validated, reason = self._validate_candidate(
            candidate,
            governed_vocabulary=governed_vocabulary,
        )
        if reason:
            return {
                "status": "insufficient_evidence",
                "reason_code": reason,
                "accepted_requirements": {},
                "provenance": self._proposal_provenance(proposal),
            }
        confidence = float(validated["confidence"])
        if confidence < self.minimum_confidence:
            return {
                "status": "insufficient_evidence",
                "reason_code": "SEMANTIC_DEMAND_INTERPRETATION_CONFIDENCE_INSUFFICIENT",
                "accepted_requirements": {},
                "provenance": self._proposal_provenance(proposal),
            }

        required_use_safety = dict(validated["required_use_safety"])
        if bool(validated["truth_claim_required"]):
            values = list(required_use_safety.get("safe_for_truth_claim") or [])
            if True not in values:
                values.append(True)
            required_use_safety["safe_for_truth_claim"] = values

        return {
            "status": "accepted",
            "reason_code": None,
            "accepted_requirements": {
                "required_downstream_uses": list(validated["required_downstream_uses"]),
                "required_use_safety": required_use_safety,
                "required_semantic_properties": dict(
                    validated["required_semantic_properties"]
                ),
                "base_constraints": list(validated["base_constraints"]),
                "risk_constraints": list(validated["risk_constraints"]),
            },
            "confidence": confidence,
            "rationale": str(validated["rationale"]),
            "provenance": self._proposal_provenance(proposal),
        }

    def _validate_candidate(
        self,
        candidate: dict[str, Any],
        *,
        governed_vocabulary: dict[str, Any],
    ) -> tuple[dict[str, Any], str | None]:
        if not isinstance(candidate.get("truth_claim_required"), bool):
            return {}, "SEMANTIC_DEMAND_TRUTH_REQUIREMENT_INVALID"
        try:
            confidence = float(candidate.get("confidence"))
        except (TypeError, ValueError):
            return {}, "SEMANTIC_DEMAND_CONFIDENCE_INVALID"
        if not 0.0 <= confidence <= 1.0:
            return {}, "SEMANTIC_DEMAND_CONFIDENCE_INVALID"

        required_downstream_uses = self._string_list(
            candidate.get("required_downstream_uses")
        )
        governed_uses = {
            str(value)
            for value in governed_vocabulary.get("downstream_use_identifiers") or []
            if str(value)
        }
        if any(value not in governed_uses for value in required_downstream_uses):
            return {}, "SEMANTIC_DEMAND_DOWNSTREAM_USE_UNGOVERNED"

        base_constraints = self._string_list(candidate.get("base_constraints"))
        risk_constraints = self._string_list(candidate.get("risk_constraints"))
        if any(not self._valid_constraint(value) for value in [*base_constraints, *risk_constraints]):
            return {}, "SEMANTIC_DEMAND_CONSTRAINT_INVALID"
        governed_capabilities = {
            str(value)
            for value in governed_vocabulary.get("capability_identifiers") or []
            if str(value)
        }
        if any(
            self._constraint_reclassifies_capability(value, governed_capabilities)
            for value in [*base_constraints, *risk_constraints]
        ):
            return {}, "SEMANTIC_DEMAND_CONSTRAINT_RECLASSIFIES_CAPABILITY"

        rationale = str(candidate.get("rationale") or "").strip()
        if not rationale:
            return {}, "SEMANTIC_DEMAND_RATIONALE_REQUIRED"

        required_use_safety = self._mapping(candidate.get("required_use_safety"))
        if required_use_safety is None:
            return {}, "SEMANTIC_DEMAND_USE_SAFETY_INVALID"
        governed_safety = {
            str(value)
            for value in governed_vocabulary.get("use_safety_dimensions") or []
            if str(value)
        }
        if any(
            re.fullmatch(r"safe_for_[a-z][a-z0-9_]*", key) is None
            or key not in governed_safety
            for key in required_use_safety
        ):
            return {}, "SEMANTIC_DEMAND_USE_SAFETY_DIMENSION_INVALID"
        allowed_requirement_states = governed_vocabulary.get(
            "use_safety_requirement_states"
        )
        allowed_requirement_states = (
            dict(allowed_requirement_states)
            if isinstance(allowed_requirement_states, dict)
            else {}
        )
        for name, values in required_use_safety.items():
            allowed = list(allowed_requirement_states.get(name) or [])
            if not allowed or any(value not in allowed for value in values):
                return {}, "SEMANTIC_DEMAND_USE_SAFETY_STATE_INVALID"

        required_semantic_properties = self._mapping(
            candidate.get("required_semantic_properties")
        )
        if required_semantic_properties is None:
            return {}, "SEMANTIC_DEMAND_SEMANTIC_PROPERTIES_INVALID"
        governed_properties = {
            str(value)
            for value in governed_vocabulary.get("semantic_property_identifiers") or []
            if str(value)
        }
        if any(
            re.fullmatch(r"[a-z][a-z0-9_]*", key) is None
            or key not in governed_properties
            for key in required_semantic_properties
        ):
            return {}, "SEMANTIC_DEMAND_SEMANTIC_PROPERTY_INVALID"

        return {
            "truth_claim_required": candidate["truth_claim_required"],
            "required_downstream_uses": required_downstream_uses,
            "required_use_safety": required_use_safety,
            "required_semantic_properties": required_semantic_properties,
            "base_constraints": base_constraints,
            "risk_constraints": risk_constraints,
            "confidence": confidence,
            "rationale": rationale,
        }, None

    def _governed_downstream_uses(
        self,
        source_payload: dict[str, Any],
    ) -> set[str]:
        values: set[str] = set()
        for container in (
            source_payload,
            source_payload.get("intent_map"),
            source_payload.get("semantic_intent_graph"),
        ):
            if not isinstance(container, dict):
                continue
            for field in (
                "allowed_downstream_uses",
                "required_downstream_uses",
                "downstream_uses",
            ):
                raw = container.get(field)
                if isinstance(raw, list):
                    values.update(str(item) for item in raw if str(item).strip())
        return values

    def _valid_constraint(self, value: str) -> bool:
        if re.fullmatch(r"[a-z][a-z0-9_]*", value) is None:
            return False
        return value.startswith(
            (
                "do_not_",
                "require_",
                "preserve_",
                "disclose_",
                "prohibit_",
                "restrict_",
                "scope_",
                "avoid_",
                "must_",
            )
        )

    def _constraint_reclassifies_capability(
        self,
        value: str,
        capabilities: set[str],
    ) -> bool:
        return any(
            value == f"{prefix}{capability}"
            for capability in capabilities
            for prefix in ("require_", "must_")
        )

    def _mapping(self, value: Any) -> dict[str, list[Any]] | None:
        if not isinstance(value, dict):
            return None
        normalized: dict[str, list[Any]] = {}
        for key, values in value.items():
            name = str(key or "").strip()
            if not name or not isinstance(values, list) or not values:
                return None
            if any(isinstance(item, (dict, list)) for item in values):
                return None
            normalized[name] = list(values)
        return normalized

    def _string_list(self, value: Any) -> list[str]:
        if not isinstance(value, list):
            return []
        return list(dict.fromkeys(str(item) for item in value if str(item).strip()))

    def _proposal_provenance(self, proposal: dict[str, Any]) -> dict[str, Any]:
        return {
            "model_id": proposal.get("model_id"),
            "response_id": proposal.get("response_id"),
            "real_inference": proposal.get("real_inference"),
            "evaluation_status": proposal.get("evaluation_status"),
            "warnings": list(proposal.get("warnings") or []),
            "authority": "deterministic_semantic_gate",
        }
