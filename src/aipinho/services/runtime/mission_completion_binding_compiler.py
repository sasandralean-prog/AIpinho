from __future__ import annotations

from collections import defaultdict
from typing import Iterable

from aipinho.core.paths import PATHS
from aipinho.schemas.runtime.mission_completion import (
    MissionCompletionBindingCandidate,
    MissionCompletionBindingCompilation,
    MissionCompletionBindingProposal,
    MissionCompletionEvidenceCatalog,
    MissionCompletionEvidenceItem,
    MissionCompletionRequirementEvaluation,
    MissionCompletionSnapshot,
)
from aipinho.utils.yaml_loader import load_yaml_file


_BLOCKING_STATUSES = {
    "blocked",
    "failed",
    "cancelled",
    "expired",
}


class MissionCompletionBindingCompiler:
    """Compile semantic proposals into deterministic requirement evaluations.

    Model relations are candidate semantics only. Satisfaction is derived here
    from catalog identity plus canonical RuntimeTruth/dependency/use-safety.
    """

    def __init__(self) -> None:
        config_path = (
            PATHS.config_root
            / "runtime"
            / "mission_completion_binding_policy.yaml"
        )
        self.policy = load_yaml_file(
            config_path,
            critical=True,
            root=config_path.parent,
        )

    def compile(
        self,
        snapshot: MissionCompletionSnapshot,
        catalog: MissionCompletionEvidenceCatalog,
        proposal: MissionCompletionBindingProposal,
    ) -> MissionCompletionBindingCompilation:
        structural = self._structural_reasons(
            snapshot,
            catalog,
            proposal,
        )
        if structural:
            return self._result(
                snapshot,
                catalog,
                proposal,
                status="blocked",
                reason_codes=structural,
                evaluations=[],
            )

        grouped: dict[
            tuple[str, str],
            list[MissionCompletionBindingCandidate],
        ] = defaultdict(list)
        for binding in proposal.bindings:
            grouped[
                (binding.requirement_kind, binding.requirement)
            ].append(binding)

        evaluations: list[MissionCompletionRequirementEvaluation] = []
        for kind, requirement in self._expected(snapshot):
            evaluations.append(
                self._compile_requirement(
                    catalog,
                    requirement_kind=kind,
                    requirement=requirement,
                    bindings=grouped.get((kind, requirement), []),
                )
            )

        return self._result(
            snapshot,
            catalog,
            proposal,
            status="compiled",
            reason_codes=["MISSION_COMPLETION_BINDINGS_COMPILED"],
            evaluations=evaluations,
        )

    def _structural_reasons(
        self,
        snapshot: MissionCompletionSnapshot,
        catalog: MissionCompletionEvidenceCatalog,
        proposal: MissionCompletionBindingProposal,
    ) -> list[str]:
        reasons: list[str] = []
        if snapshot.status != "ready":
            reasons.append("MISSION_COMPLETION_SNAPSHOT_NOT_READY")
        if proposal.status != "candidate":
            reasons.append(
                f"MISSION_COMPLETION_BINDING_PROPOSAL_NOT_CANDIDATE:{proposal.status}"
            )
        if proposal.mission_id != snapshot.mission_id:
            reasons.append("MISSION_COMPLETION_PROPOSAL_MISSION_MISMATCH")
        if catalog.mission_id != snapshot.mission_id:
            reasons.append("MISSION_COMPLETION_CATALOG_MISSION_MISMATCH")
        if (
            proposal.snapshot_authority_sha256
            != snapshot.authority_sha256
            or catalog.snapshot_authority_sha256
            != snapshot.authority_sha256
        ):
            reasons.append("MISSION_COMPLETION_SNAPSHOT_BINDING_MISMATCH")
        if proposal.catalog_authority_sha256 != catalog.authority_sha256:
            reasons.append("MISSION_COMPLETION_CATALOG_AUTHORITY_MISMATCH")

        expected = set(self._expected(snapshot))
        settings = self.policy.get("semantic_binding", {}) or {}
        max_refs = int(
            settings.get("max_evidence_refs_per_requirement", 12)
        )
        max_producers = int(
            settings.get("max_producers_per_requirement", 8)
        )
        for binding in proposal.bindings:
            key = (
                binding.requirement_kind,
                binding.requirement,
            )
            if key not in expected:
                reasons.append(
                    "MISSION_COMPLETION_UNKNOWN_BINDING_REQUIREMENT:"
                    f"{binding.requirement_kind}:{binding.requirement}"
                )
            if len(binding.evidence_refs) > max_refs:
                reasons.append(
                    "MISSION_COMPLETION_BINDING_EVIDENCE_LIMIT_EXCEEDED:"
                    f"{binding.requirement}"
                )
            if len(binding.producer_task_run_ids) > max_producers:
                reasons.append(
                    "MISSION_COMPLETION_BINDING_PRODUCER_LIMIT_EXCEEDED:"
                    f"{binding.requirement}"
                )
            reasons.extend(
                self._candidate_identity_reasons(
                    catalog,
                    binding,
                )
            )
        return self._unique(reasons)

    def _candidate_identity_reasons(
        self,
        catalog: MissionCompletionEvidenceCatalog,
        binding: MissionCompletionBindingCandidate,
    ) -> list[str]:
        reasons: list[str] = []
        if (
            binding.semantic_relation == "supports"
            and not binding.evidence_refs
        ):
            reasons.append(
                f"MISSION_COMPLETION_BINDING_EVIDENCE_REQUIRED:{binding.requirement}"
            )
        if (
            binding.semantic_relation == "supports"
            and not binding.producer_task_run_ids
        ):
            reasons.append(
                f"MISSION_COMPLETION_BINDING_PRODUCER_REQUIRED:{binding.requirement}"
            )
        by_pair = {
            (item.evidence_ref, item.producer_task_run_id)
            for item in catalog.items
        }
        catalog_refs = {item.evidence_ref for item in catalog.items}
        catalog_producers = {
            item.producer_task_run_id for item in catalog.items
        }
        for ref in binding.evidence_refs:
            if ref not in catalog_refs:
                reasons.append(
                    f"MISSION_COMPLETION_BINDING_EVIDENCE_UNKNOWN:{ref}"
                )
        for run_id in binding.producer_task_run_ids:
            if run_id not in catalog_producers:
                reasons.append(
                    f"MISSION_COMPLETION_BINDING_PRODUCER_UNKNOWN:{run_id}"
                )
        for ref in binding.evidence_refs:
            if (
                ref in catalog_refs
                and binding.producer_task_run_ids
                and not any(
                    (ref, run_id) in by_pair
                    for run_id in binding.producer_task_run_ids
                )
            ):
                reasons.append(
                    "MISSION_COMPLETION_BINDING_REF_PRODUCER_MISMATCH:"
                    f"{ref}"
                )
        for run_id in binding.producer_task_run_ids:
            if (
                run_id in catalog_producers
                and binding.evidence_refs
                and not any(
                    (ref, run_id) in by_pair
                    for ref in binding.evidence_refs
                )
            ):
                reasons.append(
                    "MISSION_COMPLETION_BINDING_PRODUCER_REF_MISMATCH:"
                    f"{run_id}"
                )
        return reasons

    def _compile_requirement(
        self,
        catalog: MissionCompletionEvidenceCatalog,
        *,
        requirement_kind: str,
        requirement: str,
        bindings: list[MissionCompletionBindingCandidate],
    ) -> MissionCompletionRequirementEvaluation:
        min_confidence = float(
            (
                self.policy.get("semantic_binding", {})
                or {}
            ).get("min_confidence", 0.65)
        )
        supports = [
            binding
            for binding in bindings
            if binding.semantic_relation == "supports"
            and binding.confidence >= min_confidence
        ]
        if not supports:
            reason = (
                "MISSION_COMPLETION_BINDING_CONFIDENCE_INSUFFICIENT"
                if any(
                    binding.semantic_relation == "supports"
                    for binding in bindings
                )
                else "MISSION_COMPLETION_SUPPORTING_EVIDENCE_NOT_BOUND"
            )
            return MissionCompletionRequirementEvaluation(
                requirement=requirement,
                requirement_kind=requirement_kind,
                status="unsatisfied",
                reason_codes=[reason],
            )

        blocked_candidates: list[
            tuple[MissionCompletionBindingCandidate, list[MissionCompletionEvidenceItem]]
        ] = []
        unsafe_candidates: list[
            tuple[MissionCompletionBindingCandidate, list[MissionCompletionEvidenceItem]]
        ] = []
        limited_candidates: list[
            tuple[MissionCompletionBindingCandidate, list[MissionCompletionEvidenceItem]]
        ] = []
        safe_candidates: list[
            tuple[MissionCompletionBindingCandidate, list[MissionCompletionEvidenceItem]]
        ] = []

        for binding in supports:
            items = self._items_for_binding(catalog, binding)
            classification = self._classify_items(items)
            if classification == "blocked":
                blocked_candidates.append((binding, items))
            elif classification == "unsafe":
                unsafe_candidates.append((binding, items))
            elif classification == "limited":
                limited_candidates.append((binding, items))
            else:
                safe_candidates.append((binding, items))

        if safe_candidates:
            return self._evaluation_from_candidates(
                requirement,
                requirement_kind,
                "satisfied",
                safe_candidates,
                reason_codes=[
                    "MISSION_COMPLETION_CANONICAL_EVIDENCE_SATISFIED"
                ],
            )
        if limited_candidates:
            return self._evaluation_from_candidates(
                requirement,
                requirement_kind,
                "satisfied_with_limitations",
                limited_candidates,
                reason_codes=[
                    "MISSION_COMPLETION_CANONICAL_EVIDENCE_LIMITED"
                ],
            )
        if blocked_candidates:
            return self._evaluation_from_candidates(
                requirement,
                requirement_kind,
                "blocked",
                blocked_candidates,
                reason_codes=[
                    "MISSION_COMPLETION_CANONICAL_EVIDENCE_BLOCKED"
                ],
            )
        return self._evaluation_from_candidates(
            requirement,
            requirement_kind,
            "unsatisfied",
            unsafe_candidates,
            reason_codes=[
                "MISSION_COMPLETION_CANONICAL_EVIDENCE_UNSAFE"
            ],
        )

    def _items_for_binding(
        self,
        catalog: MissionCompletionEvidenceCatalog,
        binding: MissionCompletionBindingCandidate,
    ) -> list[MissionCompletionEvidenceItem]:
        refs = set(binding.evidence_refs)
        producers = set(binding.producer_task_run_ids)
        return [
            item
            for item in catalog.items
            if item.evidence_ref in refs
            and item.producer_task_run_id in producers
        ]

    def _classify_items(
        self,
        items: list[MissionCompletionEvidenceItem],
    ) -> str:
        if not items:
            return "unsafe"
        if any(
            item.runtime_status in _BLOCKING_STATUSES
            or item.result_status in _BLOCKING_STATUSES
            or item.runtime_truth_status in _BLOCKING_STATUSES
            or item.phase_dependency_status == "blocked"
            for item in items
        ):
            return "blocked"
        if any(
            item.runtime_truth_safe_to_report_success is not True
            or bool(item.missing_truth)
            or item.use_safety.get("safe_for_truth_claim") is False
            for item in items
        ):
            return "unsafe"
        if any(
            bool(item.limitations)
            or item.result_status in {
                "completed_with_limitations",
                "partial",
            }
            or item.phase_dependency_status
            == "satisfied_with_limitations"
            for item in items
        ):
            return "limited"
        return "safe"

    def _evaluation_from_candidates(
        self,
        requirement: str,
        requirement_kind: str,
        status: str,
        candidates: Iterable[
            tuple[
                MissionCompletionBindingCandidate,
                list[MissionCompletionEvidenceItem],
            ]
        ],
        *,
        reason_codes: list[str],
    ) -> MissionCompletionRequirementEvaluation:
        rows = list(candidates)
        evidence_refs = self._unique(
            ref
            for binding, _items in rows
            for ref in binding.evidence_refs
        )
        producer_ids = self._unique(
            run_id
            for binding, _items in rows
            for run_id in binding.producer_task_run_ids
        )
        limitations = self._unique(
            limitation
            for _binding, items in rows
            for item in items
            for limitation in item.limitations
        )
        return MissionCompletionRequirementEvaluation(
            requirement=requirement,
            requirement_kind=requirement_kind,
            status=status,
            evidence_refs=evidence_refs,
            producer_task_run_ids=producer_ids,
            reason_codes=reason_codes,
            limitations=limitations,
        )

    def _result(
        self,
        snapshot: MissionCompletionSnapshot,
        catalog: MissionCompletionEvidenceCatalog,
        proposal: MissionCompletionBindingProposal,
        *,
        status: str,
        reason_codes: list[str],
        evaluations: list[MissionCompletionRequirementEvaluation],
    ) -> MissionCompletionBindingCompilation:
        return MissionCompletionBindingCompilation(
            mission_id=snapshot.mission_id,
            snapshot_authority_sha256=snapshot.authority_sha256,
            catalog_authority_sha256=catalog.authority_sha256,
            proposal_sha256=proposal.proposal_sha256,
            status=status,
            reason_codes=self._unique(reason_codes),
            evaluations=sorted(
                evaluations,
                key=lambda item: (
                    item.requirement_kind,
                    item.requirement,
                ),
            ),
        )

    @staticmethod
    def _expected(
        snapshot: MissionCompletionSnapshot,
    ) -> list[tuple[str, str]]:
        return [
            *[
                ("completion", item)
                for item in snapshot.completion_requirements
            ],
            *[
                ("validation", item)
                for item in snapshot.validation_requirements
            ],
        ]

    @staticmethod
    def _unique(values) -> list[str]:
        return list(
            dict.fromkeys(
                str(item) for item in values if str(item)
            )
        )
