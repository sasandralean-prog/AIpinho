from __future__ import annotations

import re
from typing import Any

from aipinho.schemas.semantics.task_semantic_vocabulary import TaskSemanticVocabulary
from aipinho.services.semantics.contract_bound_semantic_reasoner import (
    ContractBoundSemanticReasoner,
)
from aipinho.services.semantics.semantic_reasoning_playbook_service import (
    SemanticReasoningPlaybookService,
)


class SemanticDemandInterpreterService:
    """Interpret ambiguous downstream truth/use demand without granting authority."""

    _UNRESOLVED_REASON_CODES = {
        "task_semantics_ambiguous",
        "required_concept_not_in_vocabulary",
        "dependency_scope_ambiguous",
        "conflicting_task_semantics",
    }

    def __init__(
        self,
        *,
        reasoner: ContractBoundSemanticReasoner | None = None,
        playbook: SemanticReasoningPlaybookService | None = None,
    ) -> None:
        self.reasoner = reasoner
        self.playbook = playbook or SemanticReasoningPlaybookService()

    def interpret(
        self,
        *,
        source_payload: dict[str, Any],
        semantic_graph: dict[str, Any],
        vocabulary: TaskSemanticVocabulary | None = None,
    ) -> dict[str, Any]:
        if not bool(semantic_graph.get("knowledge_output")):
            return {
                "status": "not_required",
                "reason_code": None,
                "accepted_requirements": {},
                "provenance": {},
            }

        if vocabulary is None:
            return {
                "status": "insufficient_evidence",
                "reason_code": "SEMANTIC_DEMAND_TASK_VOCABULARY_REQUIRED",
                "accepted_requirements": {},
                "provenance": {},
            }

        reasoner = self.reasoner or ContractBoundSemanticReasoner()
        self.reasoner = reasoner
        try:
            reasoning_context = self.playbook.build_model_view(
                source_payload=source_payload,
                vocabulary=vocabulary,
            )
        except ValueError:
            return {
                "status": "insufficient_evidence",
                "reason_code": "SEMANTIC_DEMAND_TASK_VOCABULARY_AUTHORITY_INVALID",
                "accepted_requirements": {},
                "provenance": {
                    "vocabulary_id": vocabulary.vocabulary_id,
                    "vocabulary_authority_sha256": vocabulary.authority_sha256,
                    "authority": "deterministic_semantic_gate",
                },
            }
        governed_vocabulary = dict(
            reasoning_context.get("governed_vocabulary") or {}
        )
        governed_downstream_uses = sorted(
            {
                str(value)
                for value in governed_vocabulary.get(
                    "downstream_use_identifiers"
                )
                or []
                if str(value)
            }
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
                    "required_downstream_uses": {
                        "type": "list",
                        "item": {
                            "type": "string",
                            "enum": governed_downstream_uses,
                        },
                    },
                    "required_use_safety": "object[string,list[scalar]]",
                    "required_semantic_properties": "object[string,list[scalar]]",
                    "base_constraints": {
                        "type": "list",
                        "item": {
                            "type": "string",
                            "pattern": (
                                "^(do_not_|require_|preserve_|disclose_|"
                                "prohibit_|restrict_|scope_|avoid_|must_)"
                                "[a-z0-9_]*$"
                            ),
                        },
                    },
                    "risk_constraints": {
                        "type": "list",
                        "item": {
                            "type": "string",
                            "pattern": (
                                "^(do_not_|require_|preserve_|disclose_|"
                                "prohibit_|restrict_|scope_|avoid_|must_)"
                                "[a-z0-9_]*$"
                            ),
                        },
                    },
                    "resolution_status": {
                        "type": "string",
                        "enum": ["resolved", "unresolved"],
                    },
                    "unresolved_reason_codes": {
                        "type": "list",
                        "item": {
                            "type": "string",
                            "enum": sorted(self._UNRESOLVED_REASON_CODES),
                        },
                    },
                    "rationale": {
                        "type": "string",
                        "non_empty": True,
                    },
                },
                "instruction": (
                    "Apply the playbook to current_task_semantics. "
                    "Select identifiers only from governed_vocabulary. Empty "
                    "requirement lists or mappings are valid. Use resolution_status="
                    "resolved when the minimum requirement set can be determined, "
                    "including a confidently empty requirement set. Use unresolved "
                    "only when ambiguity or missing governed vocabulary prevents "
                    "determining the requirement set, and then provide one or more "
                    "allowed unresolved_reason_codes. Never invent an identifier."
                ),
            },
            allowed_fields=[
                "truth_claim_required",
                "required_downstream_uses",
                "required_use_safety",
                "required_semantic_properties",
                "base_constraints",
                "risk_constraints",
                "resolution_status",
                "unresolved_reason_codes",
                "rationale",
            ],
            required_fields=[
                "truth_claim_required",
                "required_downstream_uses",
                "required_use_safety",
                "required_semantic_properties",
                "base_constraints",
                "risk_constraints",
                "resolution_status",
                "unresolved_reason_codes",
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
        if validated["resolution_status"] == "unresolved":
            return {
                "status": "insufficient_evidence",
                "reason_code": "SEMANTIC_DEMAND_INTERPRETATION_UNRESOLVED",
                "accepted_requirements": {},
                "unresolved_reason_codes": list(
                    validated["unresolved_reason_codes"]
                ),
                "rationale": str(validated["rationale"]),
                "provenance": self._proposal_provenance(proposal),
            }

        required_use_safety = dict(validated["required_use_safety"])
        exact_requirement_states = dict(
            governed_vocabulary.get("use_safety_exact_requirement_states")
            or {}
        )
        for name in list(required_use_safety):
            exact_states = exact_requirement_states.get(name)
            if isinstance(exact_states, list) and exact_states:
                required_use_safety[name] = list(exact_states)

        if bool(validated["truth_claim_required"]):
            values = list(required_use_safety.get("safe_for_truth_claim") or [])
            if True not in values:
                values.append(True)
            required_use_safety["safe_for_truth_claim"] = values
        else:
            required_use_safety.pop("safe_for_truth_claim", None)

        steps = list(source_payload.get("steps") or [])
        if steps and not any(bool(step.get("side_effect")) for step in steps if isinstance(step, dict)):
            required_use_safety.pop("safe_for_destructive_action", None)

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
            "resolution_status": str(validated["resolution_status"]),
            "unresolved_reason_codes": list(
                validated["unresolved_reason_codes"]
            ),
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

        resolution_status = str(
            candidate.get("resolution_status") or ""
        ).strip().casefold()
        if resolution_status not in {"resolved", "unresolved"}:
            return {}, "SEMANTIC_DEMAND_RESOLUTION_STATUS_INVALID"
        unresolved_reason_codes = self._string_list(
            candidate.get("unresolved_reason_codes")
        )
        if any(
            value not in self._UNRESOLVED_REASON_CODES
            for value in unresolved_reason_codes
        ):
            return {}, "SEMANTIC_DEMAND_UNRESOLVED_REASON_INVALID"
        if resolution_status == "resolved" and unresolved_reason_codes:
            return {}, "SEMANTIC_DEMAND_RESOLUTION_CONFLICT"
        if resolution_status == "unresolved" and not unresolved_reason_codes:
            return {}, "SEMANTIC_DEMAND_UNRESOLVED_REASON_REQUIRED"

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
        if (
            bool(candidate["truth_claim_required"])
            and "safe_for_truth_claim" not in governed_safety
        ):
            return {}, "SEMANTIC_DEMAND_TRUTH_REQUIREMENT_OUT_OF_SCOPE"
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
        allowed_property_states = governed_vocabulary.get(
            "semantic_property_requirement_states"
        )
        allowed_property_states = (
            dict(allowed_property_states)
            if isinstance(allowed_property_states, dict)
            else {}
        )
        for name, values in required_semantic_properties.items():
            allowed = list(allowed_property_states.get(name) or [])
            if not allowed or any(value not in allowed for value in values):
                return {}, "SEMANTIC_DEMAND_SEMANTIC_PROPERTY_STATE_INVALID"

        return {
            "truth_claim_required": candidate["truth_claim_required"],
            "required_downstream_uses": required_downstream_uses,
            "required_use_safety": required_use_safety,
            "required_semantic_properties": required_semantic_properties,
            "base_constraints": base_constraints,
            "risk_constraints": risk_constraints,
            "resolution_status": resolution_status,
            "unresolved_reason_codes": unresolved_reason_codes,
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
