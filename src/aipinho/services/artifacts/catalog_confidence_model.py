from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


FIELD_EPISTEMIC_STATUSES = {
    "observed",
    "inferred",
    "candidate",
    "unknown",
    "not_applicable",
    "unsupported",
    "read_error",
    "container_mismatch",
}


@dataclass(frozen=True)
class CatalogFieldEvidence:
    field_name: str
    value: Any
    status: str
    source: str
    source_method: str
    evidence_refs: list[str] = field(default_factory=list)
    confidence: float = 0.0
    limitations: list[str] = field(default_factory=list)
    risk_flags: list[str] = field(default_factory=list)
    promoted_to_truth: bool = False
    safe_for_truth_claim: bool = False

    def model_dump(self, *, mode: str = "python") -> dict[str, Any]:
        status = self.status if self.status in FIELD_EPISTEMIC_STATUSES else "unknown"
        return {
            "field_name": self.field_name,
            "value": self.value,
            "status": status,
            "source": self.source,
            "source_method": self.source_method,
            "evidence_refs": list(self.evidence_refs),
            "confidence": _clamp_score(self.confidence),
            "limitations": list(dict.fromkeys(self.limitations)),
            "risk_flags": list(dict.fromkeys(self.risk_flags)),
            "promoted_to_truth": bool(self.promoted_to_truth),
            "safe_for_truth_claim": bool(self.safe_for_truth_claim),
        }


class CatalogConfidenceScoringService:
    """Scores catalog usefulness without converting inferred values into Truth."""

    def score_row(
        self,
        *,
        row_class: str,
        technical_observed: bool,
        identity_status: str,
        identity_confidence: float,
        container_confidence: float,
        extension_container_mismatch: bool,
        relationship_candidate: bool,
        has_entity_binding: bool,
    ) -> dict[str, Any]:
        technical_score = 0.9 if technical_observed else 0.0
        observed_identity_score = identity_confidence if identity_status == "observed" else 0.0
        inferred_identity_score = identity_confidence if identity_status == "inferred" else 0.0
        candidate_identity_score = identity_confidence if identity_status == "candidate" else 0.0
        container_score = _container_score(
            confidence=container_confidence,
            mismatch=extension_container_mismatch,
            identity_status=identity_status,
        )
        relationship_score = 0.55 if relationship_candidate else 0.0
        evidence_binding_score = 0.9 if has_entity_binding else 0.0
        row_applicability_score = 0.9 if row_class and row_class != "unknown_or_unclassified" else 0.2
        identity_planning_score = max(
            observed_identity_score,
            inferred_identity_score * 0.75,
            candidate_identity_score * 0.45,
        )
        overall_catalog_confidence = _average(
            technical_score,
            identity_planning_score,
            container_score,
            evidence_binding_score,
            row_applicability_score,
        )
        truth_claim_confidence = observed_identity_score
        planning_confidence = _average(
            technical_score,
            identity_planning_score,
            container_score,
            evidence_binding_score,
            row_applicability_score,
            relationship_score if relationship_candidate else row_applicability_score,
        )
        item_status = self._item_status(
            row_class=row_class,
            identity_status=identity_status,
            extension_container_mismatch=extension_container_mismatch,
            technical_observed=technical_observed,
        )
        return {
            "technical_score": _clamp_score(technical_score),
            "technical_score_basis": "technical metadata observed by governed backend" if technical_observed else "technical metadata not observed",
            "identity_observed_score": _clamp_score(observed_identity_score),
            "identity_observed_score_basis": "observed identity evidence" if observed_identity_score else "no observed identity evidence",
            "identity_inferred_score": _clamp_score(inferred_identity_score),
            "identity_inferred_score_basis": "governed filename inference" if inferred_identity_score else "no inferred identity",
            "identity_candidate_score": _clamp_score(candidate_identity_score),
            "identity_candidate_score_basis": "candidate identity only" if candidate_identity_score else "no candidate identity",
            "container_score": _clamp_score(container_score),
            "container_score_basis": "container anatomy routing confidence",
            "relationship_score": _clamp_score(relationship_score),
            "relationship_score_basis": "sidecar relationship candidate" if relationship_candidate else "no governed relationship confirmation",
            "evidence_binding_score": _clamp_score(evidence_binding_score),
            "evidence_binding_score_basis": "stable entity/evidence binding" if has_entity_binding else "missing stable entity/evidence binding",
            "row_applicability_score": _clamp_score(row_applicability_score),
            "row_applicability_score_basis": "row applicability class assigned",
            "overall_catalog_confidence": _clamp_score(overall_catalog_confidence),
            "truth_claim_confidence": _clamp_score(truth_claim_confidence),
            "planning_confidence": _clamp_score(planning_confidence),
            "catalog_item_status": item_status,
        }

    def _item_status(
        self,
        *,
        row_class: str,
        identity_status: str,
        extension_container_mismatch: bool,
        technical_observed: bool,
    ) -> str:
        if extension_container_mismatch:
            return "cataloged_container_mismatch"
        if row_class == "primary_media_backend_no_valid_evidence":
            return "cataloged_unsupported"
        if identity_status == "observed":
            return "cataloged_observed"
        if identity_status == "inferred":
            return "cataloged_inferred"
        if identity_status == "candidate":
            return "cataloged_candidate"
        if technical_observed:
            return "cataloged_partial"
        return "cataloged_unknown_identity"


def build_catalog_field(
    *,
    field_name: str,
    value: Any,
    status: str,
    source: str,
    source_method: str,
    evidence_refs: list[str] | None = None,
    confidence: float = 0.0,
    limitations: list[str] | None = None,
    risk_flags: list[str] | None = None,
    promoted_to_truth: bool = False,
    safe_for_truth_claim: bool = False,
) -> dict[str, Any]:
    return CatalogFieldEvidence(
        field_name=field_name,
        value=value,
        status=status,
        source=source,
        source_method=source_method,
        evidence_refs=list(evidence_refs or []),
        confidence=confidence,
        limitations=list(limitations or []),
        risk_flags=list(risk_flags or []),
        promoted_to_truth=promoted_to_truth,
        safe_for_truth_claim=safe_for_truth_claim,
    ).model_dump()


def _container_score(*, confidence: float, mismatch: bool, identity_status: str) -> float:
    if mismatch:
        return min(_clamp_score(confidence), 0.35)
    if identity_status == "container_mismatch":
        return 0.2
    return _clamp_score(confidence)


def _score(score: float, basis: str) -> dict[str, Any]:
    return {"score": _clamp_score(score), "basis": basis, "limitations": []}


def _average(*values: float) -> float:
    usable = [_clamp_score(value) for value in values]
    return sum(usable) / max(1, len(usable))


def _clamp_score(value: float) -> float:
    return round(max(0.0, min(1.0, float(value or 0.0))), 4)
