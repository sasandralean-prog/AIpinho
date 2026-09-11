from __future__ import annotations

from typing import Any

from aipinho.schemas.artifacts.observed_entity import (
    RootRoleCandidate,
    RootRoleDecision,
    WorkspaceRootRole,
)
from aipinho.services.semantics.contract_bound_semantic_reasoner import ContractBoundSemanticReasoner


_ALLOWED_ROLES: tuple[WorkspaceRootRole, ...] = (
    "project_root",
    "source_code_root",
    "library_root",
    "corpus_root",
    "artifact_root",
    "external_root",
    "build_output_root",
    "cache_root",
    "generated_root",
    "unknown_root",
)


class RootRoleResolverService:
    """Resolve a path role relative to the current semantic intent.

    Explicit user/context declarations are stronger evidence than model
    proposals. The model only proposes; deterministic validation decides.
    """

    def __init__(
        self,
        *,
        reasoner: ContractBoundSemanticReasoner | None = None,
        minimum_model_confidence: float = 0.62,
    ) -> None:
        self.reasoner = reasoner or ContractBoundSemanticReasoner()
        self.minimum_model_confidence = max(0.0, min(1.0, minimum_model_confidence))

    def resolve(
        self,
        *,
        path: str,
        prompt: str,
        intent_map: dict[str, Any] | None = None,
        explicit_role: str | None = None,
        context_role: str | None = None,
        allow_model_inference: bool = True,
    ) -> RootRoleDecision:
        candidates: list[RootRoleCandidate] = []
        explicit = self._valid_role(explicit_role)
        contextual = self._valid_role(context_role)
        if explicit:
            candidates.append(
                RootRoleCandidate(
                    role=explicit,
                    confidence=1.0,
                    rationale="Role explicitly bound by prompt analysis.",
                    source="prompt_explicit_role",
                    evidence_refs=[f"prompt:path:{path}", "prompt:root_role_label"],
                )
            )
        if contextual:
            candidates.append(
                RootRoleCandidate(
                    role=contextual,
                    confidence=0.98,
                    rationale="Role explicitly supplied by governed workspace context.",
                    source="workspace_context",
                    evidence_refs=[f"workspace_context:path:{path}"],
                )
            )
        deterministic = self._deterministic_choice(path=path, candidates=candidates)
        if deterministic is not None:
            return deterministic

        if not allow_model_inference:
            return RootRoleDecision(
                path=path,
                role="unknown_root",
                confidence=0.0,
                status="unknown",
                candidates=candidates,
                evidence_refs=[f"prompt:path:{path}"],
                deterministic_validation_status="passed",
                reason_codes=["ROOT_ROLE_SEMANTIC_INTERPRETATION_REQUIRED"],
                provenance={"authority": "deterministic_gate", "model_used": False},
            )

        proposal = self.reasoner.propose_json(
            semantic_goal=(
                "Classify the semantic role of this filesystem path relative to "
                "the user's current request. Role is contextual, not intrinsic."
            ),
            payload={
                "path": path,
                "prompt": prompt,
                "intent_map": intent_map or {},
                "allowed_roles": list(_ALLOWED_ROLES),
                "rules": [
                    "Use only allowed_roles.",
                    "Do not infer permissions.",
                    "Do not classify a project workspace as a corpus merely because another path exists.",
                    "If evidence is insufficient, use unknown_root.",
                ],
            },
            allowed_fields=["role", "confidence", "rationale", "evidence_refs"],
            required_fields=["role", "confidence", "rationale"],
        )
        if proposal.get("status") != "candidate":
            return RootRoleDecision(
                path=path,
                role="unknown_root",
                confidence=0.0,
                status="unknown",
                candidates=candidates,
                evidence_refs=[f"prompt:path:{path}"],
                model_id=proposal.get("model_id"),
                model_response_id=proposal.get("response_id"),
                deterministic_validation_status="passed",
                reason_codes=[
                    "ROOT_ROLE_MODEL_PROPOSAL_UNAVAILABLE",
                    str(proposal.get("reason_code") or ""),
                ],
                provenance={"authority": "deterministic_gate", "model_status": proposal.get("status")},
            )
        raw = proposal.get("candidate") or {}
        role = self._valid_role(raw.get("role"))
        confidence = self._confidence(raw.get("confidence"))
        model_candidate = RootRoleCandidate(
            role=role or "unknown_root",
            confidence=confidence,
            rationale=str(raw.get("rationale") or ""),
            source="contract_bound_semantic_reasoner",
            evidence_refs=[
                *[str(item) for item in raw.get("evidence_refs") or [] if item],
                f"prompt:path:{path}",
            ],
        )
        candidates.append(model_candidate)
        if role is None:
            return self._blocked(path, candidates, proposal, "ROOT_ROLE_MODEL_ROLE_OUTSIDE_CONTRACT")
        if role == "unknown_root" or confidence < self.minimum_model_confidence:
            return RootRoleDecision(
                path=path,
                role="unknown_root",
                confidence=confidence,
                status="ambiguous" if role != "unknown_root" else "unknown",
                candidates=candidates,
                evidence_refs=list(model_candidate.evidence_refs),
                model_id=proposal.get("model_id"),
                model_response_id=proposal.get("response_id"),
                deterministic_validation_status="passed",
                reason_codes=["ROOT_ROLE_CONFIDENCE_INSUFFICIENT"],
                provenance={
                    "authority": "deterministic_gate",
                    "candidate_source": "model",
                    "model_real_inference": proposal.get("real_inference"),
                },
            )
        return RootRoleDecision(
            path=path,
            role=role,
            confidence=confidence,
            status="resolved",
            candidates=candidates,
            evidence_refs=list(model_candidate.evidence_refs),
            model_id=proposal.get("model_id"),
            model_response_id=proposal.get("response_id"),
            deterministic_validation_status="passed",
            reason_codes=[],
            provenance={
                "authority": "deterministic_gate",
                "candidate_source": "model",
                "model_real_inference": proposal.get("real_inference"),
                "model_evaluation_status": proposal.get("evaluation_status"),
            },
        )

    def _deterministic_choice(
        self,
        *,
        path: str,
        candidates: list[RootRoleCandidate],
    ) -> RootRoleDecision | None:
        if not candidates:
            return None
        roles = list(dict.fromkeys(candidate.role for candidate in candidates))
        if len(roles) > 1:
            return RootRoleDecision(
                path=path,
                role="unknown_root",
                confidence=max(candidate.confidence for candidate in candidates),
                status="ambiguous",
                candidates=candidates,
                evidence_refs=self._evidence(candidates),
                deterministic_validation_status="passed",
                reason_codes=["ROOT_ROLE_AUTHORITATIVE_EVIDENCE_CONFLICT"],
                provenance={"authority": "deterministic_gate"},
            )
        winner = max(candidates, key=lambda candidate: candidate.confidence)
        return RootRoleDecision(
            path=path,
            role=winner.role,
            confidence=winner.confidence,
            status="resolved",
            candidates=candidates,
            evidence_refs=self._evidence(candidates),
            deterministic_validation_status="passed",
            reason_codes=[],
            provenance={"authority": "deterministic_gate", "candidate_source": winner.source},
        )

    def _blocked(
        self,
        path: str,
        candidates: list[RootRoleCandidate],
        proposal: dict[str, Any],
        reason: str,
    ) -> RootRoleDecision:
        return RootRoleDecision(
            path=path,
            role="unknown_root",
            confidence=0.0,
            status="blocked",
            candidates=candidates,
            evidence_refs=self._evidence(candidates),
            model_id=proposal.get("model_id"),
            model_response_id=proposal.get("response_id"),
            deterministic_validation_status="blocked",
            reason_codes=[reason],
            provenance={"authority": "deterministic_gate"},
        )

    def _valid_role(self, value: Any) -> WorkspaceRootRole | None:
        role = str(value or "")
        return role if role in _ALLOWED_ROLES else None  # type: ignore[return-value]

    def _confidence(self, value: Any) -> float:
        try:
            return max(0.0, min(1.0, float(value)))
        except (TypeError, ValueError):
            return 0.0

    def _evidence(self, candidates: list[RootRoleCandidate]) -> list[str]:
        return list(
            dict.fromkeys(
                ref
                for candidate in candidates
                for ref in candidate.evidence_refs
                if ref
            )
        )
