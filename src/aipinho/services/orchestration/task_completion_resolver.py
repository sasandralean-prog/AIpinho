from __future__ import annotations

from typing import Any

from aipinho.core.paths import PATHS
from aipinho.schemas.runtime.task_completion import (
    TaskCompletionCriterion,
    TaskCompletionEvaluation,
)
from aipinho.utils.yaml_loader import load_yaml_file


class TaskCompletionResolver:
    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self.config = config or load_yaml_file(
            PATHS.config_root / "runtime" / "task_completion_policy.yaml",
            critical=True,
            root=PATHS.config_root / "runtime",
        )

    def resolve(
        self,
        run: Any,
        context: Any,
        *,
        proposed_status: str = "completed",
    ) -> TaskCompletionEvaluation:
        contract_type = str(getattr(run, "contract_type", "unknown"))
        contract = self._contract(contract_type)
        criteria: list[TaskCompletionCriterion] = []
        expected: list[str] = []
        fulfilled: list[str] = []
        missing: list[str] = []

        for output_id in self._required_outputs(contract):
            expected.append(output_id)
            criterion = self._output_criterion(output_id, context)
            criteria.append(criterion)
            if criterion.status == "fulfilled":
                fulfilled.append(output_id)
            elif criterion.required:
                missing.append(output_id)

        if self._deliverable_checks_enabled(contract):
            deliverable_criteria = self._deliverable_criteria(run, context)
            criteria.extend(deliverable_criteria)
            for criterion in deliverable_criteria:
                expected.append(criterion.criterion_id)
                if criterion.status == "fulfilled":
                    fulfilled.append(criterion.criterion_id)
                elif criterion.required:
                    missing.append(criterion.criterion_id)

        limitations: list[str] = []
        if missing:
            limitations.append("missing_required_expected_outcomes:" + ",".join(missing))
        if proposed_status in {"failed", "blocked"}:
            status = proposed_status
        elif missing:
            status = "partial"
        elif proposed_status == "partial":
            status = "partial"
        else:
            status = "completed"
        return TaskCompletionEvaluation(
            status=status,
            safe_to_report_success=status == "completed" and not missing,
            expected_outcomes=list(dict.fromkeys(expected)),
            fulfilled_outcomes=list(dict.fromkeys(fulfilled)),
            missing_outcomes=list(dict.fromkeys(missing)),
            criteria=criteria,
            limitations=limitations,
            metadata={
                "contract_type": contract_type,
                "proposed_status": proposed_status,
            },
        )

    def _contract(self, contract_type: str) -> dict[str, Any]:
        contracts = self.config.get("contracts", {})
        if isinstance(contracts, dict):
            raw = contracts.get(contract_type) or {}
            if isinstance(raw, dict):
                return raw
        return {}

    def _required_outputs(self, contract: dict[str, Any]) -> list[str]:
        return [
            str(item)
            for item in contract.get("required_outputs", []) or []
            if str(item).strip()
        ]

    def _deliverable_checks_enabled(self, contract: dict[str, Any]) -> bool:
        raw = contract.get("requested_deliverables", {})
        return isinstance(raw, dict) and bool(raw.get("enabled", False))

    def _output_criterion(self, output_id: str, context: Any) -> TaskCompletionCriterion:
        value = self._output_value(output_id, context)
        fulfilled = value is not None
        return TaskCompletionCriterion(
            criterion_id=output_id,
            kind="required_output",
            required=True,
            status="fulfilled" if fulfilled else "missing",
            summary=(
                f"Output {output_id} is present."
                if fulfilled
                else f"Output {output_id} is missing."
            ),
            evidence_refs=[output_id] if fulfilled else [],
        )

    def _deliverable_criteria(self, run: Any, context: Any) -> list[TaskCompletionCriterion]:
        requested = [
            str(item)
            for item in (getattr(run, "intent_map", {}) or {}).get(
                "requested_deliverables", []
            )
            if str(item).strip()
        ]
        if not requested:
            return []
        report = self._project_report(context)
        if report is None:
            return [
                TaskCompletionCriterion(
                    criterion_id=f"deliverable:{item}",
                    kind="requested_deliverable",
                    status="missing",
                    summary="Requested deliverable requires a project report, but no report evidence exists.",
                    metadata={"deliverable_id": item},
                )
                for item in requested
            ]
        fulfilled = set(getattr(report, "fulfilled_deliverables", []) or [])
        missing = set(getattr(report, "missing_deliverables", []) or [])
        criteria: list[TaskCompletionCriterion] = []
        for item in requested:
            ok = item in fulfilled and item not in missing
            criteria.append(
                TaskCompletionCriterion(
                    criterion_id=f"deliverable:{item}",
                    kind="requested_deliverable",
                    status="fulfilled" if ok else "missing",
                    summary=(
                        f"Requested deliverable {item} was fulfilled."
                        if ok
                        else f"Requested deliverable {item} is missing from the report."
                    ),
                    evidence_refs=[getattr(report, "report_id", "project_report")]
                    if ok
                    else [],
                    metadata={"deliverable_id": item},
                )
            )
        return criteria

    def _output_value(self, output_id: str, context: Any) -> Any | None:
        outputs = getattr(context, "outputs", {}) or {}
        aliases = self.config.get("output_aliases", {})
        keys = aliases.get(output_id, []) if isinstance(aliases, dict) else []
        for key in [output_id, *[str(item) for item in keys]]:
            if key in outputs and outputs[key] is not None:
                return outputs[key]
        return None

    def _project_report(self, context: Any) -> Any | None:
        value = self._output_value("project_report", context)
        if value is None:
            return None
        return getattr(value, "report", value)

    def status(self) -> dict[str, object]:
        contracts = self.config.get("contracts", {})
        return {
            "status": "ok",
            "service": "task_completion_resolver",
            "contracts": sorted(contracts.keys()) if isinstance(contracts, dict) else [],
        }
