from __future__ import annotations

import hashlib
import json
from typing import Any

from aipinho.schemas.runtime.phase_outcome import PhaseOutcome
from aipinho.services.runtime.phase_identity_service import PhaseIdentityService
from aipinho.services.runtime.runtime_timeline_service import RuntimeTimelineService
from aipinho.services.runtime.runtime_truth_engine import RuntimeTruthEngine
from aipinho.services.runtime.task_run_store import TaskRunStore


class PhaseOutcomeRepository:
    """Resolve phase outcomes from canonical TaskRun state.

    This is a projection boundary, not an authorization boundary. Outcomes are
    rebuilt from TaskRun + TaskRunResult + canonical artifact bindings.
    """

    def __init__(
        self,
        store: TaskRunStore | None = None,
        *,
        timelines: RuntimeTimelineService | None = None,
        truth: RuntimeTruthEngine | None = None,
        phases: PhaseIdentityService | None = None,
    ) -> None:
        self.store = store or TaskRunStore()
        self.phases = phases or PhaseIdentityService()
        self.timelines = timelines or RuntimeTimelineService(store=self.store, phases=self.phases)
        self.truth = truth or RuntimeTruthEngine()

    def resolve(self, *, session_id: str | None, phase_id: str) -> PhaseOutcome | None:
        candidates = self.store.list_runs(session_id=session_id, limit=1000)
        for run in candidates:
            observed_phase = self.phases.from_run(run) or ""
            if observed_phase != phase_id:
                continue
            result = self.store.get_result(run.run_id)
            if result is None:
                continue
            return self.project(run_id=run.run_id)
        return None

    def list_for_mission(
        self,
        *,
        mission_id: str,
        limit: int = 1000,
    ) -> list[PhaseOutcome]:
        if not mission_id:
            return []
        runs = self.store.list_runs(
            mission_id=mission_id,
            limit=limit,
        )
        ordered = sorted(
            runs,
            key=lambda item: (
                str(item.created_at or ""),
                str(item.run_id),
            ),
        )
        outcomes: list[PhaseOutcome] = []
        for run in ordered:
            binding = getattr(run, "mission_binding", None)
            if binding is None or binding.mission_id != mission_id:
                continue
            if self.store.get_result(run.run_id) is None:
                continue
            outcome = self.project(run_id=run.run_id)
            if outcome is not None:
                outcomes.append(outcome)
        return outcomes

    def project(self, *, run_id: str) -> PhaseOutcome | None:
        run = self.store.get_run(run_id)
        result = self.store.get_result(run_id)
        if run is None or result is None:
            return None
        phase_id = self.phases.from_run(run) or ""
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
        timeline = self.timelines.build(run_id)
        runtime_truth = self.truth.evaluate(run, result=result, timeline=timeline)
        runtime_truth_payload = runtime_truth.model_dump(mode="json")
        truth_blocks_dependency = runtime_truth.status in {
            "blocked",
            "failed",
            "cancelled",
            "expired",
        }
        if truth_blocks_dependency:
            previous_dependency_status = phase_dependency.get("status")
            phase_dependency = {
                **phase_dependency,
                "status": "blocked",
                "reason_code": runtime_truth.reason_code or "UPSTREAM_RUNTIME_TRUTH_BLOCKED",
                "runtime_truth_status": runtime_truth.status,
                "runtime_truth_safe_to_report_success": runtime_truth.safe_to_report_success,
                "runtime_truth_previous_dependency_status": previous_dependency_status,
            }
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

        intermediate_semantics = self._intermediate_semantics(result)
        use_safety = self._merge_use_safety(
            [
                use_safety,
                *[
                    dict(item.get("use_safety") or {})
                    for item in intermediate_semantics
                    if isinstance(item.get("use_safety"), dict)
                ],
            ]
        )

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
                *[
                    str(value)
                    for item in intermediate_semantics
                    for value in list(item.get("limitations") or [])
                    if str(value)
                ],
            ]
        )
        required_disclosures = self._unique(
            [
                *list(semantic.get("required_disclosures") or []),
                *list(completion_meta.get("required_disclosures") or []),
                *[
                    str(value)
                    for item in intermediate_semantics
                    for value in list(
                        item.get("required_disclosures") or []
                    )
                    if str(value)
                ],
                *(
                    [f"runtime_truth_blocked:{runtime_truth.reason_code}"]
                    if truth_blocks_dependency and runtime_truth.reason_code
                    else []
                ),
            ]
        )
        missing_truth = self._unique(
            [
                *list(semantic.get("missing_truth") or []),
                *list(completion_meta.get("missing_truth") or []),
                *[
                    str(value)
                    for item in intermediate_semantics
                    for value in list(item.get("missing_truth") or [])
                    if str(value)
                ],
                *list(runtime_truth.contradictions if truth_blocks_dependency else []),
                *list(runtime_truth.missing_evidence if truth_blocks_dependency else []),
            ]
        )
        risk_constraints = self._unique(
            [
                *list(semantic.get("risk_constraints") or []),
                *list(completion_meta.get("risk_constraints") or []),
            ]
        )
        intermediate_properties: dict[str, Any] = {}
        repair_state_seen = False
        repair_focus_complete_values: list[bool] = []
        repair_declared_focus: list[str] = []
        repair_unresolved: list[str] = []
        for item in intermediate_semantics:
            properties = item.get("semantic_properties")
            if isinstance(properties, dict):
                for key, value in properties.items():
                    # Backward-compatible ingestion for older persisted
                    # semantic envelopes. Structured repair metadata is the
                    # canonical form because semantic properties are scalar.
                    if key == "evidence_repair_focus_complete":
                        repair_state_seen = True
                        if isinstance(value, bool):
                            repair_focus_complete_values.append(value)
                        continue
                    if key == "evidence_repair_focus_paths":
                        repair_state_seen = True
                        repair_declared_focus.extend(
                            str(path)
                            for path in list(value or [])
                            if str(path)
                        )
                        continue
                    if key == "evidence_repair_unresolved_paths":
                        repair_state_seen = True
                        repair_unresolved.extend(
                            str(path)
                            for path in list(value or [])
                            if str(path)
                        )
                        continue
                    intermediate_properties[key] = value

            repair = item.get("evidence_repair")
            if isinstance(repair, dict) and repair.get("required"):
                repair_state_seen = True
                focus_complete = repair.get("focus_complete")
                if isinstance(focus_complete, bool):
                    repair_focus_complete_values.append(focus_complete)
                repair_declared_focus.extend(
                    str(path)
                    for path in list(repair.get("focus_paths") or [])
                    if str(path)
                )
                repair_unresolved.extend(
                    str(path)
                    for path in list(repair.get("unresolved_paths") or [])
                    if str(path)
                )

        file_context_summary = (
            outputs.get("file_context_summary")
            if isinstance(outputs.get("file_context_summary"), dict)
            else {}
        )
        observed_omitted_paths = self._unique(
            list(file_context_summary.get("omitted_files") or [])
        )
        if repair_state_seen:
            repair_focus_complete = bool(
                repair_focus_complete_values
                and all(repair_focus_complete_values)
            )
            if repair_focus_complete:
                repair_focus_paths = []
            elif repair_unresolved:
                repair_focus_paths = self._unique(repair_unresolved)
            else:
                repair_focus_paths = self._unique(repair_declared_focus)
            intermediate_properties[
                "evidence_repair_focus_complete"
            ] = repair_focus_complete
        else:
            repair_focus_paths = observed_omitted_paths

        semantic_properties = {
            **intermediate_properties,
            "phase_contract_status": semantic.get("phase_contract_status"),
            "artifact_sufficiency_status": semantic.get("artifact_sufficiency_status"),
            "safe_for_limited_discovery": semantic.get("safe_for_limited_discovery"),
            "partial_artifact_accepted": semantic.get("partial_artifact_accepted"),
            "runtime_truth_status": runtime_truth.status,
            "runtime_truth_reason_code": runtime_truth.reason_code,
            "runtime_truth_safe_to_report_success": runtime_truth.safe_to_report_success,
            "speaker_truth_status": runtime_truth.speaker_truth_status,
            "evidence_repair_focus_paths": repair_focus_paths,
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
            "use_safety": use_safety,
            "semantic_properties": semantic_properties,
            "limitations": limitations,
            "required_disclosures": required_disclosures,
            "missing_truth": missing_truth,
            "risk_constraints": risk_constraints,
            "runtime_truth": runtime_truth_payload,
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
            reason_code=(
                runtime_truth.reason_code
                if truth_blocks_dependency
                else result.reason_code
            ),
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
                f"runtime_truth:{runtime_truth.truth_id}",
            ],
            authority_sha256=authority_sha256,
        )

    def _intermediate_semantics(
        self,
        result: Any,
    ) -> list[dict[str, Any]]:
        observed: list[dict[str, Any]] = []
        outputs = (
            result.outputs
            if isinstance(getattr(result, "outputs", None), dict)
            else {}
        )
        for value in outputs.values():
            if not isinstance(value, dict):
                continue
            semantic = value.get("semantic_outcome")
            if isinstance(semantic, dict):
                observed.append(dict(semantic))

        for step in list(
            getattr(result, "step_summaries", []) or []
        ):
            if not isinstance(step, dict):
                continue
            summary = step.get("output_summary")
            if not isinstance(summary, dict):
                continue
            semantic = summary.get("semantic_outcome")
            if isinstance(semantic, dict):
                observed.append(dict(semantic))
        return observed

    def _merge_use_safety(
        self,
        mappings: list[dict[str, Any]],
    ) -> dict[str, Any]:
        values_by_key: dict[str, list[Any]] = {}
        for mapping in mappings:
            for key, value in mapping.items():
                values_by_key.setdefault(str(key), []).append(value)

        merged: dict[str, Any] = {}
        for key, values in values_by_key.items():
            merged[key] = self._conservative_safety_value(values)
        return merged

    @staticmethod
    def _conservative_safety_value(values: list[Any]) -> Any:
        if not values:
            return None
        normalized = []
        for value in values:
            if value is True:
                normalized.append(("true", value))
            elif value is False:
                normalized.append(("false", value))
            else:
                text = str(value).strip().casefold()
                if text == "true":
                    normalized.append(("true", True))
                elif text == "false":
                    normalized.append(("false", False))
                elif text == "true_with_limitations":
                    normalized.append(
                        ("true_with_limitations", "true_with_limitations")
                    )
                else:
                    normalized.append(("unknown", value))

        labels = {label for label, _ in normalized}
        if "false" in labels:
            return False
        if "unknown" in labels:
            first = normalized[0][1]
            if all(item[1] == first for item in normalized):
                return first
            return False
        if "true_with_limitations" in labels:
            return "true_with_limitations"
        return True

    def _unique(self, values: list[Any]) -> list[str]:
        return list(dict.fromkeys(str(item) for item in values if str(item)))
