from __future__ import annotations

import hashlib
import json
from typing import Iterable

from aipinho.schemas.runtime.mission_completion import (
    MissionCompletionFacet,
    MissionCompletionRequirementEvaluation,
    MissionCompletionSnapshot,
)


class MissionCompletionFacetService:
    """Resolve a deterministic mission completion facet from explicit evaluations.

    Requirement semantics and evidence matching are supplied by a separate binding
    stage. This service only validates bindings against the rehydratable mission
    snapshot and applies the frozen completion policy.
    """

    def evaluate(
        self,
        snapshot: MissionCompletionSnapshot,
        *,
        evaluations: Iterable[MissionCompletionRequirementEvaluation] = (),
    ) -> MissionCompletionFacet:
        rows = list(evaluations)
        if snapshot.status == "invalid":
            return self._facet(
                snapshot,
                status="blocked",
                safe=False,
                reason_codes=[
                    *snapshot.reason_codes,
                    "MISSION_COMPLETION_SNAPSHOT_INVALID",
                ],
            )
        if snapshot.status == "missing":
            return self._facet(
                snapshot,
                status="insufficient_evidence",
                safe=False,
                reason_codes=[
                    *snapshot.reason_codes,
                    "MISSION_COMPLETION_SNAPSHOT_MISSING",
                ],
            )

        expected_completion = list(snapshot.completion_requirements)
        expected_validation = list(snapshot.validation_requirements)
        if not expected_completion and not expected_validation:
            return self._facet(
                snapshot,
                status="not_applicable",
                safe=True,
                reason_codes=["MISSION_COMPLETION_REQUIREMENTS_ABSENT"],
            )

        indexed: dict[tuple[str, str], MissionCompletionRequirementEvaluation] = {}
        structural_reasons: list[str] = []
        for row in rows:
            key = (row.requirement_kind, row.requirement)
            if key in indexed:
                structural_reasons.append(
                    f"MISSION_COMPLETION_DUPLICATE_EVALUATION:{row.requirement_kind}:{row.requirement}"
                )
                continue
            indexed[key] = row

        expected_keys = {
            *[("completion", item) for item in expected_completion],
            *[("validation", item) for item in expected_validation],
        }
        unknown = sorted(set(indexed) - expected_keys)
        structural_reasons.extend(
            f"MISSION_COMPLETION_UNKNOWN_REQUIREMENT:{kind}:{requirement}"
            for kind, requirement in unknown
        )

        selected = [
            indexed[key]
            for key in sorted(expected_keys)
            if key in indexed
        ]
        for row in selected:
            structural_reasons.extend(
                self._binding_reasons(snapshot, row)
            )
        if structural_reasons:
            return self._facet(
                snapshot,
                status="blocked",
                safe=False,
                reason_codes=structural_reasons,
                evaluations=selected,
            )

        missing_keys = sorted(expected_keys - set(indexed))
        if missing_keys:
            return self._facet(
                snapshot,
                status="insufficient_evidence",
                safe=False,
                reason_codes=[
                    f"MISSION_COMPLETION_EVALUATION_MISSING:{kind}:{requirement}"
                    for kind, requirement in missing_keys
                ],
                evaluations=selected,
            )

        blocked = [row for row in selected if row.status == "blocked"]
        if blocked:
            return self._facet(
                snapshot,
                status="blocked",
                safe=False,
                reason_codes=self._row_reasons(
                    blocked,
                    fallback="MISSION_COMPLETION_REQUIREMENT_BLOCKED",
                ),
                evaluations=selected,
            )

        unsatisfied = [
            row for row in selected if row.status == "unsatisfied"
        ]
        if unsatisfied:
            return self._facet(
                snapshot,
                status="insufficient_evidence",
                safe=False,
                reason_codes=self._row_reasons(
                    unsatisfied,
                    fallback="MISSION_COMPLETION_REQUIREMENT_UNSATISFIED",
                ),
                evaluations=selected,
            )

        limited = [
            row
            for row in selected
            if row.status == "satisfied_with_limitations"
        ]
        if limited and not snapshot.allow_limited_completion:
            return self._facet(
                snapshot,
                status="insufficient_evidence",
                safe=False,
                reason_codes=[
                    "MISSION_COMPLETION_LIMITED_NOT_ALLOWED"
                ],
                disclosures=self._row_disclosures(limited),
                evaluations=selected,
            )
        if limited:
            return self._facet(
                snapshot,
                status="constrained",
                safe=True,
                reason_codes=[
                    "MISSION_COMPLETION_READY_WITH_LIMITATIONS"
                ],
                disclosures=self._row_disclosures(limited),
                evaluations=selected,
            )

        return self._facet(
            snapshot,
            status="ready",
            safe=True,
            reason_codes=["MISSION_COMPLETION_REQUIREMENTS_SATISFIED"],
            evaluations=selected,
        )

    def unresolved(
        self,
        snapshot: MissionCompletionSnapshot,
        *,
        reason_codes: list[str],
    ) -> MissionCompletionFacet:
        return self._facet(
            snapshot,
            status="insufficient_evidence",
            safe=False,
            reason_codes=reason_codes,
        )

    def blocked(
        self,
        snapshot: MissionCompletionSnapshot,
        *,
        reason_codes: list[str],
    ) -> MissionCompletionFacet:
        return self._facet(
            snapshot,
            status="blocked",
            safe=False,
            reason_codes=reason_codes,
        )

    def _binding_reasons(
        self,
        snapshot: MissionCompletionSnapshot,
        row: MissionCompletionRequirementEvaluation,
    ) -> list[str]:
        if row.status not in {
            "satisfied",
            "satisfied_with_limitations",
        }:
            return []
        reasons: list[str] = []
        if not row.evidence_refs:
            reasons.append(
                f"MISSION_COMPLETION_EVIDENCE_REQUIRED:{row.requirement}"
            )
        unknown_evidence = sorted(
            set(row.evidence_refs) - set(snapshot.evidence_refs)
        )
        if unknown_evidence:
            reasons.extend(
                f"MISSION_COMPLETION_EVIDENCE_OUTSIDE_MISSION:{ref}"
                for ref in unknown_evidence
            )
        if not row.producer_task_run_ids:
            reasons.append(
                f"MISSION_COMPLETION_PRODUCER_REQUIRED:{row.requirement}"
            )
        unknown_producers = sorted(
            set(row.producer_task_run_ids) - set(snapshot.task_run_ids)
        )
        if unknown_producers:
            reasons.extend(
                f"MISSION_COMPLETION_PRODUCER_OUTSIDE_MISSION:{run_id}"
                for run_id in unknown_producers
            )
        return reasons

    def _facet(
        self,
        snapshot: MissionCompletionSnapshot,
        *,
        status: str,
        safe: bool,
        reason_codes: list[str],
        disclosures: list[str] | None = None,
        evaluations: list[MissionCompletionRequirementEvaluation] | None = None,
    ) -> MissionCompletionFacet:
        selected = list(evaluations or [])
        completion_rows = sorted(
            [
                row
                for row in selected
                if row.requirement_kind == "completion"
            ],
            key=lambda row: row.requirement,
        )
        validation_rows = sorted(
            [
                row
                for row in selected
                if row.requirement_kind == "validation"
            ],
            key=lambda row: row.requirement,
        )
        evidence_refs = self._unique(
            ref
            for row in selected
            for ref in row.evidence_refs
        )
        producer_ids = self._unique(
            run_id
            for row in selected
            for run_id in row.producer_task_run_ids
        )
        payload = {
            "mission_id": snapshot.mission_id,
            "snapshot_authority_sha256": snapshot.authority_sha256,
            "status": status,
            "safe_to_report_success": bool(safe),
            "reason_codes": self._unique(reason_codes),
            "disclosures": self._unique(disclosures or []),
            "completion_evaluations": [
                row.model_dump(mode="json") for row in completion_rows
            ],
            "validation_evaluations": [
                row.model_dump(mode="json") for row in validation_rows
            ],
            "evidence_refs": evidence_refs,
            "producer_task_run_ids": producer_ids,
        }
        authority_sha256 = hashlib.sha256(
            json.dumps(
                payload,
                sort_keys=True,
                ensure_ascii=True,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest()
        return MissionCompletionFacet(
            **payload,
            authority_sha256=authority_sha256,
        )

    @staticmethod
    def _row_reasons(
        rows: list[MissionCompletionRequirementEvaluation],
        *,
        fallback: str,
    ) -> list[str]:
        reasons = [
            reason
            for row in rows
            for reason in row.reason_codes
            if reason
        ]
        return reasons or [fallback]

    @staticmethod
    def _row_disclosures(
        rows: list[MissionCompletionRequirementEvaluation],
    ) -> list[str]:
        disclosures = [
            limitation
            for row in rows
            for limitation in row.limitations
            if limitation
        ]
        return disclosures or [
            f"limited_completion:{row.requirement}" for row in rows
        ]

    @staticmethod
    def _unique(values) -> list[str]:
        return list(
            dict.fromkeys(
                str(item) for item in values if str(item)
            )
        )
