from __future__ import annotations

import re
from typing import Any

from aipinho.schemas.semantics.semantic_offer import (
    ObservedWorkUnitSemanticOutcome,
    SemanticOffer,
    SemanticOfferCompilation,
)
from aipinho.services.semantics.semantic_execution_graph_authority_service import (
    SemanticExecutionGraphAuthorityService,
)
from aipinho.services.semantics.semantic_offer_authority_service import (
    SemanticOfferAuthorityService,
)
from aipinho.services.semantics.task_semantic_vocabulary_authority_service import (
    TaskSemanticVocabularyAuthorityService,
)


class SemanticOfferCompilerService:
    """Compiles producer-local observed outcomes into immutable semantic offers."""

    VERSION = "semantic_offer_compiler.v1"

    def __init__(
        self,
        *,
        graph_authority: SemanticExecutionGraphAuthorityService | None = None,
        vocabulary_authority: TaskSemanticVocabularyAuthorityService | None = None,
        offer_authority: SemanticOfferAuthorityService | None = None,
    ) -> None:
        self.graph_authority = (
            graph_authority or SemanticExecutionGraphAuthorityService()
        )
        self.vocabulary_authority = (
            vocabulary_authority or TaskSemanticVocabularyAuthorityService()
        )
        self.offer_authority = (
            offer_authority or SemanticOfferAuthorityService()
        )

    def compile_for_work_unit(
        self,
        *,
        run: Any,
        observed: ObservedWorkUnitSemanticOutcome,
    ) -> SemanticOfferCompilation:
        context, reason = self._context(
            run=run,
            work_unit_id=observed.producer_work_unit_id,
        )
        if reason:
            return self._insufficient(
                work_unit_id=observed.producer_work_unit_id,
                reason=reason,
            )
        assert context is not None
        producer = context["producer"]
        view = context["vocabulary_view"]

        if set(observed.source_step_ids) != set(producer.source_step_ids):
            return self._blocked(
                observed.producer_work_unit_id,
                "SEMANTIC_OFFER_SOURCE_STEP_BINDING_MISMATCH",
            )
        if not observed.result_ref.strip():
            return self._insufficient(
                work_unit_id=observed.producer_work_unit_id,
                reason="SEMANTIC_OFFER_RESULT_REF_REQUIRED",
            )
        if not observed.provenance:
            return self._insufficient(
                work_unit_id=observed.producer_work_unit_id,
                reason="SEMANTIC_OFFER_PROVENANCE_REQUIRED",
            )

        reason = self._validate_observed(observed, view=view)
        if reason:
            return self._blocked(observed.producer_work_unit_id, reason)

        semantic_signal = any(
            [
                observed.observed_use_safety,
                observed.observed_semantic_properties,
                observed.allowed_downstream_uses,
                observed.evidence_domains,
                observed.observed_effects,
            ]
        )
        status = "complete"
        reason_codes: list[str] = []
        if not semantic_signal:
            status = "unknown"
            reason_codes.append("semantic_offer_no_observed_semantic_signal")
        elif (
            observed.limitations
            or observed.missing_truth
            or observed.result_status
            in {
                "partial",
                "completed_with_limitations",
                "failed",
                "blocked",
                "cancelled",
            }
            or any(
                value == "unknown"
                for value in observed.observed_semantic_properties.values()
            )
        ):
            status = "partial"

        offer = SemanticOffer(
            offer_id="pending",
            semantic_graph_id=context["graph"].semantic_graph_id,
            semantic_graph_authority_sha256=context["graph"].authority_sha256,
            producer_work_unit_id=producer.work_unit_id,
            vocabulary_binding=context["vocabulary"].binding(),
            status=status,
            result_status=observed.result_status,
            result_ref=observed.result_ref,
            source_step_ids=list(producer.source_step_ids),
            use_safety=dict(observed.observed_use_safety),
            semantic_properties=dict(observed.observed_semantic_properties),
            allowed_downstream_uses=self._unique(
                observed.allowed_downstream_uses
            ),
            evidence_domains=self._unique(observed.evidence_domains),
            observed_effects=self._unique(observed.observed_effects),
            evidence_refs=self._unique(observed.evidence_refs),
            artifact_refs=self._unique(observed.artifact_refs),
            limitations=self._unique(observed.limitations),
            missing_truth=self._unique(observed.missing_truth),
            required_disclosures=self._unique(
                observed.required_disclosures
            ),
            risk_constraints=self._unique(observed.risk_constraints),
            source_provenance=dict(observed.provenance),
            reason_codes=reason_codes,
            authority_sha256="pending",
        )
        authority_sha256 = self.offer_authority.compute_authority_sha256(
            offer
        )
        offer.authority_sha256 = authority_sha256
        offer.offer_id = f"semantic_offer_{authority_sha256[:24]}"
        return SemanticOfferCompilation(
            status="compiled",
            producer_work_unit_id=producer.work_unit_id,
            offer=offer,
        )

    def _context(
        self,
        *,
        run: Any,
        work_unit_id: str,
    ) -> tuple[dict[str, Any] | None, str | None]:
        plan = getattr(run, "plan", None)
        graph = getattr(plan, "semantic_execution_graph", None)
        vocabulary = getattr(plan, "task_semantic_vocabulary", None)
        if graph is None:
            return None, "SEMANTIC_OFFER_GRAPH_REQUIRED"
        if not self.graph_authority.verify(graph):
            return None, "SEMANTIC_OFFER_GRAPH_AUTHORITY_INVALID"
        if vocabulary is None:
            return None, "SEMANTIC_OFFER_VOCABULARY_REQUIRED"
        if not self.vocabulary_authority.verify(vocabulary):
            return None, "SEMANTIC_OFFER_VOCABULARY_AUTHORITY_INVALID"
        if graph.vocabulary_binding != vocabulary.binding():
            return None, "SEMANTIC_OFFER_VOCABULARY_BINDING_MISMATCH"
        producer = next(
            (
                unit
                for unit in graph.work_units
                if unit.work_unit_id == work_unit_id
            ),
            None,
        )
        if producer is None:
            return None, "SEMANTIC_OFFER_WORK_UNIT_UNKNOWN"
        return {
            "plan": plan,
            "graph": graph,
            "vocabulary": vocabulary,
            "vocabulary_view": self.vocabulary_authority.governed_view(
                vocabulary
            ),
            "producer": producer,
        }, None

    def _validate_observed(
        self,
        observed: ObservedWorkUnitSemanticOutcome,
        *,
        view: dict[str, Any],
    ) -> str | None:
        safety_states = dict(
            view.get("use_safety_allowed_states") or {}
        )
        for name, value in observed.observed_use_safety.items():
            allowed = list(safety_states.get(name) or [])
            if not allowed or value not in allowed:
                return "SEMANTIC_OFFER_USE_SAFETY_INVALID"

        property_states = dict(
            view.get("semantic_property_allowed_states") or {}
        )
        for name, value in observed.observed_semantic_properties.items():
            allowed = list(property_states.get(name) or [])
            if not allowed or value not in allowed:
                return "SEMANTIC_OFFER_SEMANTIC_PROPERTY_INVALID"

        governed_uses = set(
            view.get("downstream_use_identifiers") or []
        )
        if any(
            item not in governed_uses
            for item in observed.allowed_downstream_uses
        ):
            return "SEMANTIC_OFFER_DOWNSTREAM_USE_UNGOVERNED"

        governed_evidence = set(
            view.get("evidence_domain_identifiers") or []
        )
        if any(
            item not in governed_evidence
            for item in observed.evidence_domains
        ):
            return "SEMANTIC_OFFER_EVIDENCE_DOMAIN_UNGOVERNED"

        governed_effects = set(view.get("effect_identifiers") or [])
        if any(
            item not in governed_effects
            for item in observed.observed_effects
        ):
            return "SEMANTIC_OFFER_EFFECT_UNGOVERNED"

        constraint_families = set(
            view.get("constraint_families") or []
        )
        for constraint in observed.risk_constraints:
            if re.fullmatch(r"[a-z][a-z0-9_]*", constraint) is None:
                return "SEMANTIC_OFFER_RISK_CONSTRAINT_INVALID"
            if not any(
                constraint.startswith(f"{family}_")
                for family in constraint_families
            ):
                return "SEMANTIC_OFFER_RISK_CONSTRAINT_INVALID"
        return None

    def _unique(self, values: list[str]) -> list[str]:
        return list(dict.fromkeys(str(item) for item in values if str(item)))

    def _blocked(
        self,
        work_unit_id: str,
        reason: str,
    ) -> SemanticOfferCompilation:
        return SemanticOfferCompilation(
            status="blocked",
            producer_work_unit_id=work_unit_id or None,
            reason_codes=[reason],
        )

    def _insufficient(
        self,
        *,
        work_unit_id: str,
        reason: str,
    ) -> SemanticOfferCompilation:
        return SemanticOfferCompilation(
            status="insufficient_evidence",
            producer_work_unit_id=work_unit_id or None,
            reason_codes=[reason],
        )
