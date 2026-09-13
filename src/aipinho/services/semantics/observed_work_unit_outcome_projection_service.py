from __future__ import annotations

from typing import Any

from aipinho.schemas.runtime.task_run_result import TaskRunResult
from aipinho.schemas.semantics.semantic_offer import (
    ObservedWorkUnitSemanticOutcome,
)


class ObservedWorkUnitOutcomeProjectionService:
    """Projects only work-unit-attributable result evidence.

    Semantic fields are read exclusively from an explicit semantic_outcome
    envelope in source step output summaries. Free-form output is never
    promoted into semantic truth.
    """

    TERMINAL_STEP_STATUSES = {
        "completed",
        "partial",
        "failed",
        "blocked",
        "cancelled",
    }

    def project(
        self,
        *,
        run: Any,
        result: TaskRunResult,
    ) -> list[ObservedWorkUnitSemanticOutcome]:
        plan = getattr(run, "plan", None)
        graph = getattr(plan, "semantic_execution_graph", None)
        if graph is None:
            return []

        summaries = {
            str(item.get("step_id")): dict(item)
            for item in list(result.step_summaries or [])
            if isinstance(item, dict) and item.get("step_id")
        }
        projected: list[ObservedWorkUnitSemanticOutcome] = []
        for unit in graph.work_units:
            source_summaries = [
                summaries.get(step_id)
                for step_id in unit.source_step_ids
            ]
            observed_summaries = [
                item
                for item in source_summaries
                if item is not None
                and str(item.get("status") or "")
                in self.TERMINAL_STEP_STATUSES
            ]
            if not observed_summaries:
                continue

            semantic_envelopes: list[tuple[str, dict[str, Any]]] = []
            for item in observed_summaries:
                output = item.get("output_summary")
                if not isinstance(output, dict):
                    continue
                semantic = output.get("semantic_outcome")
                if isinstance(semantic, dict):
                    semantic_envelopes.append(
                        (str(item.get("step_id") or ""), dict(semantic))
                    )

            use_safety, safety_conflicts = self._merge_scalar_mapping(
                semantic_envelopes,
                field="use_safety",
            )
            properties, property_conflicts = self._merge_scalar_mapping(
                semantic_envelopes,
                field="semantic_properties",
            )
            missing_steps = [
                step_id
                for step_id, item in zip(
                    unit.source_step_ids,
                    source_summaries,
                    strict=False,
                )
                if item is None
                or str(item.get("status") or "")
                not in self.TERMINAL_STEP_STATUSES
            ]
            limitations = self._collect_list(
                semantic_envelopes,
                "limitations",
            )
            missing_truth = self._collect_list(
                semantic_envelopes,
                "missing_truth",
            )
            limitations.extend(
                f"semantic_outcome_conflict:use_safety:{key}"
                for key in safety_conflicts
            )
            missing_truth.extend(
                f"semantic_outcome_conflict:semantic_property:{key}"
                for key in property_conflicts
            )
            missing_truth.extend(
                f"unobserved_source_step:{step_id}"
                for step_id in missing_steps
            )

            statuses = [
                str(item.get("status") or "")
                for item in observed_summaries
            ]
            result_status = self._combined_status(
                statuses=statuses,
                missing_steps=missing_steps,
            )
            projected.append(
                ObservedWorkUnitSemanticOutcome(
                    producer_work_unit_id=unit.work_unit_id,
                    source_step_ids=list(unit.source_step_ids),
                    result_status=result_status,
                    result_ref=(
                        f"task_run_result:{result.run_id}"
                        f"#work_unit:{unit.work_unit_id}"
                    ),
                    observed_use_safety=use_safety,
                    observed_semantic_properties=properties,
                    allowed_downstream_uses=self._collect_list(
                        semantic_envelopes,
                        "allowed_downstream_uses",
                    ),
                    evidence_domains=self._collect_list(
                        semantic_envelopes,
                        "evidence_domains",
                    ),
                    observed_effects=self._collect_list(
                        semantic_envelopes,
                        "observed_effects",
                    ),
                    evidence_refs=self._collect_list(
                        semantic_envelopes,
                        "evidence_refs",
                    ),
                    artifact_refs=self._collect_list(
                        semantic_envelopes,
                        "artifact_refs",
                    ),
                    limitations=self._unique(limitations),
                    missing_truth=self._unique(missing_truth),
                    required_disclosures=self._collect_list(
                        semantic_envelopes,
                        "required_disclosures",
                    ),
                    risk_constraints=self._collect_list(
                        semantic_envelopes,
                        "risk_constraints",
                    ),
                    provenance={
                        "source": "task_run_result_step_summaries",
                        "task_run_result_ref": (
                            f"task_run_result:{result.run_id}"
                        ),
                        "source_step_ids": list(unit.source_step_ids),
                        "observed_step_ids": [
                            str(item.get("step_id") or "")
                            for item in observed_summaries
                        ],
                        "semantic_outcome_step_ids": [
                            step_id
                            for step_id, _ in semantic_envelopes
                        ],
                        "semantic_outcome_envelope_count": len(
                            semantic_envelopes
                        ),
                    },
                )
            )
        return projected

    def _merge_scalar_mapping(
        self,
        envelopes: list[tuple[str, dict[str, Any]]],
        *,
        field: str,
    ) -> tuple[dict[str, Any], list[str]]:
        values: dict[str, Any] = {}
        conflicts: set[str] = set()
        for _, envelope in envelopes:
            raw = envelope.get(field)
            if not isinstance(raw, dict):
                continue
            for key, value in raw.items():
                name = str(key)
                if name in conflicts:
                    continue
                if name not in values:
                    values[name] = value
                    continue
                if values[name] != value:
                    values.pop(name, None)
                    conflicts.add(name)
        return dict(sorted(values.items())), sorted(conflicts)

    def _collect_list(
        self,
        envelopes: list[tuple[str, dict[str, Any]]],
        field: str,
    ) -> list[str]:
        values: list[str] = []
        for _, envelope in envelopes:
            raw = envelope.get(field)
            if not isinstance(raw, list):
                continue
            values.extend(
                str(item)
                for item in raw
                if str(item).strip()
            )
        return self._unique(values)

    def _combined_status(
        self,
        *,
        statuses: list[str],
        missing_steps: list[str],
    ) -> str:
        if missing_steps:
            return "partial"
        if any(status == "blocked" for status in statuses):
            return "blocked"
        if any(status == "failed" for status in statuses):
            return "failed"
        if any(status == "cancelled" for status in statuses):
            return "cancelled"
        if any(status == "partial" for status in statuses):
            return "partial"
        if statuses and all(status == "completed" for status in statuses):
            return "completed"
        return "partial"

    def _unique(self, values: list[str]) -> list[str]:
        return list(
            dict.fromkeys(
                str(item)
                for item in values
                if str(item).strip()
            )
        )
