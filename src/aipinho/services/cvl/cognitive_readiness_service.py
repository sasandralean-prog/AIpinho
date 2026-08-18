from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any
from uuid import uuid4

from aipinho.core.paths import PATHS
from aipinho.schemas.cvl import (
    CognitiveCoverageReport,
    CognitiveDependencyGraph,
    CognitiveFrontierReport,
    CognitivePrediction,
    CognitivePredictionCalibrationResult,
    CognitiveReadinessDecision,
    CognitiveReadinessResult,
    CognitiveSimulationResult,
    FireTestProfile,
)
from aipinho.services.cvl.cognitive_validation_laboratory_service import (
    CognitiveValidationLaboratoryService,
    CVLReportWriter,
)
from aipinho.services.runtime.task_run_store import TaskRunStore


class CognitiveReadinessService:
    """Canonical Phase 0 gate.

    This service does not create runtime tasks, operations, or operational
    artifacts. It only persists CVL readiness documents and calibration reports.
    """

    def __init__(
        self,
        *,
        runtime_reports_root: Path | None = None,
        firetest_reports_root: Path | None = None,
        store: TaskRunStore | None = None,
    ) -> None:
        self.runtime_reports_root = runtime_reports_root or (PATHS.reports_root / "runtime_consolidation")
        self.firetest_reports_root = firetest_reports_root or (PATHS.reports_root / "firetest5")
        self.store = store or TaskRunStore()

    def build_phase0(
        self,
        *,
        prompt: str,
        firetest_id: str = "firetest5",
        firetest_version: str = "h1b4_4",
        workspace_ref: str | None = None,
        context_ref: str | None = None,
        frontier_context: dict[str, Any] | None = None,
        available_capabilities: list[str] | None = None,
    ) -> CognitiveReadinessResult:
        profile, selection = self.select_profile(
            prompt=prompt,
            firetest_id=firetest_id,
            firetest_version=firetest_version,
            frontier_context=frontier_context,
        )
        writer = CVLReportWriter(root=self.firetest_reports_root)
        cvl = CognitiveValidationLaboratoryService(writer=writer).analyze(
            [profile],
            suite_name=f"{firetest_id}_{firetest_version}_phase0_cognitive_gate",
            available_capabilities=available_capabilities or ["read_workspace"],
            write_reports=True,
        )
        prediction_report = cvl.prediction_reports[0]
        graph = cvl.dependency_graphs[0]
        coverage = cvl.coverage_reports[0]
        simulation = cvl.simulation_results[0]
        prediction = self._prediction(profile, prediction_report, frontier_context=frontier_context)
        decision = self._decision(prediction)
        readiness = CognitiveReadinessResult(
            firetest_id=firetest_id,
            firetest_version=firetest_version,
            status="blocked" if decision.decision.startswith("NO_GO") else "ready",
            input_prompt_hash=self._hash(prompt),
            workspace_ref=workspace_ref,
            context_ref=context_ref,
            decision=decision,
            prediction=prediction,
            dependency_graph=self._dependency_graph(profile, graph, prediction),
            coverage_report=self._coverage_report(coverage),
            simulation_result=self._simulation_result(profile, simulation, prediction),
            frontier_report=self._frontier_report(prediction),
            go_no_go_recommendation=decision.decision,
            confidence=decision.confidence,
            reason_codes=list(dict.fromkeys([*prediction_report.reason_codes, *selection["reason_codes"]])),
            critical_dependencies=list(prediction.critical_dependencies),
            expected_blockers=[prediction.predicted_reason_code] if prediction.predicted_reason_code else [],
            limitations=[
                "phase0_is_cognitive_only",
                "phase0_does_not_execute_runtime",
                "prediction_is_not_truth",
            ],
            safe_to_start_phase1=decision.safe_to_start_phase1,
            profile_id=profile.profile_id,
            profile_selection_method=selection["method"],
            profile_selection_confidence=float(selection["confidence"]),
            profile_selection_reason_codes=list(selection["reason_codes"]),
            report_paths=self._rewrite_phase0_reports(cvl.report_paths),
        )
        self._write_readiness(readiness)
        return readiness

    def select_profile(
        self,
        *,
        prompt: str,
        firetest_id: str,
        firetest_version: str,
        frontier_context: dict[str, Any] | None = None,
    ) -> tuple[FireTestProfile, dict[str, Any]]:
        lowered = (prompt or "").casefold()
        artifact_generation = any(token in lowered for token in ("artifact", "artefato", "reports/", ".csv", ".zip"))
        readonly = any(token in lowered for token in ("nao pode modificar", "não pode modificar", "sem modificar", "read-only"))
        discovery = any(token in lowered for token in ("discovery", "descoberta", "inventariar", "mapear", "analysis", "analise", "análise"))
        method = "heuristic_prompt_profile_selection"
        reason_codes = ["PROFILE_SELECTED_BY_READONLY_ARTIFACT_DISCOVERY"] if artifact_generation and readonly and discovery else ["PROFILE_SELECTED_BY_GENERIC_READONLY_ANALYSIS"]
        if frontier_context:
            reason_codes.append("FRONTIER_CONTEXT_ATTACHED")
        confidence = 0.86 if artifact_generation and readonly and discovery else 0.62
        project_analysis_cognition = self._project_analysis_cognition_from_frontier(frontier_context)
        public_response_boundary = self._public_response_boundary_from_frontier(frontier_context)
        metadata: dict[str, Any] = {
            "frontier_context": frontier_context or {},
            "profile_selection": {
                "method": method,
                "confidence": confidence,
                "reason_codes": reason_codes,
            },
            "semantic_maturity": {
                "truth_readiness": "not_ready",
                "confidence": 0.74,
            },
        }
        if project_analysis_cognition:
            metadata["project_analysis_cognition"] = project_analysis_cognition
        if public_response_boundary:
            metadata["public_response_boundary"] = public_response_boundary
        profile = FireTestProfile(
            profile_id=f"{firetest_id}_{firetest_version}_phase0_profile",
            name="Phase 0 Cognitive Readiness",
            objective="Predict the governed runtime frontier before execution.",
            domain="runtime_cognitive_readiness",
            expected_pipeline=[
                "Intent",
                "Lifecycle",
                "Workspace",
                "Contracts",
                "ProjectAnalysis",
                "ObservedEntity",
                "Perception",
                "Capability",
                "Observer",
                "ArtifactRuntime",
                "Validation",
                "Completion",
                "SpeakerTruth",
            ],
            involved_contracts=["analysis_readonly", "task_run_terminality", "artifact_runtime", "speaker_truth"],
            involved_modules=[
                "GovernanceLifecycleService",
                "ReadonlyAnalysisArtifactRuntimeService",
                "ProjectAnalysisService",
                "ProjectTreeService",
                "FileContextBuilder",
                "ArtifactRuntimeService",
                "UniversalTaskSessionService",
            ],
            expected_capabilities=["read_workspace", "artifact_generate"],
            expected_artifacts=[],
            success_contract={
                "runtime_execution_required": False,
                "phase0_must_not_create_task": True,
                "phase0_must_not_create_task_run": True,
                "phase0_must_not_create_operation": True,
                "phase0_prediction_required": True,
            },
            metadata=metadata,
        )
        return profile, {"method": method, "confidence": confidence, "reason_codes": reason_codes}

    def _public_response_boundary_from_frontier(self, frontier_context: dict[str, Any] | None) -> dict[str, Any]:
        if not isinstance(frontier_context, dict):
            return {}
        reason = str(frontier_context.get("predicted_reason_code") or frontier_context.get("reason_code") or "")
        component = str(frontier_context.get("predicted_component") or frontier_context.get("component") or "")
        frontier = str(frontier_context.get("predicted_frontier") or frontier_context.get("frontier") or "")
        public_tokens = (
            "PUBLIC_CHAT_RESPONSE_BOUNDARY",
            "PUBLIC_RESPONSE_ACCEPTED_RUNNING",
            "PUBLIC_RESPONSE_TIMEOUT_BLOCKED",
            "PUBLIC_RUNTIME_RESULT_FINALIZATION_MISSING",
            "PUBLIC_RUNTIME_CONTINUATION_NOT_AVAILABLE",
            "PUBLIC_ENDPOINT_SUMMARY_SLOW_OR_INCONSISTENT",
            "PHASE_DEPENDENCY_TEXT_FALSE_POSITIVE",
            "ARTIFACT_RENDER_LATE_ARTIFACT_REJECTED",
            "PHASE3_PUBLIC_PREACCEPTANCE_BOUNDARY",
            "PUBLIC_RUNTIME_PREACCEPTANCE_HEAVY_WORK_DETECTED",
            "PUBLIC_RUNTIME_CREATE_RUN_NOT_REACHED",
            "PHASE_PROGRESSION_STOP_CONDITION_REQUIRED",
            "PHASE_SKIPPED_DUE_TO_PRIOR_BLOCK",
            "ACCEPTED_RUNNING_ARTIFACT_WORKER_TERMINALIZATION_GAP",
            "ARTIFACT_RUNTIME_STALLED_AFTER_ARTIFACT_CREATION_STARTED",
            "ARTIFACT_CREATION_STARTED_WITHOUT_TERMINAL_ARTIFACT",
            "BACKGROUND_WORKER_EXCEPTION_AFTER_ACCEPTED_RUNNING",
            "TASKRUN_RESULT_MISSING_AFTER_ARTIFACT_START",
            "RESULT_ENDPOINT_404_AFTER_ARTIFACT_START",
            "ARTIFACT_WORKER_ORPHANED_AFTER_ACCEPTED_RUNNING",
            "ARTIFACT_REGISTRY_LEGACY_PROJECTION_UNREADABLE",
            "ARTIFACT_REGISTRY_LEGACY_TOO_LARGE_OR_INVALID",
            "ARTIFACT_REGISTRY_LEGACY_JSON_DECODE_ERROR",
            "PAYLOAD_REF_HYDRATION_BOUNDARY",
            "PAYLOAD_REF_HYDRATION_FAILED",
            "PAYLOAD_JSON_DECODE_ERROR",
            "PAYLOAD_TOO_LARGE_FOR_INLINE",
        )
        if not (
            any(token in reason or token in frontier for token in public_tokens)
            or "PublicRuntime" in component
            or "UniversalTaskSessionService" in component
            or "ArtifactRenderLifecycle" in component
            or "artifact_worker_terminalization_guard" in component
        ):
            return {}
        boundary: dict[str, Any] = {
            "reason_code": reason or None,
            "component": component or "PublicRuntimeResponsePolicy",
            "confidence": float(frontier_context.get("confidence") or 0.8),
        }
        if reason == "PUBLIC_RUNTIME_CONTINUATION_NOT_AVAILABLE":
            boundary["accepted_running_status"] = "not_available"
        elif reason == "PUBLIC_RESPONSE_TIMEOUT_BLOCKED":
            boundary["timeout_blocked_status"] = "missing"
        elif reason == "PUBLIC_RUNTIME_RESULT_FINALIZATION_MISSING":
            boundary["result_finalization_status"] = "missing"
        elif reason == "PUBLIC_ENDPOINT_SUMMARY_SLOW_OR_INCONSISTENT":
            boundary["endpoint_health"] = "inconsistent"
        elif reason == "PHASE_DEPENDENCY_TEXT_FALSE_POSITIVE":
            boundary["phase_dependency_boundary"] = "text_false_positive"
        elif reason == "ARTIFACT_RENDER_LATE_ARTIFACT_REJECTED":
            boundary["artifact_lifecycle_status"] = "late_artifact_rejected"
        elif reason == "PUBLIC_RUNTIME_PREACCEPTANCE_HEAVY_WORK_DETECTED":
            boundary["preacceptance_status"] = "heavy_work_detected"
        elif reason == "PUBLIC_RUNTIME_CREATE_RUN_NOT_REACHED":
            boundary["taskrun_bootstrap_status"] = "not_reached"
        elif reason == "PHASE_PROGRESSION_STOP_CONDITION_REQUIRED":
            boundary["phase_progression_status"] = "stop_condition_required"
        elif reason == "PHASE_SKIPPED_DUE_TO_PRIOR_BLOCK":
            boundary["phase_progression_status"] = "skipped_due_to_prior_block"
        elif reason == "ACCEPTED_RUNNING_ARTIFACT_WORKER_TERMINALIZATION_GAP":
            boundary["artifact_worker_terminalization"] = "missing"
        elif reason == "ARTIFACT_RUNTIME_STALLED_AFTER_ARTIFACT_CREATION_STARTED":
            boundary["artifact_runtime_status"] = "stalled_after_artifact_creation_started"
        elif reason == "ARTIFACT_CREATION_STARTED_WITHOUT_TERMINAL_ARTIFACT":
            boundary["artifact_runtime_status"] = "artifact_started_without_terminal"
        elif reason == "BACKGROUND_WORKER_EXCEPTION_AFTER_ACCEPTED_RUNNING":
            boundary["artifact_runtime_status"] = "orphaned_after_accept"
        elif reason == "TASKRUN_RESULT_MISSING_AFTER_ARTIFACT_START":
            boundary["result_finalization_status"] = "missing"
        elif reason == "RESULT_ENDPOINT_404_AFTER_ARTIFACT_START":
            boundary["result_endpoint_after_artifact_start"] = "404"
        elif reason == "ARTIFACT_WORKER_ORPHANED_AFTER_ACCEPTED_RUNNING":
            boundary["artifact_worker_terminalization"] = "orphaned"
        elif reason in {
            "ARTIFACT_REGISTRY_LEGACY_PROJECTION_UNREADABLE",
            "ARTIFACT_REGISTRY_LEGACY_TOO_LARGE_OR_INVALID",
            "ARTIFACT_REGISTRY_LEGACY_JSON_DECODE_ERROR",
        }:
            boundary["artifact_registry_status"] = "legacy_invalid"
            boundary["artifact_runtime_status"] = "artifact_creation_exception_after_accept"
        elif reason in {
            "PAYLOAD_REF_HYDRATION_BOUNDARY",
            "PAYLOAD_REF_HYDRATION_FAILED",
            "PAYLOAD_JSON_DECODE_ERROR",
            "PAYLOAD_TOO_LARGE_FOR_INLINE",
        }:
            boundary["payload_hydration_status"] = "json_decode_error" if "JSON" in reason else "too_large_for_inline"
        else:
            boundary["response_mode"] = "synchronous"
        return boundary

    def _project_analysis_cognition_from_frontier(self, frontier_context: dict[str, Any] | None) -> dict[str, Any]:
        if not isinstance(frontier_context, dict):
            return {}
        reason = str(frontier_context.get("predicted_reason_code") or frontier_context.get("reason_code") or "")
        component = str(frontier_context.get("predicted_component") or frontier_context.get("component") or "")
        frontier = str(frontier_context.get("predicted_frontier") or frontier_context.get("frontier") or "")
        project_analysis_reasons = (
            reason.startswith("PROJECT_ANALYSIS")
            or reason.startswith("MEDIA_CORPUS_ROOT")
            or reason in {"EXTENSION_NOT_ALLOWED_FOR_SOURCE_READING"}
        )
        if not (project_analysis_reasons or "ProjectAnalysis" in component or "PROJECT_ANALYSIS" in frontier):
            return {}
        cognition: dict[str, Any] = {
            "reason_code": reason or None,
            "component": component or "ProjectAnalysisService",
            "confidence": float(frontier_context.get("confidence") or 0.8),
        }
        if reason == "PROJECT_ANALYSIS_PARTIAL_CONTEXT_AVAILABLE":
            cognition.update(
                {
                    "file_read_status": "cooperative",
                    "partial_context_status": "available",
                    "cooperation_status": "active",
                }
            )
        elif reason == "MEDIA_CORPUS_ROOT_HANDOFF_READY":
            cognition.update(
                {
                    "file_read_status": "not_applicable_to_media_corpus",
                    "partial_context_status": "available",
                    "cooperation_status": "active",
                    "corpus_handoff_status": "ready",
                    "root_role_file_selection_status": "separated",
                }
            )
        elif reason in {"MEDIA_CORPUS_ROOT_NO_INVENTORY_ELIGIBLE_ENTITIES", "PROJECT_ANALYSIS_CORPUS_HANDOFF_FAILED"}:
            cognition.update(
                {
                    "file_read_status": "not_applicable_to_media_corpus",
                    "partial_context_status": "insufficient",
                    "cooperation_status": "active",
                    "corpus_handoff_status": "blocked",
                    "root_role_file_selection_status": "separated",
                }
            )
        elif reason == "PROJECT_ANALYSIS_ROOT_ROLE_FILE_SELECTION_MISMATCH":
            cognition.update(
                {
                    "file_read_status": "blocked",
                    "partial_context_status": "insufficient",
                    "cooperation_status": "active",
                    "corpus_handoff_status": "missing",
                    "root_role_file_selection_status": "mismatch",
                }
            )
        elif reason == "PROJECT_ANALYSIS_PARTIAL_CONTEXT_INSUFFICIENT":
            cognition.update(
                {
                    "file_read_status": "partial",
                    "partial_context_status": "insufficient",
                    "cooperation_status": "active",
                }
            )
        elif reason == "PROJECT_ANALYSIS_FILE_SKIPPED_BY_SINGLE_FILE_BUDGET":
            cognition.update(
                {
                    "file_read_status": "bounded",
                    "partial_context_status": "unknown",
                    "cooperation_status": "active",
                }
            )
        elif reason == "PROJECT_ANALYSIS_SELECTION_READ_COOPERATION_MISSING":
            cognition.update(
                {
                    "file_read_status": "blocked",
                    "partial_context_status": "unknown",
                    "cooperation_status": "missing",
                }
            )
        else:
            cognition.update(
                {
                    "file_read_status": "single_file_budget_exceeded",
                    "partial_context_status": "unknown",
                    "cooperation_status": "unknown",
                }
            )
        return cognition

    def calibrate_phase1(
        self,
        *,
        readiness: CognitiveReadinessResult,
        task_run_id: str,
        write_path: Path | None = None,
    ) -> CognitivePredictionCalibrationResult:
        run = self.store.get_run(task_run_id)
        result = self.store.get_result(task_run_id)
        actual = self._actual_from_runtime(run, result)
        prediction = readiness.prediction
        matched_outcome = self._outcome_matches(prediction.predicted_outcome, actual["outcome"])
        matched_frontier = self._match_token(prediction.predicted_frontier, actual["frontier"])
        matched_component = self._match_token(prediction.predicted_component, actual["component"])
        matched_reason = self._match_token(prediction.predicted_reason_code, actual["reason_code"])
        matched_contract = self._match_token(prediction.predicted_contract, actual["contract"])
        matched_capability = self._match_token(prediction.predicted_capability, actual["capability"])
        causal_score = self._causal_score(prediction.causal_chain, actual["causal_chain"])
        specificity = self._specificity_score(prediction)
        binary_scores = [matched_outcome, matched_frontier, matched_component, matched_reason, matched_contract]
        overall = (sum(1 for item in binary_scores if item) / len(binary_scores) * 0.7) + (causal_score * 0.3)
        confidence_error = abs(float(prediction.confidence) - overall)
        status = "matched" if overall >= 0.85 else "partial_match" if overall >= 0.45 else "mismatch"
        calibration = CognitivePredictionCalibrationResult(
            readiness_id=readiness.readiness_id,
            task_run_id=task_run_id,
            actual_outcome=actual["outcome"],
            actual_frontier=actual["frontier"],
            actual_component=actual["component"],
            actual_reason_code=actual["reason_code"],
            actual_contract=actual["contract"],
            actual_capability=actual["capability"],
            actual_causal_chain=actual["causal_chain"],
            prediction_matched_outcome=matched_outcome,
            prediction_matched_frontier=matched_frontier,
            prediction_matched_component=matched_component,
            prediction_matched_reason_code=matched_reason,
            prediction_matched_contract=matched_contract,
            prediction_matched_capability=matched_capability,
            prediction_matched_causal_chain=causal_score >= 0.5,
            confidence_was_calibrated=confidence_error <= 0.2,
            confidence_error=round(confidence_error, 4),
            specificity_score=specificity,
            causal_accuracy_score=causal_score,
            overall_accuracy_score=round(overall, 4),
            false_positive=prediction.predicted_outcome == "blocked" and actual["outcome"] not in {"blocked", "timeout", "failed"},
            false_negative=prediction.predicted_outcome != "blocked" and actual["outcome"] in {"blocked", "timeout", "failed"},
            overconfidence=float(prediction.confidence) > overall + 0.2,
            underconfidence=float(prediction.confidence) + 0.2 < overall,
            divergence_explanation=self._divergence(
                matched_frontier=matched_frontier,
                matched_component=matched_component,
                matched_reason=matched_reason,
                actual=actual,
                prediction=prediction,
            ),
            lessons=self._lessons(status, actual),
            status=status,
        )
        path = write_path or (self.runtime_reports_root / "firetest5_phase0_vs_phase1_calibration.json")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(calibration.model_dump(mode="json"), indent=2, ensure_ascii=False), encoding="utf-8")
        return calibration

    def load_readiness(self, readiness_id_or_path: str) -> CognitiveReadinessResult | None:
        path = Path(readiness_id_or_path)
        if not path.exists():
            path = self.runtime_reports_root / "firetest5_phase0_cognitive_readiness_result.json"
        if not path.exists():
            return None
        return CognitiveReadinessResult.model_validate(json.loads(path.read_text(encoding="utf-8")))

    def lightweight_summary(
        self,
        *,
        readiness_ref: str | None,
        task_run_id: str | None = None,
        runtime_executed_despite_no_go: bool = False,
    ) -> dict[str, Any] | None:
        if not readiness_ref:
            return None
        readiness = self.load_readiness(readiness_ref)
        if readiness is None:
            return {"readiness_id": readiness_ref, "status": "missing"}
        calibration = None
        readiness_path = Path(readiness_ref)
        candidate_paths = []
        if readiness_path.exists():
            candidate_paths.append(readiness_path.parent / "firetest5_phase0_vs_phase1_calibration.json")
        candidate_paths.append(self.runtime_reports_root / "firetest5_phase0_vs_phase1_calibration.json")
        for calibration_path in candidate_paths:
            if not calibration_path.exists():
                continue
            try:
                payload = json.loads(calibration_path.read_text(encoding="utf-8"))
                if not task_run_id or payload.get("task_run_id") == task_run_id:
                    calibration = payload
                    break
            except Exception:
                calibration = None
        return {
            "readiness_id": readiness.readiness_id,
            "decision": readiness.decision.decision,
            "confidence": readiness.confidence,
            "predicted_frontier": readiness.prediction.predicted_frontier,
            "predicted_component": readiness.prediction.predicted_component,
            "predicted_reason_code": readiness.prediction.predicted_reason_code,
            "runtime_executed_despite_no_go": runtime_executed_despite_no_go,
            "calibration": {
                "status": calibration.get("status") if isinstance(calibration, dict) else "pending",
                "overall_accuracy_score": calibration.get("overall_accuracy_score") if isinstance(calibration, dict) else None,
            },
            "details_ref": str(self.runtime_reports_root / "firetest5_phase0_cognitive_readiness_result.json"),
        }

    def _prediction(self, profile: FireTestProfile, prediction_report, *, frontier_context: dict[str, Any] | None = None) -> CognitivePrediction:
        boundary = frontier_context if isinstance(frontier_context, dict) else {}
        predicted_reason = str(boundary.get("predicted_reason_code") or boundary.get("reason_code") or "") or (
            prediction_report.reason_codes[0] if prediction_report.reason_codes else None
        )
        predicted_component = str(boundary.get("predicted_component") or boundary.get("component") or "") or prediction_report.probable_component
        predicted_frontier = str(boundary.get("predicted_frontier") or boundary.get("frontier") or "") or self._frontier_from_component(predicted_component)
        causal_chain = self._string_list(boundary.get("causal_chain")) or list(profile.expected_pipeline)
        critical_dependencies = self._string_list(boundary.get("critical_dependencies")) or list(
            dict.fromkeys([*profile.expected_capabilities, *profile.involved_contracts])
        )
        return CognitivePrediction(
            predicted_outcome="blocked" if predicted_reason else str(prediction_report.predicted_status),
            predicted_frontier=predicted_frontier,
            predicted_component=predicted_component,
            predicted_contract=prediction_report.probable_contract or "analysis_readonly",
            predicted_capability=prediction_report.probable_capability,
            predicted_observer=str(boundary.get("predicted_observer") or boundary.get("observer") or "") or None,
            predicted_reason_code=predicted_reason,
            predicted_blocking_stage=str(boundary.get("predicted_blocking_stage") or boundary.get("blocking_stage") or "") or None,
            predicted_failure_mode=str(boundary.get("predicted_failure_mode") or "") or (
                "governed_timeout" if predicted_reason and "TIMEOUT" in predicted_reason else "cognitive_block"
            ),
            confidence=float(boundary.get("confidence") or prediction_report.confidence or 0.0),
            causal_chain=causal_chain,
            critical_dependencies=critical_dependencies,
            alternative_hypotheses=self._string_list(boundary.get("alternative_hypotheses")),
            false_positive_risks=self._string_list(boundary.get("false_positive_risks")),
            false_negative_risks=self._string_list(boundary.get("false_negative_risks")),
        )

    def _decision(self, prediction: CognitivePrediction) -> CognitiveReadinessDecision:
        if prediction.predicted_outcome == "blocked":
            decision = "NO_GO_EXPECTED_BLOCK"
            safe = False
            override = True
            risk = "high"
        elif prediction.confidence < 0.7:
            decision = "GO_WITH_RISK"
            safe = True
            override = False
            risk = "medium"
        else:
            decision = "GO"
            safe = True
            override = False
            risk = "low"
        return CognitiveReadinessDecision(
            decision=decision,  # type: ignore[arg-type]
            confidence=prediction.confidence,
            rationale="CVL predicts the current dominant governed boundary before Runtime execution.",
            expected_risk_level=risk,
            expected_blocking_frontier=prediction.predicted_frontier,
            expected_blocking_component=prediction.predicted_component,
            expected_blocking_reason_code=prediction.predicted_reason_code,
            safe_to_start_phase1=safe,
            requires_user_override=override,
        )

    def _dependency_graph(self, profile: FireTestProfile, graph, prediction: CognitivePrediction) -> CognitiveDependencyGraph:
        return CognitiveDependencyGraph(
            graph=graph,
            nodes=[node.model_dump(mode="json") for node in graph.nodes],
            edges=list(graph.edges),
            critical_path=list(prediction.causal_chain),
            critical_dependencies=list(prediction.critical_dependencies),
            expected_modules=list(profile.involved_modules),
            expected_contracts=list(profile.involved_contracts),
            expected_capabilities=list(profile.expected_capabilities),
            expected_observers=self._string_list(profile.metadata.get("expected_observers")),
            expected_artifacts=list(profile.expected_artifacts),
            expected_validation_gates=["Validation", "Completion"],
            expected_truth_gates=["SpeakerTruth"],
            possible_bottlenecks=[item for item in [prediction.predicted_frontier, *prediction.alternative_hypotheses] if item],
        )

    def _coverage_report(self, coverage) -> CognitiveCoverageReport:
        by_domain = {metric.domain: metric.coverage for metric in coverage.metrics}
        critical = [metric.coverage for metric in coverage.metrics if metric.criticality in {"high", "critical"}]
        return CognitiveCoverageReport(
            coverage=coverage,
            coverage_by_domain=by_domain,
            overall_coverage=coverage.overall_coverage,
            critical_coverage=round(sum(critical) / max(1, len(critical)), 4),
            coverage_confidence=round(sum(metric.confidence for metric in coverage.metrics) / max(1, len(coverage.metrics)), 4),
            unknown_areas=[metric.domain for metric in coverage.metrics if "unknown" in metric.gaps],
            weak_areas=[metric.domain for metric in coverage.metrics if metric.coverage < 0.5],
            strong_areas=[metric.domain for metric in coverage.metrics if metric.coverage >= 0.95],
            coverage_reason_codes=[f"COVERAGE_{metric.domain.upper()}_{metric.health.upper()}" for metric in coverage.metrics],
        )

    def _simulation_result(self, profile: FireTestProfile, simulation, prediction: CognitivePrediction) -> CognitiveSimulationResult:
        steps = [step.model_copy(deep=True) for step in simulation.steps]
        blocked = next((step for step in steps if step.status == "predicted_blocked"), None)
        if blocked is None and prediction.predicted_outcome == "blocked" and prediction.predicted_frontier:
            target_index = self._predicted_block_step_index(steps, prediction)
            if target_index is not None:
                for index, step in enumerate(steps):
                    if index == target_index:
                        step.status = "predicted_blocked"
                        step.reason_code = prediction.predicted_reason_code or "PREDICTED_BLOCK"
                        step.explanation = (
                            "Explicit frontier context predicts this component as the current governed boundary."
                        )
                        step.confidence = prediction.confidence
                        blocked = step
                    elif index > target_index:
                        step.status = "predicted_skipped"
                        step.reason_code = "UPSTREAM_PREDICTED_BLOCK"
                        step.explanation = (
                            "Step skipped in simulation because an upstream boundary is predicted to block."
                        )
                        step.confidence = prediction.confidence
        simulated = simulation.model_copy(update={"steps": steps, "status": "blocked" if blocked else simulation.status})
        return CognitiveSimulationResult(
            simulation=simulated,
            simulation_id=simulated.simulation_id,
            simulated_path=[step.component for step in steps],
            simulated_steps=[step.model_dump(mode="json") for step in steps],
            simulated_blocking_point=blocked.component if blocked else None,
            simulated_reason_code=blocked.reason_code if blocked else None,
            simulated_confidence=prediction.confidence if blocked else simulation.confidence,
            contracts_involved=list(profile.involved_contracts),
            capabilities_involved=list(profile.expected_capabilities),
            observers_required=self._string_list(profile.metadata.get("expected_observers")),
            evidence_required=["runtime_evidence", "validation_evidence", "speaker_truth_evidence"],
            artifacts_expected=list(profile.expected_artifacts),
            validation_expected=["Validation must be based on real execution, not CVL."],
            truth_expected=["Speaker Truth must be based on real execution, not CVL."],
            simulation_limitations=["Simulation is cognitive only and does not execute Runtime."],
        )

    def _predicted_block_step_index(self, steps: list[Any], prediction: CognitivePrediction) -> int | None:
        for candidate in [prediction.predicted_component, prediction.predicted_frontier, prediction.predicted_blocking_stage]:
            for index, step in enumerate(steps):
                component = str(getattr(step, "component", "") or "")
                if self._component_overlaps(component, candidate):
                    return index
        for candidate in reversed(prediction.causal_chain):
            for index, step in enumerate(steps):
                component = str(getattr(step, "component", "") or "")
                if self._component_overlaps(component, candidate):
                    return index
        return None

    def _component_overlaps(self, component: str, candidate: str | None) -> bool:
        if not candidate:
            return False
        component_token = self._normalize_match_token(component)
        candidate_token = self._normalize_match_token(candidate)
        return bool(component_token and candidate_token and (component_token in candidate_token or candidate_token in component_token))

    def _normalize_match_token(self, value: str) -> str:
        token = "".join(char for char in value.casefold() if char.isalnum())
        return token.removesuffix("service")

    def _frontier_report(self, prediction: CognitivePrediction) -> CognitiveFrontierReport:
        return CognitiveFrontierReport(
            primary_frontier=prediction.predicted_frontier,
            secondary_frontiers=list(prediction.alternative_hypotheses),
            frontier_chain=list(prediction.causal_chain),
            frontier_confidence=prediction.confidence,
            why_this_frontier=f"Predicted reason code is {prediction.predicted_reason_code}.",
            what_would_move_frontier_forward=[
                "Improve ProjectAnalysis file selection/read cooperation under budget.",
                "Repeat H1B4.3.3 artifact terminality diagnostic after ProjectAnalysis crosses.",
            ],
            required_capabilities=list(prediction.critical_dependencies),
            required_observability=["checkpoint_metrics", "reason_code_specificity", "runtime_terminal_events"],
            required_runtime_changes=["file_read_budget_cooperation", "public_chat_governed_response_boundary"],
        )

    def _actual_from_runtime(self, run, result) -> dict[str, Any]:
        outputs = result.outputs if result is not None else {}
        validation = outputs.get("validation_result", {}) if isinstance(outputs, dict) else {}
        details = validation.get("details", {}) if isinstance(validation, dict) else {}
        frontier = details.get("frontier") or details.get("blocking_operation")
        reason = validation.get("reason_code") or details.get("project_analysis_reason_code") or details.get("reason_code")
        component = validation.get("component") or details.get("component")
        outcome = result.status if result is not None else (run.status if run is not None else "unknown")
        actual_frontier = self._frontier_from_actual(frontier, reason)
        return {
            "outcome": outcome,
            "frontier": actual_frontier,
            "component": component,
            "reason_code": reason,
            "contract": getattr(run, "contract_type", None) if run is not None else None,
            "capability": None,
            "causal_chain": [
                item
                for item in [
                    "Intent",
                    "Lifecycle",
                    "Workspace",
                    "Contracts",
                    component,
                    details.get("blocking_operation"),
                    reason,
                ]
                if item
            ],
        }

    def _frontier_from_actual(self, frontier: Any, reason: Any) -> str | None:
        reason_text = str(reason or "")
        if reason_text.endswith("_TIMEOUT"):
            return reason_text.removesuffix("_TIMEOUT")
        if reason_text.endswith("_BLOCKED"):
            return reason_text.removesuffix("_BLOCKED")
        if reason_text.endswith("_FAILED"):
            return reason_text.removesuffix("_FAILED")
        if frontier:
            return str(frontier)
        return None

    def _frontier_from_component(self, component: str | None) -> str | None:
        if not component:
            return None
        normalized = component.upper().replace("SERVICE", "").replace("__", "_").strip("_")
        return normalized

    def _outcome_matches(self, predicted: str | None, actual: str | None) -> bool:
        if not predicted or not actual:
            return False
        if predicted == actual:
            return True
        return predicted == "blocked" and actual in {"blocked", "timeout", "failed"}

    def _match_token(self, predicted: str | None, actual: str | None) -> bool:
        if not predicted or not actual:
            return False
        return predicted.casefold() == actual.casefold()

    def _causal_score(self, predicted: list[str], actual: list[str]) -> float:
        if not predicted:
            return 0.0
        actual_tokens = {str(item).casefold() for item in actual}
        matched = sum(1 for item in predicted if str(item).casefold() in actual_tokens)
        return round(matched / len(predicted), 4)

    def _specificity_score(self, prediction: CognitivePrediction) -> float:
        fields = [
            prediction.predicted_frontier,
            prediction.predicted_component,
            prediction.predicted_contract,
            prediction.predicted_reason_code,
            prediction.predicted_blocking_stage,
        ]
        return round(sum(1 for item in fields if item) / len(fields), 4)

    def _divergence(self, *, matched_frontier: bool, matched_component: bool, matched_reason: bool, actual: dict[str, Any], prediction: CognitivePrediction) -> str:
        if matched_frontier and matched_component and matched_reason:
            return "Prediction matched the dominant Phase 1 boundary."
        return (
            "Prediction diverged from actual runtime boundary. "
            f"Predicted {prediction.predicted_frontier}/{prediction.predicted_component}/{prediction.predicted_reason_code}; "
            f"actual {actual.get('frontier')}/{actual.get('component')}/{actual.get('reason_code')}."
        )

    def _lessons(self, status: str, actual: dict[str, Any]) -> list[str]:
        if status == "matched":
            return ["Current CVL frontier model is calibrated for this Phase 1 boundary."]
        return [f"Update CVL model with actual boundary {actual.get('frontier')} and reason {actual.get('reason_code')}."]

    def _rewrite_phase0_reports(self, report_paths: dict[str, str]) -> dict[str, str]:
        self.firetest_reports_root.mkdir(parents=True, exist_ok=True)
        mapping = {
            "firetest_lab": "phase0_cognitive_readiness.md",
            "prediction_report": "phase0_prediction.md",
            "dependency_graph": "phase0_dependency_graph.md",
            "coverage_report": "phase0_coverage.md",
            "simulation_report": "phase0_simulation.md",
            "laboratory_summary": "phase0_frontier.md",
        }
        rewritten: dict[str, str] = {}
        for key, target_name in mapping.items():
            source = Path(report_paths.get(key, ""))
            target = self.firetest_reports_root / target_name
            if source.exists():
                target.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
            else:
                target.write_text(f"# {target_name}\n\nNo CVL source report was available.\n", encoding="utf-8")
            rewritten[key] = str(target)
        return rewritten

    def _write_readiness(self, readiness: CognitiveReadinessResult) -> None:
        self.runtime_reports_root.mkdir(parents=True, exist_ok=True)
        path = self.runtime_reports_root / "firetest5_phase0_cognitive_readiness_result.json"
        path.write_text(json.dumps(readiness.model_dump(mode="json"), indent=2, ensure_ascii=False), encoding="utf-8")
        self._write_canonical_phase0_reports(readiness)

    def _write_canonical_phase0_reports(self, readiness: CognitiveReadinessResult) -> None:
        self.firetest_reports_root.mkdir(parents=True, exist_ok=True)
        reports = {
            "phase0_cognitive_readiness.md": self._phase0_readiness_markdown(readiness),
            "phase0_prediction.md": self._phase0_prediction_markdown(readiness),
            "phase0_dependency_graph.md": self._phase0_dependency_graph_markdown(readiness),
            "phase0_coverage.md": self._phase0_coverage_markdown(readiness),
            "phase0_simulation.md": self._phase0_simulation_markdown(readiness),
            "phase0_frontier.md": self._phase0_frontier_markdown(readiness),
            "phase6_prediction_accuracy.md": self._phase6_prediction_accuracy_markdown(readiness),
            "phase6_cvl_validation.md": self._phase6_cvl_validation_markdown(readiness),
        }
        for filename, content in reports.items():
            (self.firetest_reports_root / filename).write_text(content, encoding="utf-8")

    def _phase0_readiness_markdown(self, readiness: CognitiveReadinessResult) -> str:
        return "\n".join(
            [
                "# FireTest Phase 0 - Cognitive Readiness",
                "",
                f"- Readiness ID: `{readiness.readiness_id}`",
                f"- FireTest: `{readiness.firetest_id}`",
                f"- Version: `{readiness.firetest_version}`",
                f"- Status: `{readiness.status}`",
                f"- Decision: `{readiness.decision.decision}`",
                f"- Confidence: `{readiness.confidence}`",
                f"- Safe to start Phase 1: `{readiness.safe_to_start_phase1}`",
                "",
                "## Phase 0 Invariants",
                "",
                f"- Runtime executed: `{readiness.runtime_executed}`",
                f"- Task created: `{readiness.task_created}`",
                f"- TaskRun created: `{readiness.task_run_created}`",
                f"- Operation created: `{readiness.operation_created}`",
                f"- Operational artifacts created: `{readiness.operational_artifacts_created}`",
                "",
                "Phase 0 is cognitive only. It does not decide operational success.",
                "",
            ]
        )

    def _phase0_prediction_markdown(self, readiness: CognitiveReadinessResult) -> str:
        prediction = readiness.prediction
        return "\n".join(
            [
                "# FireTest Phase 0 - Prediction",
                "",
                f"- Prediction ID: `{prediction.prediction_id}`",
                f"- Predicted outcome: `{prediction.predicted_outcome}`",
                f"- Predicted frontier: `{prediction.predicted_frontier}`",
                f"- Predicted component: `{prediction.predicted_component}`",
                f"- Predicted contract: `{prediction.predicted_contract}`",
                f"- Predicted capability: `{prediction.predicted_capability}`",
                f"- Predicted observer: `{prediction.predicted_observer}`",
                f"- Predicted reason code: `{prediction.predicted_reason_code}`",
                f"- Predicted blocking stage: `{prediction.predicted_blocking_stage}`",
                f"- Confidence: `{prediction.confidence}`",
                "",
                "## Causal Chain",
                "",
                *[f"- `{item}`" for item in prediction.causal_chain],
                "",
            ]
        )

    def _phase0_dependency_graph_markdown(self, readiness: CognitiveReadinessResult) -> str:
        graph = readiness.dependency_graph
        return "\n".join(
            [
                "# FireTest Phase 0 - Dependency Graph",
                "",
                f"- Nodes: `{len(graph.nodes)}`",
                f"- Edges: `{len(graph.edges)}`",
                "",
                "## Critical Path",
                "",
                *[f"- `{item}`" for item in graph.critical_path],
                "",
                "## Possible Bottlenecks",
                "",
                *[f"- `{item}`" for item in graph.possible_bottlenecks],
                "",
            ]
        )

    def _phase0_coverage_markdown(self, readiness: CognitiveReadinessResult) -> str:
        coverage = readiness.coverage_report
        lines = [
            "# FireTest Phase 0 - Cognitive Coverage",
            "",
            f"- Overall coverage: `{coverage.overall_coverage}`",
            f"- Critical coverage: `{coverage.critical_coverage}`",
            f"- Coverage confidence: `{coverage.coverage_confidence}`",
            "",
            "## Coverage By Domain",
            "",
        ]
        lines.extend(f"- `{domain}`: `{value}`" for domain, value in coverage.coverage_by_domain.items())
        lines.extend(["", "Coverage is diagnostic only, not operational success.", ""])
        return "\n".join(lines)

    def _phase0_simulation_markdown(self, readiness: CognitiveReadinessResult) -> str:
        simulation = readiness.simulation_result
        lines = [
            "# FireTest Phase 0 - Cognitive Simulation",
            "",
            f"- Simulation ID: `{simulation.simulation_id}`",
            f"- Simulated blocking point: `{simulation.simulated_blocking_point}`",
            f"- Simulated reason code: `{simulation.simulated_reason_code}`",
            f"- Simulated confidence: `{simulation.simulated_confidence}`",
            "",
            "## Steps",
            "",
        ]
        for step in simulation.simulated_steps:
            lines.append(
                f"- `{step.get('index')}` `{step.get('component')}`: `{step.get('status')}` "
                f"reason=`{step.get('reason_code')}`"
            )
        lines.extend(["", "Simulation does not execute Runtime.", ""])
        return "\n".join(lines)

    def _phase0_frontier_markdown(self, readiness: CognitiveReadinessResult) -> str:
        frontier = readiness.frontier_report
        return "\n".join(
            [
                "# FireTest Phase 0 - Cognitive Frontier",
                "",
                f"- Frontier ID: `{frontier.frontier_id}`",
                f"- Primary frontier: `{frontier.primary_frontier}`",
                f"- Frontier confidence: `{frontier.frontier_confidence}`",
                f"- Why this frontier: {frontier.why_this_frontier}",
                "",
                "## Secondary Frontiers",
                "",
                *[f"- `{item}`" for item in frontier.secondary_frontiers],
                "",
                "## What Would Move The Frontier Forward",
                "",
                *[f"- {item}" for item in frontier.what_would_move_frontier_forward],
                "",
            ]
        )

    def _phase6_prediction_accuracy_markdown(self, readiness: CognitiveReadinessResult) -> str:
        return "\n".join(
            [
                "# FireTest Phase 6 - Prediction Accuracy",
                "",
                f"- Readiness ID: `{readiness.readiness_id}`",
                "- Status: `pending_phase6_execution`",
                "",
                "Phase 6 calibration will compare the Phase 0 prediction against final runtime validation.",
                "",
            ]
        )

    def _phase6_cvl_validation_markdown(self, readiness: CognitiveReadinessResult) -> str:
        return "\n".join(
            [
                "# FireTest Phase 6 - CVL Validation",
                "",
                f"- Readiness ID: `{readiness.readiness_id}`",
                "- Status: `pending_phase6_execution`",
                "",
                "CVL validation remains separate from Validation, Completion, and Speaker Truth.",
                "",
            ]
        )

    def _hash(self, value: str) -> str:
        return hashlib.sha256((value or "").encode("utf-8")).hexdigest()

    def _string_list(self, value: Any) -> list[str]:
        if not isinstance(value, list):
            return []
        return [str(item) for item in value if str(item or "")]
