from __future__ import annotations

import hashlib
import json
from typing import Any

from aipinho.schemas.runtime.phase_outcome import PhaseOutcome
from aipinho.services.runtime.task_run_store import TaskRunStore


class PhaseOutcomeRepository:
    """Resolve phase outcomes from canonical TaskRun state.

    This is a projection boundary, not an authorization boundary. Outcomes are
    rebuilt from TaskRun + TaskRunResult + canonical artifact bindings.
    """

    def __init__(self, store: TaskRunStore | None = None) -> None:
        self.store = store or TaskRunStore()

    def resolve(self, *, session_id: str | None, phase_id: str) -> PhaseOutcome | None:
        candidates = self.store.list_runs(session_id=session_id, limit=1000)
        for run in candidates:
            observed_phase = str(
                run.intent_map.get("phase_id")
                or run.bootstrap_context.get("phase_id")
                or run.current_phase
                or ""
            )
            if observed_phase != phase_id:
                continue
            result = self.store.get_result(run.run_id)
            if result is None:
                continue
            return self.project(run_id=run.run_id)
        return None

    def project(self, *, run_id: str) -> PhaseOutcome | None:
        run = self.store.get_run(run_id)
        result = self.store.get_result(run_id)
        if run is None or result is None:
            return None
        phase_id = str(
            run.intent_map.get("phase_id")
            or run.bootstrap_context.get("phase_id")
            or run.current_phase
            or ""
        )
        if not phase_id:
            return None

        outputs = result.outputs if isinstance(result.outputs, dict) else {}
        semantic = (
            outputs.get("phase_semantic_completion_decision")
            if isinstance(outputs.get("phase_semantic_completion_decision"), dict)
            else {}
        )
        completion_meta = (
            result.completion.metadata
            if result.completion is not None and isinstance(result.completion.metadata, dict)
            else {}
        )
        if not semantic and isinstance(completion_meta.get("phase_dependency"), dict):
            semantic = dict(completion_meta)

        phase_dependency = (
            dict(semantic.get("phase_dependency"))
            if isinstance(semantic.get("phase_dependency"), dict)
            else dict(completion_meta.get("phase_dependency") or {})
        )
        semantic_metadata = semantic.get("metadata") if isinstance(semantic.get("metadata"), dict) else {}
        use_safety = (
            dict(semantic.get("use_safety"))
            if isinstance(semantic.get("use_safety"), dict)
            else dict(semantic_metadata.get("use_safety") or {})
        )
        if not use_safety and isinstance(completion_meta.get("policy"), dict):
            policy = completion_meta.get("policy") or {}
            if isinstance(policy.get("use_safety"), dict):
                use_safety = dict(policy["use_safety"])
        if not use_safety:
            prefix = "artifact_safe_for_"
            use_safety = {
                f"safe_for_{str(source)[len(prefix):]}": value
                for source, value in phase_dependency.items()
                if str(source).startswith(prefix)
            }

        artifacts = [dict(item) for item in run.produced_artifacts if isinstance(item, dict)]
        artifact_refs = [str(item.get("artifact_id")) for item in artifacts if item.get("artifact_id")]
        evidence_refs = self._unique(
            [
                f"task_run:{run.run_id}",
                f"task_run_result:{run.run_id}",
                *artifact_refs,
                *[
                    str(ref)
                    for artifact in artifacts
                    for ref in artifact.get("evidence_refs") or []
                    if ref
                ],
            ]
        )
        limitations = self._unique(
            [
                *list(result.limitations or []),
                *list(semantic.get("limitations") or []),
                *list(completion_meta.get("limitations") or []),
            ]
        )
        required_disclosures = self._unique(
            [
                *list(semantic.get("required_disclosures") or []),
                *list(completion_meta.get("required_disclosures") or []),
            ]
        )
        missing_truth = self._unique(
            [
                *list(semantic.get("missing_truth") or []),
                *list(completion_meta.get("missing_truth") or []),
            ]
        )
        risk_constraints = self._unique(
            [
                *list(semantic.get("risk_constraints") or []),
                *list(completion_meta.get("risk_constraints") or []),
            ]
        )
        semantic_properties = {
            "phase_contract_status": semantic.get("phase_contract_status"),
            "artifact_sufficiency_status": semantic.get("artifact_sufficiency_status"),
            "safe_for_limited_discovery": semantic.get("safe_for_limited_discovery"),
            "partial_artifact_accepted": semantic.get("partial_artifact_accepted"),
            "truth_status": (
                run.canonical_state.truth_status
                if run.canonical_state is not None and hasattr(run.canonical_state, "truth_status")
                else None
            ),
        }
        semantic_properties = {key: value for key, value in semantic_properties.items() if value is not None}

        authority_payload = {
            "producer_task_run_id": run.run_id,
            "producer_operation_id": run.operation_id,
            "phase_id": phase_id,
            "result_status": result.status,
            "reason_code": result.reason_code,
            "semantic_completion": semantic,
            "phase_dependency": phase_dependency,
            "artifact_refs": artifact_refs,
            "evidence_refs": evidence_refs,
        }
        authority_sha256 = hashlib.sha256(
            json.dumps(
                authority_payload,
                sort_keys=True,
                ensure_ascii=True,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest()
        return PhaseOutcome(
            producer_task_run_id=run.run_id,
            producer_operation_id=run.operation_id,
            session_id=run.session_id,
            phase_id=phase_id,
            workspace=run.workspace,
            runtime_status=str(run.status),
            result_status=str(result.status),
            reason_code=result.reason_code,
            semantic_completion=semantic,
            phase_dependency=phase_dependency,
            use_safety=use_safety,
            semantic_properties=semantic_properties,
            limitations=limitations,
            required_disclosures=required_disclosures,
            missing_truth=missing_truth,
            risk_constraints=risk_constraints,
            artifact_refs=artifact_refs,
            evidence_refs=evidence_refs,
            artifacts=artifacts,
            result_ref=f"task_run_result:{run.run_id}",
            authority_refs=[
                f"task_run:{run.run_id}",
                f"task_run_result:{run.run_id}",
            ],
            authority_sha256=authority_sha256,
        )

    def _unique(self, values: list[Any]) -> list[str]:
        return list(dict.fromkeys(str(item) for item in values if str(item)))
