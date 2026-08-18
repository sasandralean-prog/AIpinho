from __future__ import annotations

import csv
import io
import json
from datetime import datetime, timezone
from typing import Any

from aipinho.schemas.artifacts.artifact_runtime import ArtifactRuntimeCreateRequest
from aipinho.schemas.runtime.runtime_doctor import (
    ExpectedRuntimeContract,
    RegressionFinding,
    RegressionMatrix,
    RuntimeDoctorArtifactRefs,
    RuntimeDoctorReport,
)
from aipinho.services.artifacts.artifact_runtime_service import ArtifactRuntimeService


def _dump_model(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    if hasattr(value, "dict"):
        return value.dict()
    if isinstance(value, dict):
        return value
    return {"value": str(value)}


class RuntimeDoctorService:
    """Read-only, contract-based diagnostics for runtime executions."""

    DOMAINS = (
        "text_ingress",
        "encoding",
        "semantic_normalization",
        "semantic_propositions",
        "state_effects",
        "intent_candidates",
        "intent_arbitration",
        "operation_contract_selection",
        "intent",
        "inference",
        "diagnosis",
        "repair_intent",
        "semantic_evidence",
        "behavior_localization",
        "behavior_justification",
        "candidate_transformation",
        "patch_candidate",
        "actionability",
        "prompt",
        "completeness",
        "context_budget",
        "firetest_lab",
        "prediction",
        "dependency_graph",
        "coverage",
        "simulation",
        "prediction_accuracy",
        "simulation_accuracy",
        "lifecycle",
        "workspace_binding",
        "artifact_contract",
        "entity_compilation",
        "contract_observation",
        "entity_selection",
        "observation_planning",
        "observation_goal",
        "observation_strategy",
        "capability_registry",
        "capability_matching",
        "capability_arbitration",
        "observer_capability",
        "observer_execution",
        "attribute_observation",
        "evidence_recording",
        "knowledge_representation",
        "semantic_assertions",
        "semantic_self_review",
        "truth_readiness",
        "coverage_analysis",
        "artifact_renderer",
        "schema_coverage",
        "approval",
        "validation",
        "completion",
        "speaker_truth",
        "patch_planning",
        "dispatcher",
        "timeline",
    )

    SUSPECTED_MODULES = {
        "text_ingress": [
            "schemas/semantic_runtime/semantic_ingress.py",
            "services/semantic_runtime/semantic_ingress_doctor_service.py",
            "services/governance/lifecycle/public_route_lifecycle_service.py",
        ],
        "encoding": [
            "services/governance/intent/intent_normalizer.py",
            "services/semantic_runtime/semantic_ingress_doctor_service.py",
        ],
        "semantic_normalization": [
            "services/semantic_runtime/semantic_proposition_normalization_service.py",
            "services/semantic_runtime/semantic_ingress_doctor_service.py",
        ],
        "semantic_propositions": [
            "schemas/semantic_runtime/semantic_ingress.py",
            "services/semantic_runtime/semantic_ingress_doctor_service.py",
        ],
        "state_effects": [
            "schemas/intent/semantic_intent_graph.py",
            "services/semantic_runtime/semantic_proposition_normalization_service.py",
            "services/semantic_runtime/semantic_ingress_doctor_service.py",
        ],
        "intent_candidates": [
            "schemas/semantic_runtime/semantic_ingress.py",
            "services/governance/intent/canonical_intent_router.py",
            "services/semantic_runtime/semantic_ingress_doctor_service.py",
        ],
        "intent_arbitration": [
            "services/governance/intent/canonical_intent_router.py",
            "services/semantic_runtime/semantic_intent_resolution_service.py",
            "services/semantic_runtime/semantic_ingress_doctor_service.py",
        ],
        "operation_contract_selection": [
            "services/governance/lifecycle/governance_lifecycle_service.py",
            "services/governance/operation_contract_service.py",
            "services/semantic_runtime/semantic_ingress_doctor_service.py",
        ],
        "intent": [
            "services/governance/intent",
            "services/prompt_intelligence",
            "services/governance/lifecycle",
        ],
        "lifecycle": [
            "services/runtime/task_bootstrap_runtime_service.py",
            "services/runtime/task_runtime_service.py",
            "services/runtime/canonical_operation_state_service.py",
        ],
        "workspace_binding": [
            "schemas/runtime/workspace_context.py",
            "services/runtime/workspace_context_service.py",
        ],
        "artifact_contract": [
            "services/artifacts/artifact_runtime_service.py",
            "services/artifacts/universal_artifact_registry_service.py",
            "services/artifacts/artifact_semantic_contract_service.py",
            "services/runtime/canonical_operation_state_service.py",
        ],
        "entity_compilation": [
            "schemas/artifacts/observed_entity.py",
            "services/artifacts/observed_entity_compilation_service.py",
            "services/governance/runtime/readonly_analysis_artifact_runtime_service.py",
        ],
        "contract_observation": [
            "schemas/artifacts/contract_perception.py",
            "services/artifacts/contract_driven_perception_service.py",
        ],
        "entity_selection": [
            "schemas/artifacts/contract_perception.py",
            "services/artifacts/contract_driven_perception_service.py",
        ],
        "observation_planning": [
            "schemas/artifacts/contract_perception.py",
            "services/artifacts/contract_driven_perception_service.py",
        ],
        "observation_goal": [
            "schemas/artifacts/contract_perception.py",
            "services/artifacts/contract_driven_perception_service.py",
        ],
        "observation_strategy": [
            "schemas/artifacts/contract_perception.py",
            "services/artifacts/contract_driven_perception_service.py",
        ],
        "capability_registry": [
            "schemas/artifacts/contract_perception.py",
            "services/artifacts/contract_driven_perception_service.py",
        ],
        "capability_matching": [
            "schemas/artifacts/contract_perception.py",
            "services/artifacts/contract_driven_perception_service.py",
        ],
        "capability_arbitration": [
            "schemas/artifacts/contract_perception.py",
            "services/artifacts/contract_driven_perception_service.py",
        ],
        "observer_capability": [
            "schemas/artifacts/contract_perception.py",
            "services/artifacts/contract_driven_perception_service.py",
        ],
        "observer_execution": [
            "schemas/artifacts/contract_perception.py",
            "services/artifacts/contract_driven_perception_service.py",
            "services/artifacts/observation_execution_boundary_service.py",
        ],
        "attribute_observation": [
            "schemas/artifacts/contract_perception.py",
            "services/artifacts/contract_driven_perception_service.py",
        ],
        "evidence_recording": [
            "schemas/artifacts/contract_perception.py",
            "services/artifacts/contract_driven_perception_service.py",
            "services/artifacts/observation_execution_boundary_service.py",
        ],
        "knowledge_representation": [
            "schemas/artifacts/contract_perception.py",
            "services/artifacts/contract_driven_perception_service.py",
        ],
        "semantic_assertions": [
            "schemas/artifacts/contract_perception.py",
            "services/artifacts/contract_driven_perception_service.py",
        ],
        "semantic_self_review": [
            "schemas/artifacts/contract_perception.py",
            "services/artifacts/contract_driven_perception_service.py",
        ],
        "truth_readiness": [
            "schemas/artifacts/contract_perception.py",
            "services/artifacts/contract_driven_perception_service.py",
            "services/runtime/runtime_truth_engine.py",
        ],
        "coverage_analysis": [
            "schemas/artifacts/contract_perception.py",
            "schemas/artifacts/artifact_semantic_profile.py",
            "services/artifacts/artifact_semantic_contract_service.py",
        ],
        "artifact_renderer": [
            "services/governance/runtime/readonly_analysis_artifact_runtime_service.py",
        ],
        "schema_coverage": [
            "schemas/artifacts/artifact_semantic_profile.py",
            "services/artifacts/artifact_semantic_contract_service.py",
        ],
        "approval": [
            "services/approvals",
            "services/governance/lifecycle",
        ],
        "validation": [
            "services/runtime/tool_governance_service.py",
            "services/runtime/canonical_operation_state_service.py",
        ],
        "completion": [
            "schemas/runtime/task_completion.py",
            "services/runtime/canonical_operation_state_service.py",
        ],
        "speaker_truth": [
            "services/runtime/runtime_truth_engine.py",
            "services/speaker",
        ],
        "patch_planning": [
            "schemas/patching/canonical_diagnosis_artifact.py",
            "schemas/patching/patch_candidate_artifact.py",
            "services/patching/diagnosis_runtime_service.py",
            "services/patching/patch_candidate_builder.py",
            "services/patching/patch_planning_service.py",
            "services/patching/model_assisted_patch_planner_service.py",
        ],
        "inference": [
            "schemas/models/inference_runtime.py",
            "schemas/models/inference_observability.py",
            "services/models/inference_runtime_service.py",
            "services/models/inference_input_doctor_service.py",
            "services/models/model_invocation_service.py",
            "services/models/llama_cpp_provider.py",
            "services/models/model_process_runner.py",
        ],
        "diagnosis": [
            "schemas/patching/canonical_diagnosis_artifact.py",
            "services/patching/diagnosis_runtime_service.py",
            "services/patching/diagnosis_quality_analyzer.py",
        ],
        "repair_intent": [
            "schemas/patching/canonical_diagnosis_artifact.py",
            "services/patching/repair_intent_resolver.py",
            "services/patching/diagnosis_runtime_service.py",
        ],
        "semantic_evidence": [
            "schemas/patching/diagnosis_pipeline_artifact.py",
            "services/patching/diagnosis_pipeline_compiler.py",
            "services/patching/diagnosis_runtime_service.py",
        ],
        "behavior_localization": [
            "schemas/patching/diagnosis_pipeline_artifact.py",
            "services/patching/diagnosis_pipeline_compiler.py",
            "services/patching/diagnosis_alignment_validator.py",
        ],
        "behavior_justification": [
            "schemas/patching/diagnosis_pipeline_artifact.py",
            "services/patching/diagnosis_pipeline_compiler.py",
            "services/patching/diagnosis_alignment_validator.py",
        ],
        "candidate_transformation": [
            "schemas/patching/diagnosis_pipeline_artifact.py",
            "services/patching/diagnosis_pipeline_compiler.py",
            "services/patching/model_assisted_patch_planner_service.py",
        ],
        "patch_candidate": [
            "schemas/patching/patch_candidate_artifact.py",
            "services/patching/diagnosis_runtime_service.py",
            "services/patching/patch_candidate_quality_analyzer.py",
        ],
        "actionability": [
            "schemas/patching/patch_observability.py",
            "services/patching/diagnosis_runtime_service.py",
            "services/patching/patch_candidate_actionability_analyzer.py",
            "services/patching/model_assisted_patch_planner_service.py",
        ],
        "prompt": [
            "schemas/models/inference_observability.py",
            "services/models/inference_input_doctor_service.py",
            "services/roles/role_prompt_contract_builder.py",
        ],
        "completeness": [
            "services/models/inference_input_doctor_service.py",
            "services/patching/diagnosis_quality_analyzer.py",
            "services/patching/patch_candidate_quality_analyzer.py",
        ],
        "context_budget": [
            "schemas/models/inference_observability.py",
            "services/models/inference_input_doctor_service.py",
            "services/roles/role_inference_budget_service.py",
        ],
        "firetest_lab": [
            "schemas/cvl/cognitive_validation_laboratory.py",
            "services/cvl/cognitive_validation_laboratory_service.py",
        ],
        "prediction": [
            "schemas/cvl/cognitive_validation_laboratory.py",
            "services/cvl/cognitive_validation_laboratory_service.py",
        ],
        "dependency_graph": [
            "schemas/cvl/cognitive_validation_laboratory.py",
            "services/cvl/cognitive_validation_laboratory_service.py",
        ],
        "coverage": [
            "schemas/cvl/cognitive_validation_laboratory.py",
            "services/cvl/cognitive_validation_laboratory_service.py",
        ],
        "simulation": [
            "schemas/cvl/cognitive_validation_laboratory.py",
            "services/cvl/cognitive_validation_laboratory_service.py",
        ],
        "prediction_accuracy": [
            "schemas/cvl/cognitive_validation_laboratory.py",
            "services/cvl/cognitive_validation_laboratory_service.py",
        ],
        "simulation_accuracy": [
            "schemas/cvl/cognitive_validation_laboratory.py",
            "services/cvl/cognitive_validation_laboratory_service.py",
        ],
        "dispatcher": [
            "services/runtime/runtime_state_hygiene_service.py",
            "services/runtime/task_queue_service.py",
        ],
        "timeline": [
            "schemas/runtime/runtime_timeline.py",
            "services/runtime/runtime_timeline_service.py",
        ],
    }

    def __init__(self, *, artifact_runtime: ArtifactRuntimeService | None = None) -> None:
        self.artifact_runtime = artifact_runtime or ArtifactRuntimeService()

    def diagnose(
        self,
        *,
        expected: ExpectedRuntimeContract,
        runtime: Any,
        create_artifacts: bool = True,
    ) -> RuntimeDoctorReport:
        actual = self._actual_runtime(runtime)
        findings: list[RegressionFinding] = []
        matrix_values = {domain: "NOT_APPLICABLE" for domain in self.DOMAINS}

        self._compare_expected_dict(
            findings,
            matrix_values,
            domain="intent",
            regression_type="INTENT_REGRESSION",
            expected=expected.expected_intent,
            actual=actual["intent"],
            severity="high",
        )
        self._compare_semantic_ingress(findings, matrix_values, actual)
        if expected.expected_intent.get("requires_task") is True and actual["intent"].get("requires_task") is not True:
            self._add_finding(
                findings,
                matrix_values,
                domain="lifecycle",
                regression_type="TASK_LIFECYCLE_REGRESSION",
                severity="critical",
                expected=True,
                actual=actual["intent"].get("requires_task"),
                evidence_refs=["expected_intent.requires_task", "actual_intent.requires_task"],
            )
        self._compare_expected_dict(
            findings,
            matrix_values,
            domain="lifecycle",
            regression_type="LIFECYCLE_REGRESSION",
            expected=expected.expected_lifecycle,
            actual=actual["lifecycle"],
            severity="high",
        )
        operation_expected = dict(expected.expected_operation)
        if expected.expected_runtime_profile:
            operation_expected["runtime_profile"] = expected.expected_runtime_profile
        self._compare_expected_dict(
            findings,
            matrix_values,
            domain="lifecycle",
            regression_type="OPERATION_CONTRACT_REGRESSION",
            expected=operation_expected,
            actual=actual["operation"],
            severity="high",
        )
        self._compare_expected_roots(findings, matrix_values, expected, actual)
        self._compare_expected_artifacts(findings, matrix_values, expected, actual)
        self._compare_expected_dict(
            findings,
            matrix_values,
            domain="approval",
            regression_type="APPROVAL_CONTRACT_REGRESSION",
            expected=expected.expected_approval,
            actual=actual["approval"],
            severity="medium",
        )
        self._compare_validation(findings, matrix_values, expected, actual)
        self._compare_completion(findings, matrix_values, expected, actual)
        self._compare_speaker_truth(findings, matrix_values, expected, actual)
        self._compare_inference(findings, matrix_values, actual)
        self._compare_patch_planning(findings, matrix_values, actual)
        self._compare_expected_dict(
            findings,
            matrix_values,
            domain="dispatcher",
            regression_type="DISPATCHER_REGRESSION",
            expected=expected.expected_dispatcher_state,
            actual=actual["dispatcher"],
            severity="medium",
        )
        self._compare_timeline(findings, matrix_values, expected, actual)

        matrix = RegressionMatrix(**matrix_values)
        status = "FAIL" if findings else "PASS"
        report = RuntimeDoctorReport(
            status=status,
            expected_contract=expected,
            matrix=matrix,
            findings=findings,
            raw_runtime_summary=actual,
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        if create_artifacts:
            refs = self._create_artifacts(report)
            report = report.model_copy(update={"artifact_refs": refs})
        return report

    def _actual_runtime(self, runtime: Any) -> dict[str, Any]:
        data = _dump_model(runtime)
        intent = self._merge_dicts(
            data.get("intent"),
            data.get("intent_map"),
            data.get("intent_decision"),
            {
                key: data.get(key)
                for key in ("intent_type", "requires_task", "requires_workspace")
                if key in data
            },
        )
        operation = self._merge_dicts(
            data.get("operation"),
            data.get("operation_contract"),
            {
                key: data.get(key)
                for key in ("operation_type", "contract_type", "runtime_profile")
                if key in data
            },
        )
        lifecycle = self._merge_dicts(
            data.get("lifecycle"),
            data.get("governance_lifecycle"),
            data.get("canonical_operation_state"),
            data.get("state"),
        )
        workspace_context = self._merge_dicts(data.get("workspace_context"), data.get("workspace"))
        artifacts = self._artifact_tokens(data)
        validation = self._merge_dicts(data.get("validation"), data.get("validation_state"))
        completion = self._merge_dicts(data.get("completion"), data.get("completion_state"))
        speaker_truth = self._merge_dicts(data.get("speaker_truth"), data.get("truth"), data.get("runtime_truth"))
        patch_planning = self._patch_planning_state(data)
        inference = self._inference_state(data)
        semantic_ingress = self._semantic_ingress_state(data, lifecycle)
        dispatcher = self._merge_dicts(data.get("dispatcher"), data.get("queue_health"), data.get("dispatcher_state"))
        timeline = _dump_model(data.get("timeline") or {})
        if timeline:
            validation = self._merge_dicts(validation, timeline.get("validation"))
            completion = self._merge_dicts(completion, timeline.get("completion"))
        return {
            "intent": intent,
            "operation": operation,
            "lifecycle": lifecycle,
            "workspace_roots": self._workspace_roots(data, workspace_context),
            "artifacts": sorted(artifacts),
            "approval": self._merge_dicts(data.get("approval"), data.get("approval_state")),
            "validation": validation,
            "completion": completion,
            "speaker_truth": speaker_truth,
            "inference": inference,
            "semantic_ingress": semantic_ingress,
            "patch_planning": patch_planning,
            "dispatcher": dispatcher,
            "timeline_events": self._timeline_events(data, timeline),
            "timeline": timeline,
            "task_id": data.get("task_id") or data.get("task", {}).get("task_id") if isinstance(data.get("task"), dict) else data.get("task_id"),
            "task_run_id": data.get("task_run_id") or data.get("run_id"),
            "operation_id": data.get("operation_id") or operation.get("operation_id"),
        }

    def _semantic_ingress_state(self, data: dict[str, Any], lifecycle: dict[str, Any]) -> dict[str, Any]:
        candidates = (
            data.get("semantic_ingress_doctor"),
            data.get("semantic_ingress"),
            lifecycle.get("semantic_ingress_doctor") if isinstance(lifecycle, dict) else None,
        )
        for candidate in candidates:
            if isinstance(candidate, dict):
                return candidate
        return {}

    def _compare_expected_dict(
        self,
        findings: list[RegressionFinding],
        matrix_values: dict[str, str],
        *,
        domain: str,
        regression_type: str,
        expected: dict[str, Any],
        actual: dict[str, Any],
        severity: str,
    ) -> None:
        if not expected:
            return
        matrix_values[domain] = "PASS"
        for key, expected_value in expected.items():
            if expected_value is None:
                continue
            actual_value = actual.get(key)
            if self._normalize_value(actual_value) != self._normalize_value(expected_value):
                self._add_finding(
                    findings,
                    matrix_values,
                    domain=domain,
                    regression_type=regression_type,
                    severity=severity,
                    expected={key: expected_value},
                    actual={key: actual_value},
                    evidence_refs=[f"expected.{domain}.{key}", f"actual.{domain}.{key}"],
                )

    def _compare_expected_roots(
        self,
        findings: list[RegressionFinding],
        matrix_values: dict[str, str],
        expected: ExpectedRuntimeContract,
        actual: dict[str, Any],
    ) -> None:
        if not expected.expected_workspace_roots:
            return
        matrix_values["workspace_binding"] = "PASS"
        expected_roots = {self._normalize_path(item) for item in expected.expected_workspace_roots}
        actual_roots = {self._normalize_path(item) for item in actual["workspace_roots"]}
        missing = sorted(expected_roots - actual_roots)
        if missing:
            self._add_finding(
                findings,
                matrix_values,
                domain="workspace_binding",
                regression_type="WORKSPACE_BINDING_REGRESSION",
                severity="critical",
                expected=sorted(expected_roots),
                actual=sorted(actual_roots),
                evidence_refs=["expected_workspace_roots", "actual_workspace_roots"],
            )

    def _compare_expected_artifacts(
        self,
        findings: list[RegressionFinding],
        matrix_values: dict[str, str],
        expected: ExpectedRuntimeContract,
        actual: dict[str, Any],
    ) -> None:
        if not expected.expected_artifacts:
            return
        matrix_values["artifact_contract"] = "PASS"
        expected_artifacts = {self._normalize_token(item) for item in expected.expected_artifacts}
        actual_artifacts = {self._normalize_token(item) for item in actual["artifacts"]}
        missing = sorted(expected_artifacts - actual_artifacts)
        if missing:
            self._add_finding(
                findings,
                matrix_values,
                domain="artifact_contract",
                regression_type="ARTIFACT_CONTRACT_REGRESSION",
                severity="critical",
                expected=sorted(expected_artifacts),
                actual=sorted(actual_artifacts),
                evidence_refs=["expected_artifacts", "actual_artifacts"],
            )

    def _compare_semantic_ingress(
        self,
        findings: list[RegressionFinding],
        matrix_values: dict[str, str],
        actual: dict[str, Any],
    ) -> None:
        ingress = actual.get("semantic_ingress") if isinstance(actual.get("semantic_ingress"), dict) else {}
        if not ingress:
            return
        for domain in (
            "text_ingress",
            "encoding",
            "semantic_normalization",
            "semantic_propositions",
            "state_effects",
            "intent_candidates",
            "intent_arbitration",
            "operation_contract_selection",
        ):
            matrix_values[domain] = "PASS"
        normalization = ingress.get("prompt_normalization") if isinstance(ingress.get("prompt_normalization"), dict) else {}
        if not normalization.get("original_text"):
            self._add_finding(
                findings,
                matrix_values,
                domain="text_ingress",
                regression_type="PROMPT_MISSING",
                severity="high",
                expected={"prompt": "present"},
                actual=normalization,
                evidence_refs=["actual.semantic_ingress.prompt_normalization.original_text"],
            )
        for issue in self._listify(normalization.get("encoding_issues")):
            self._add_finding(
                findings,
                matrix_values,
                domain="encoding",
                regression_type=f"ENCODING_{str(issue).upper()}",
                severity="high" if str(issue) == "mojibake_suspected" else "medium",
                expected={"encoding": "clean_unicode_text"},
                actual=normalization,
                evidence_refs=["actual.semantic_ingress.prompt_normalization.encoding_issues"],
            )
        if not self._listify(ingress.get("semantic_propositions")):
            self._add_finding(
                findings,
                matrix_values,
                domain="semantic_propositions",
                regression_type="SEMANTIC_PROPOSITIONS_MISSING",
                severity="high",
                expected={"semantic_propositions": "extracted"},
                actual=ingress,
                evidence_refs=["actual.semantic_ingress.semantic_propositions"],
            )
        if not self._listify(ingress.get("state_effects")):
            self._add_finding(
                findings,
                matrix_values,
                domain="state_effects",
                regression_type="STATE_EFFECTS_MISSING",
                severity="high",
                expected={"state_effects": "resolved"},
                actual=ingress,
                evidence_refs=["actual.semantic_ingress.state_effects"],
            )
        intent_decision = ingress.get("intent_decision") if isinstance(ingress.get("intent_decision"), dict) else {}
        operation_decision = ingress.get("operation_contract_decision") if isinstance(ingress.get("operation_contract_decision"), dict) else {}
        if not self._listify(intent_decision.get("candidates")):
            self._add_finding(
                findings,
                matrix_values,
                domain="intent_candidates",
                regression_type="INTENT_CANDIDATES_MISSING",
                severity="high",
                expected={"intent_candidates": "considered"},
                actual=intent_decision,
                evidence_refs=["actual.semantic_ingress.intent_decision.candidates"],
            )
        for reason in [str(item) for item in self._listify(ingress.get("reason_codes")) if item]:
            domain = self._semantic_ingress_reason_domain(reason)
            self._add_finding(
                findings,
                matrix_values,
                domain=domain,
                regression_type=reason,
                severity="high" if reason in {"OPERATION_CONTRACT_STATE_EFFECT_MISMATCH", "READONLY_CONTRACT_PROMOTED_TO_MUTATION"} else "medium",
                expected={"semantic_ingress": "explainable_and_aligned"},
                actual=ingress,
                evidence_refs=[f"actual.semantic_ingress.{domain}"],
            )
        if operation_decision and operation_decision.get("relation_to_state_effects") == "conflict":
            self._add_finding(
                findings,
                matrix_values,
                domain="operation_contract_selection",
                regression_type="OPERATION_CONTRACT_STATE_EFFECT_MISMATCH",
                severity="high",
                expected={"operation_contract": "aligned_with_state_effect"},
                actual=operation_decision,
                evidence_refs=["actual.semantic_ingress.operation_contract_decision.relation_to_state_effects"],
            )

    def _semantic_ingress_reason_domain(self, reason: str) -> str:
        if reason.startswith("ENCODING_"):
            return "encoding"
        if reason.startswith("STATE_EFFECT_"):
            return "state_effects"
        if reason.startswith("INTENT_"):
            return "intent_arbitration"
        if reason.startswith("OPERATION_CONTRACT_") or reason.startswith("READONLY_CONTRACT_"):
            return "operation_contract_selection"
        if reason.startswith("PROMPT_"):
            return "text_ingress"
        return "semantic_normalization"

    def _compare_validation(
        self,
        findings: list[RegressionFinding],
        matrix_values: dict[str, str],
        expected: ExpectedRuntimeContract,
        actual: dict[str, Any],
    ) -> None:
        self._compare_expected_dict(
            findings,
            matrix_values,
            domain="validation",
            regression_type="VALIDATION_CONTRACT_REGRESSION",
            expected=expected.expected_validation,
            actual=actual["validation"],
            severity="high",
        )
        validation_status = self._status_token(actual["validation"].get("status") or actual["validation"].get("validation_status"))
        missing_outputs = self._listify(actual["validation"].get("missing_outputs") or actual["completion"].get("missing_outputs"))
        if validation_status in {"pass", "passed", "validated", "ok"} and missing_outputs:
            self._add_finding(
                findings,
                matrix_values,
                domain="validation",
                regression_type="VALIDATION_CONTRACT_REGRESSION",
                severity="critical",
                expected={"missing_outputs": []},
                actual={"status": validation_status, "missing_outputs": missing_outputs},
                evidence_refs=["actual.validation.status", "actual.completion.missing_outputs"],
            )
        incomplete_semantics = self._artifact_semantic_states(actual)
        self._compare_artifact_semantic_subdomains(findings, matrix_values, incomplete_semantics)
        if validation_status in {"pass", "passed", "validated", "ok"} and incomplete_semantics:
            self._add_finding(
                findings,
                matrix_values,
                domain="artifact_contract",
                regression_type="ARTIFACT_SEMANTIC_VALIDATION_INCOMPLETE",
                severity="critical",
                expected={"artifact_semantic_profiles": "passed"},
                actual={"incomplete_artifact_semantics": incomplete_semantics},
                evidence_refs=["actual.validation.artifact_semantic_validations", "actual.completion.metadata.artifact_semantic_profiles"],
            )

    def _compare_completion(
        self,
        findings: list[RegressionFinding],
        matrix_values: dict[str, str],
        expected: ExpectedRuntimeContract,
        actual: dict[str, Any],
    ) -> None:
        self._compare_expected_dict(
            findings,
            matrix_values,
            domain="completion",
            regression_type="COMPLETION_REGRESSION",
            expected=expected.expected_completion,
            actual=actual["completion"],
            severity="high",
        )
        completion_status = self._status_token(actual["completion"].get("status"))
        incomplete_semantics = self._artifact_semantic_states(actual)
        if completion_status in {"ready", "completed", "complete", "pass", "passed"} and incomplete_semantics:
            self._add_finding(
                findings,
                matrix_values,
                domain="completion",
                regression_type="COMPLETION_ARTIFACT_SEMANTIC_DIVERGENCE",
                severity="critical",
                expected={"completion": "blocked_until_artifact_semantics_pass"},
                actual={"status": completion_status, "incomplete_artifact_semantics": incomplete_semantics},
                evidence_refs=["actual.completion.status", "actual.completion.metadata.artifact_semantic_profiles"],
            )

    def _compare_artifact_semantic_subdomains(
        self,
        findings: list[RegressionFinding],
        matrix_values: dict[str, str],
        incomplete_semantics: list[dict[str, Any]],
    ) -> None:
        gap_types = sorted(self._artifact_semantic_gap_types(incomplete_semantics))
        reason_codes = sorted(self._artifact_semantic_reason_codes(incomplete_semantics))
        if not gap_types and not reason_codes:
            return
        entity_gaps = [item for item in gap_types if item.startswith("ENTITY_")]
        attribute_gaps = [item for item in gap_types if item.startswith("ATTRIBUTE_NOT_OBSERVED")]
        schema_gaps = [item for item in gap_types if "schema" in item.casefold()]
        if entity_gaps:
            self._add_finding(
                findings,
                matrix_values,
                domain="entity_compilation",
                regression_type="ENTITY_COMPILATION_GAP",
                severity="high",
                expected={"entity_compilation": "entities_available_for_declared_contract"},
                actual={"semantic_gaps": entity_gaps},
                evidence_refs=["actual.validation.artifact_semantic_profiles.semantic_gaps"],
            )
        if attribute_gaps:
            self._add_finding(
                findings,
                matrix_values,
                domain="schema_coverage",
                regression_type="ARTIFACT_SCHEMA_COVERAGE_GAP",
                severity="high",
                expected={"schema_coverage": "declared_fields_supported_by_entity_attributes"},
                actual={"semantic_gaps": attribute_gaps},
                evidence_refs=["actual.validation.artifact_semantic_profiles.schema_coverage"],
            )
        for reason in reason_codes:
            domain = self._perception_reason_domain(reason)
            self._add_finding(
                findings,
                matrix_values,
                domain=domain,
                regression_type=reason,
                severity="high" if reason in {"OBSERVER_CAPABILITY_MISSING", "NO_MATCHING_CAPABILITY", "ENTITY_SELECTION_EMPTY"} else "medium",
                expected={"contract_driven_perception": "observable_contract_attributes"},
                actual={"reason_code": reason, "semantic_gaps": gap_types},
                evidence_refs=[f"actual.validation.artifact_semantic_profiles.perception.{domain}"],
            )
        if schema_gaps:
            self._add_finding(
                findings,
                matrix_values,
                domain="artifact_renderer",
                regression_type="ARTIFACT_RENDERER_SCHEMA_GAP",
                severity="high",
                expected={"renderer": "contract_aware_artifact_schema"},
                actual={"semantic_gaps": schema_gaps},
                evidence_refs=["actual.validation.artifact_semantic_profiles.observed_schema"],
            )

    def _artifact_semantic_gap_types(self, states: list[dict[str, Any]]) -> set[str]:
        gap_types: set[str] = set()
        for row in states:
            profile = row.get("profile") if isinstance(row.get("profile"), dict) else row
            if not isinstance(profile, dict):
                continue
            for key in ("semantic_gaps", "contract_gaps", "consistency_gaps"):
                gaps = profile.get(key)
                if not isinstance(gaps, list):
                    continue
                for gap in gaps:
                    if isinstance(gap, dict) and gap.get("gap_type"):
                        gap_types.add(str(gap.get("gap_type")))
        return gap_types

    def _artifact_semantic_reason_codes(self, states: list[dict[str, Any]]) -> set[str]:
        reason_codes: set[str] = set()
        for row in states:
            profile = row.get("profile") if isinstance(row.get("profile"), dict) else row
            if not isinstance(profile, dict):
                continue
            self._collect_semantic_reason_codes(profile, reason_codes)
            declared_contract = profile.get("declared_contract") if isinstance(profile.get("declared_contract"), dict) else {}
            if declared_contract:
                self._collect_semantic_reason_codes(declared_contract, reason_codes)
                perception = declared_contract.get("perception") if isinstance(declared_contract.get("perception"), dict) else {}
                if perception:
                    self._collect_semantic_reason_codes(perception, reason_codes)
            for key in ("semantic_gaps", "contract_gaps", "consistency_gaps"):
                gaps = profile.get(key)
                if not isinstance(gaps, list):
                    continue
                for gap in gaps:
                    if isinstance(gap, dict) and gap.get("reason_code"):
                        reason_codes.add(str(gap.get("reason_code")))
        return reason_codes

    def _collect_semantic_reason_codes(self, source: dict[str, Any], reason_codes: set[str]) -> None:
        self_review = source.get("semantic_self_review") if isinstance(source.get("semantic_self_review"), dict) else {}
        for reason in self_review.get("reason_codes") or []:
            if reason:
                reason_codes.add(str(reason))
        for finding in self_review.get("findings") or []:
            if isinstance(finding, dict) and finding.get("reason_code"):
                reason_codes.add(str(finding.get("reason_code")))
        coverage2 = source.get("semantic_coverage_2") if isinstance(source.get("semantic_coverage_2"), dict) else {}
        for reason in coverage2.get("blocking_reasons") or []:
            if reason:
                reason_codes.add(str(reason))

    def _perception_reason_domain(self, reason: str) -> str:
        if reason in {
            "NO_ENTITY_OVERLAPS_CONTRACT_ATTRIBUTES",
            "ENTITY_SELECTION_EMPTY",
            "ENTITY_AMBIGUOUS",
            "ENTITY_SELECTION_POLICY_NOT_APPLIED",
            "ROOT_ROLE_METADATA_MISSING",
            "ENTITY_SELECTED_FROM_UNCLASSIFIED_ROOT",
            "WORKSPACE_ROLE_MISMATCH",
        }:
            return "entity_selection"
        if reason in {"OBSERVER_CAPABILITY_MISSING"}:
            return "observer_capability"
        if reason in {"NO_MATCHING_CAPABILITY"}:
            return "capability_matching"
        if reason in {"CAPABILITY_REJECTED", "MULTIPLE_CAPABILITIES_AVAILABLE", "LOW_CONFIDENCE"}:
            return "capability_arbitration"
        if reason in {
            "OBSERVER_EXECUTION_NOT_RUN",
            "EXECUTION_FAILED",
            "OBSERVER_NOT_BOUND",
            "OBSERVER_INPUT_SCHEMA_INVALID",
            "OBSERVER_OUTPUT_SCHEMA_INVALID",
            "OBSERVER_TIMEOUT",
            "OBSERVER_RUNTIME_ERROR",
            "OBSERVER_POLICY_BLOCKED",
            "OBSERVER_PRODUCED_NO_EVIDENCE",
            "OBSERVER_CONFIDENCE_TOO_LOW",
            "MEDIA_BACKEND_NOT_AVAILABLE",
            "MEDIA_BACKEND_UNSUPPORTED_FORMAT",
            "MEDIA_BACKEND_NO_EVIDENCE",
            "MEDIA_BACKEND_PARTIAL_EVIDENCE",
            "MEDIA_BACKEND_CONTRADICTION",
            "MEDIA_BACKEND_LOW_CONFIDENCE",
            "MEDIA_BACKEND_RUNTIME_ERROR",
            "FFPROBE_NOT_AVAILABLE",
            "FFPROBE_TIMEOUT",
            "FFPROBE_INVALID_JSON",
            "FFPROBE_RUNTIME_ERROR",
        }:
            return "observer_execution"
        if reason in {"EVIDENCE_MISSING", "OBSERVER_PRODUCED_NO_EVIDENCE"}:
            return "evidence_recording"
        if reason in {"KNOWLEDGE_MISSING", "PREDICTED_KNOWLEDGE_AVAILABILITY_GAP"}:
            return "knowledge_representation"
        if reason in {"EVIDENCE_CONFLICT", "UNSUPPORTED_ASSERTION_PROMOTED"}:
            return "semantic_assertions"
        if reason in {"TRACEABILITY_MISSING", "CONFIDENCE_OR_EVIDENCE_INSUFFICIENT"}:
            return "semantic_self_review"
        if reason in {"TRUTH_NOT_READY", "PREDICTED_TRUTH_READINESS_GAP"}:
            return "truth_readiness"
        if reason in {"ATTRIBUTE_VALUE_NOT_OBSERVED", "ATTRIBUTE_CONFIDENCE_INSUFFICIENT"}:
            return "attribute_observation"
        if reason.startswith("OBSERVATION_GOAL_"):
            return "observation_goal"
        if reason.startswith("OBSERVATION_STRATEGY_"):
            return "observation_strategy"
        if reason.startswith("CAPABILITY_REGISTRY_"):
            return "capability_registry"
        if reason.startswith("OBSERVATION_PLAN_"):
            return "observation_planning"
        if reason.startswith("COVERAGE_"):
            return "coverage_analysis"
        return "contract_observation"

    def _compare_speaker_truth(
        self,
        findings: list[RegressionFinding],
        matrix_values: dict[str, str],
        expected: ExpectedRuntimeContract,
        actual: dict[str, Any],
    ) -> None:
        self._compare_expected_dict(
            findings,
            matrix_values,
            domain="speaker_truth",
            regression_type="SPEAKER_TRUTH_REGRESSION",
            expected=expected.expected_speaker_truth,
            actual=actual["speaker_truth"],
            severity="high",
        )
        completion_status = self._status_token(actual["completion"].get("status"))
        truth_status = self._status_token(actual["speaker_truth"].get("status") or actual["speaker_truth"].get("speaker_truth_status"))
        if completion_status in {"ready", "completed", "complete", "pass", "passed"} and truth_status in {"blocked", "failed", "fail"}:
            self._add_finding(
                findings,
                matrix_values,
                domain="speaker_truth",
                regression_type="TRUTH_CONSISTENCY_REGRESSION",
                severity="critical",
                expected={"speaker_truth": "compatible_with_completion"},
                actual={"completion": completion_status, "speaker_truth": truth_status},
                evidence_refs=["actual.completion.status", "actual.speaker_truth.status"],
            )

    def _artifact_semantic_states(self, actual: dict[str, Any]) -> list[dict[str, Any]]:
        states: list[dict[str, Any]] = []
        for source in (
            actual.get("validation"),
            actual.get("completion"),
            (actual.get("completion") or {}).get("metadata") if isinstance(actual.get("completion"), dict) else {},
        ):
            if not isinstance(source, dict):
                continue
            for key in ("artifact_semantic_validations", "artifact_semantic_profiles"):
                rows = source.get(key)
                if not isinstance(rows, list):
                    continue
                for row in rows:
                    if not isinstance(row, dict):
                        continue
                    profile = row.get("profile") if isinstance(row.get("profile"), dict) else row
                    status_values = {
                        str(row.get("status") or ""),
                        str(profile.get("semantic_status") or ""),
                        str(profile.get("material_status") or ""),
                        str(profile.get("contract_status") or ""),
                        str(profile.get("consistency_status") or ""),
                    }
                    if status_values & {"blocked", "partial", "not_applicable"}:
                        states.append(row)
        return states

    def _compare_patch_planning(
        self,
        findings: list[RegressionFinding],
        matrix_values: dict[str, str],
        actual: dict[str, Any],
    ) -> None:
        patch_planning = actual.get("patch_planning") if isinstance(actual.get("patch_planning"), dict) else {}
        blocked_reasons = {
            str(item)
            for item in self._listify(patch_planning.get("blocked_reasons"))
            if item
        }
        canonical_reasons = {
            "PATCH_CANDIDATE_INSUFFICIENT",
            "PATCH_SYMBOL_NOT_FOUND",
            "PATCH_CONTEXT_TOO_SMALL",
            "PATCH_MODEL_EMPTY_OUTPUT",
            "PATCH_REPLACEMENT_INVALID",
            "PATCH_COMPILER_FAILED",
            "REPAIR_TASK_NOT_ACTIONABLE",
            "REPAIR_TASK_TARGET_TOO_BROAD",
            "REPAIR_TASK_SYMBOL_UNRESOLVED",
            "REPAIR_TASK_SNIPPET_MISSING",
            "REPAIR_TASK_SNIPPET_INSUFFICIENT",
            "REPAIR_TASK_OBJECTIVE_MISSING",
            "REPAIR_TASK_OBSERVED_BEHAVIOR_MISSING",
            "REPAIR_TASK_EXPECTED_BEHAVIOR_MISSING",
            "REPAIR_TASK_EVIDENCE_MISSING",
            "REPAIR_TASK_STRATEGY_MISSING",
            "REPAIR_INTENT_MISSING",
            "REPAIR_BOUNDARY_MISSING",
            "SUCCESS_CONDITION_MISSING",
            "TARGET_SPECIFIC_EXPECTED_BEHAVIOR_MISSING",
            "SEMANTIC_EVIDENCE_MISSING",
            "BEHAVIOR_LOCALIZATION_MISSING",
            "BEHAVIOR_JUSTIFICATION_MISSING",
            "TRANSFORMATION_MISSING",
            "PROPOSAL_ASSEMBLY_FAILED",
            "INSUFFICIENT_PATCH_EVIDENCE",
            "PATCH_CANDIDATE_WITHOUT_DIAGNOSIS",
            "PATCH_PLAN_WITHOUT_PATCH_CANDIDATE",
            "DIAGNOSIS_OUTSIDE_CANONICAL_FLOW",
            "MULTIPLE_DIAGNOSIS_AUTHORITIES",
        }
        observed = sorted(blocked_reasons & canonical_reasons)
        if not patch_planning and not observed:
            return
        matrix_values["patch_planning"] = "PASS"
        if observed:
            matrix_values["patch_planning"] = "FAIL"
        diagnoses = self._listify(patch_planning.get("diagnosis_artifacts") or patch_planning.get("diagnoses"))
        candidates = self._listify(patch_planning.get("patch_candidates") or patch_planning.get("candidates"))
        has_plan = bool(patch_planning.get("plan_id") or patch_planning.get("canonical_patch_plan_id") or patch_planning.get("diff_proposal"))
        if candidates and not diagnoses:
            self._add_finding(
                findings,
                matrix_values,
                domain="patch_planning",
                regression_type="PATCH_CANDIDATE_WITHOUT_DIAGNOSIS",
                severity="critical",
                expected={"patch_candidate": "derived_from_canonical_diagnosis"},
                actual=patch_planning,
                evidence_refs=["actual.patch_planning.patch_candidates", "actual.patch_planning.diagnosis_artifacts"],
            )
        for candidate in candidates:
            if isinstance(candidate, dict) and not candidate.get("diagnosis_id"):
                self._add_finding(
                    findings,
                    matrix_values,
                    domain="patch_planning",
                    regression_type="PATCH_CANDIDATE_WITHOUT_DIAGNOSIS",
                    severity="critical",
                    expected={"patch_candidate.diagnosis_id": "present"},
                    actual=candidate,
                    evidence_refs=["actual.patch_planning.patch_candidates[].diagnosis_id"],
                )
        if has_plan and not candidates:
            self._add_finding(
                findings,
                matrix_values,
                domain="patch_planning",
                regression_type="PATCH_PLAN_WITHOUT_PATCH_CANDIDATE",
                severity="critical",
                expected={"patch_plan": "bound_to_patch_candidate"},
                actual=patch_planning,
                evidence_refs=["actual.patch_planning.plan_id", "actual.patch_planning.patch_candidates"],
            )
        legacy_diagnosis = patch_planning.get("diagnosis") or patch_planning.get("technical_diagnosis")
        if legacy_diagnosis and diagnoses:
            self._add_finding(
                findings,
                matrix_values,
                domain="patch_planning",
                regression_type="MULTIPLE_DIAGNOSIS_AUTHORITIES",
                severity="high",
                expected={"diagnosis_authority": "diagnosis_artifacts"},
                actual={"legacy_diagnosis_present": True, "diagnosis_artifacts": diagnoses},
                evidence_refs=["actual.patch_planning.diagnosis", "actual.patch_planning.diagnosis_artifacts"],
            )
        for reason in observed:
            domain = self._quality_domain(reason)
            if domain == "completeness":
                domain = "patch_planning"
            self._add_finding(
                findings,
                matrix_values,
                domain=domain,
                regression_type=reason,
                severity="high" if reason in {"PATCH_COMPILER_FAILED", "PATCH_REPLACEMENT_INVALID"} else "medium",
                expected={"patch_planning": "concrete_candidate_and_replacement"},
                actual=patch_planning,
                evidence_refs=["actual.patch_planning.blocked_reasons"],
            )
        quality_gate = patch_planning.get("quality_gate") if isinstance(patch_planning.get("quality_gate"), dict) else {}
        quality_reasons = [str(item) for item in self._listify(quality_gate.get("reason_codes")) if item]
        for reason in quality_reasons:
            domain = self._quality_domain(reason)
            self._add_finding(
                findings,
                matrix_values,
                domain=domain,
                regression_type=reason,
                severity="medium",
                expected={"quality": "sufficient_for_patch_planning"},
                actual=quality_gate,
                evidence_refs=[f"actual.patch_planning.quality_gate.{domain}"],
            )

    def _compare_inference(
        self,
        findings: list[RegressionFinding],
        matrix_values: dict[str, str],
        actual: dict[str, Any],
    ) -> None:
        inference = actual.get("inference") if isinstance(actual.get("inference"), dict) else {}
        if not inference:
            return
        matrix_values["inference"] = "PASS"
        runtime = inference.get("inference_runtime") if isinstance(inference.get("inference_runtime"), dict) else inference
        fingerprint = runtime.get("fingerprint") if isinstance(runtime.get("fingerprint"), dict) else {}
        real_inference = bool(inference.get("real_inference") or runtime.get("real_inference"))
        if real_inference and not runtime:
            self._add_finding(
                findings,
                matrix_values,
                domain="inference",
                regression_type="INFERENCE_RUNTIME_MISSING",
                severity="critical",
                expected={"inference_runtime": "present_for_real_inference"},
                actual=inference,
                evidence_refs=["actual.inference"],
            )
        required_fingerprint_fields = ["executable_path", "executable_sha256", "model_path", "cwd", "path_sha256", "env_sha256"]
        if real_inference:
            missing = [field for field in required_fingerprint_fields if not fingerprint.get(field)]
            if missing:
                self._add_finding(
                    findings,
                    matrix_values,
                    domain="inference",
                    regression_type="INFERENCE_FINGERPRINT_INCOMPLETE",
                    severity="high",
                    expected={"fingerprint_fields": required_fingerprint_fields},
                    actual={"missing": missing, "fingerprint": fingerprint},
                    evidence_refs=["actual.inference.inference_runtime.fingerprint"],
                )
            if not runtime.get("parser"):
                self._add_finding(
                    findings,
                    matrix_values,
                    domain="inference",
                    regression_type="INFERENCE_PARSER_UNRECORDED",
                    severity="medium",
                    expected={"parser": "recorded"},
                    actual=runtime,
                    evidence_refs=["actual.inference.inference_runtime.parser"],
                )
        if inference.get("direct_provider_invocation") is True:
            self._add_finding(
                findings,
                matrix_values,
                domain="inference",
                regression_type="DIRECT_MODEL_PROVIDER_INVOCATION",
                severity="critical",
                expected={"llm_call": "InferenceRuntime"},
                actual=inference,
                evidence_refs=["actual.inference.direct_provider_invocation"],
            )
        input_doctor = inference.get("inference_input_doctor") if isinstance(inference.get("inference_input_doctor"), dict) else {}
        if input_doctor:
            for reason in [str(item) for item in self._listify(input_doctor.get("reason_codes")) if item]:
                domain = self._inference_reason_domain(reason)
                self._add_finding(
                    findings,
                    matrix_values,
                    domain=domain,
                    regression_type=reason,
                    severity="medium" if reason != "INFERENCE_INPUT_INCOMPLETE" else "high",
                    expected={"inference_input": "complete_and_explainable"},
                    actual=input_doctor,
                    evidence_refs=[f"actual.inference.inference_input_doctor.{domain}"],
                )
        output_artifact = inference.get("canonical_inference_output_artifact") if isinstance(inference.get("canonical_inference_output_artifact"), dict) else {}
        if output_artifact and output_artifact.get("empty_output"):
            self._add_finding(
                findings,
                matrix_values,
                domain="inference",
                regression_type="PATCH_MODEL_EMPTY_OUTPUT",
                severity="high",
                expected={"replacement_detected": True},
                actual=output_artifact,
                evidence_refs=["actual.inference.canonical_inference_output_artifact"],
            )

    def _inference_reason_domain(self, reason: str) -> str:
        if reason.startswith("PROMPT_"):
            if reason == "PROMPT_CONTEXT_TRUNCATED":
                return "context_budget"
            return "prompt"
        if reason in {"INFERENCE_INPUT_INCOMPLETE"}:
            return "completeness"
        if reason in {"PATCH_MODEL_EMPTY_OUTPUT", "INFERENCE_EMPTY_OUTPUT"}:
            return "inference"
        return "inference"

    def _quality_domain(self, reason: str) -> str:
        if reason.startswith("DIAGNOSIS_"):
            return "diagnosis"
        if reason.startswith("REPAIR_INTENT_") or reason in {
            "REPAIR_BOUNDARY_MISSING",
            "SUCCESS_CONDITION_MISSING",
            "TARGET_SPECIFIC_EXPECTED_BEHAVIOR_MISSING",
        }:
            return "repair_intent"
        if reason == "SEMANTIC_EVIDENCE_MISSING":
            return "semantic_evidence"
        if reason == "BEHAVIOR_LOCALIZATION_MISSING":
            return "behavior_localization"
        if reason == "BEHAVIOR_JUSTIFICATION_MISSING":
            return "behavior_justification"
        if reason in {"TRANSFORMATION_MISSING", "PROPOSAL_ASSEMBLY_FAILED"}:
            return "candidate_transformation"
        if reason.startswith("PATCH_CANDIDATE_"):
            return "patch_candidate"
        if reason.startswith("REPAIR_TASK_"):
            return "actionability"
        if reason.startswith("PROMPT_"):
            return "prompt"
        return "completeness"

    def _compare_timeline(
        self,
        findings: list[RegressionFinding],
        matrix_values: dict[str, str],
        expected: ExpectedRuntimeContract,
        actual: dict[str, Any],
    ) -> None:
        if not expected.expected_timeline_events:
            return
        matrix_values["timeline"] = "PASS"
        expected_events = {self._normalize_token(item) for item in expected.expected_timeline_events}
        actual_events = {self._normalize_token(item) for item in actual["timeline_events"]}
        missing = sorted(expected_events - actual_events)
        if missing:
            self._add_finding(
                findings,
                matrix_values,
                domain="timeline",
                regression_type="TIMELINE_REGRESSION",
                severity="high",
                expected=sorted(expected_events),
                actual=sorted(actual_events),
                evidence_refs=["expected_timeline_events", "actual_timeline_events"],
            )

    def _add_finding(
        self,
        findings: list[RegressionFinding],
        matrix_values: dict[str, str],
        *,
        domain: str,
        regression_type: str,
        severity: str,
        expected: Any,
        actual: Any,
        evidence_refs: list[str],
    ) -> None:
        matrix_values[domain] = "FAIL"
        findings.append(
            RegressionFinding(
                regression_type=regression_type,
                severity=severity,  # type: ignore[arg-type]
                subsystem=domain,
                expected_value=expected,
                actual_value=actual,
                evidence_refs=list(dict.fromkeys(evidence_refs)),
                suspected_modules=self.SUSPECTED_MODULES.get(domain, []),
                deterministic=True,
                confidence=1.0,
            )
        )

    def _create_artifacts(self, report: RuntimeDoctorReport) -> RuntimeDoctorArtifactRefs:
        task_id, task_run_id, metadata = self._artifact_binding(report)
        evidence_refs = [*report.expected_contract.evidence_refs, f"runtime_doctor_report:{report.report_id}"]
        json_artifact = self.artifact_runtime.create(
            ArtifactRuntimeCreateRequest(
                logical_path="runtime_doctor/runtime_doctor_report.json",
                content=json.dumps(report.model_dump(mode="json"), ensure_ascii=False, indent=2),
                artifact_type="runtime_doctor_report",
                content_type="application/json",
                producer_step="runtime_doctor_diagnose",
                event_id=f"{report.report_id}:json",
                task_id=task_id,
                task_run_id=task_run_id,
                source_agent="aipinho_runtime_doctor",
                validation_status="validated",
                evidence_refs=evidence_refs,
                metadata=metadata,
            )
        )
        markdown_artifact = self.artifact_runtime.create(
            ArtifactRuntimeCreateRequest(
                logical_path="runtime_doctor/runtime_doctor.md",
                content=self._markdown(report),
                artifact_type="runtime_doctor_report",
                content_type="text/markdown",
                producer_step="runtime_doctor_diagnose",
                event_id=f"{report.report_id}:markdown",
                task_id=task_id,
                task_run_id=task_run_id,
                source_agent="aipinho_runtime_doctor",
                validation_status="validated",
                evidence_refs=evidence_refs,
                metadata=metadata,
            )
        )
        csv_artifact = self.artifact_runtime.create(
            ArtifactRuntimeCreateRequest(
                logical_path="runtime_doctor/regression_matrix.csv",
                content=self._matrix_csv(report.matrix),
                artifact_type="regression_matrix",
                content_type="text/csv",
                producer_step="runtime_doctor_diagnose",
                event_id=f"{report.report_id}:matrix_csv",
                task_id=task_id,
                task_run_id=task_run_id,
                source_agent="aipinho_runtime_doctor",
                validation_status="validated",
                evidence_refs=evidence_refs,
                metadata=metadata,
            )
        )
        return RuntimeDoctorArtifactRefs(
            report_json_artifact_id=json_artifact.artifact_id,
            report_markdown_artifact_id=markdown_artifact.artifact_id,
            regression_matrix_csv_artifact_id=csv_artifact.artifact_id,
        )

    def _artifact_binding(self, report: RuntimeDoctorReport) -> tuple[str, str, dict[str, Any]]:
        task_id = report.expected_contract.task_id or f"runtime_doctor_task:{report.report_id}"
        task_run_id = report.expected_contract.task_run_id or f"runtime_doctor_run:{report.report_id}"
        metadata: dict[str, Any] = {
            "binding_source": "expected_contract"
            if report.expected_contract.task_id or report.expected_contract.task_run_id
            else "runtime_doctor_diagnostic_report",
            "runtime_doctor_report_id": report.report_id,
            "expected_contract_id": report.expected_contract.contract_id,
        }
        return task_id, task_run_id, metadata

    def _markdown(self, report: RuntimeDoctorReport) -> str:
        lines = [
            "# Runtime Doctor Report",
            "",
            f"- Report: `{report.report_id}`",
            f"- Status: `{report.status}`",
            f"- Deterministic: `{report.deterministic}`",
            "",
            "## Regression Matrix",
            "",
        ]
        for domain, status in report.matrix.model_dump().items():
            lines.append(f"- `{domain}`: `{status}`")
        lines.extend(["", "## Findings", ""])
        if not report.findings:
            lines.append("Nenhuma regressao contratual detectada.")
        for finding in report.findings:
            lines.extend(
                [
                    f"### {finding.regression_type}",
                    "",
                    f"- Subsystem: `{finding.subsystem}`",
                    f"- Severity: `{finding.severity}`",
                    f"- Deterministic: `{finding.deterministic}`",
                    f"- Evidence: `{', '.join(finding.evidence_refs)}`",
                    "",
                ]
            )
        return "\n".join(lines).strip() + "\n"

    def _matrix_csv(self, matrix: RegressionMatrix) -> str:
        output = io.StringIO()
        writer = csv.writer(output, lineterminator="\n")
        writer.writerow(["domain", "status"])
        for domain, status in matrix.model_dump().items():
            writer.writerow([domain, status])
        return output.getvalue()

    def _artifact_tokens(self, data: dict[str, Any]) -> set[str]:
        tokens: set[str] = set()
        candidates = [
            data.get("artifacts"),
            data.get("produced_artifacts"),
            data.get("artifact_state", {}).get("artifacts") if isinstance(data.get("artifact_state"), dict) else None,
            data.get("artifact_state", {}).get("artifact_ids") if isinstance(data.get("artifact_state"), dict) else None,
        ]
        timeline = data.get("timeline") if isinstance(data.get("timeline"), dict) else {}
        candidates.append(timeline.get("artifacts") if isinstance(timeline, dict) else None)
        for candidate in candidates:
            for item in self._listify(candidate):
                if isinstance(item, dict):
                    for key in ("logical_path", "artifact_id", "storage_ref"):
                        if item.get(key):
                            tokens.add(str(item[key]))
                elif item:
                    tokens.add(str(item))
        return tokens

    def _inference_state(self, data: dict[str, Any]) -> dict[str, Any]:
        candidates: list[Any] = [
            data.get("inference"),
            data.get("inference_runtime"),
            data.get("model_response"),
            data.get("model_run"),
        ]
        metadata = data.get("metadata") if isinstance(data.get("metadata"), dict) else {}
        candidates.append(metadata.get("inference_runtime"))
        outputs = data.get("outputs")
        if isinstance(outputs, dict):
            candidates.extend([outputs.get("inference"), outputs.get("model_response"), outputs.get("model_run")])
            response = outputs.get("response")
            if isinstance(response, dict):
                response_metadata = response.get("metadata") if isinstance(response.get("metadata"), dict) else {}
                candidates.extend([response.get("inference_runtime"), response_metadata.get("inference_runtime")])
        timeline = data.get("timeline") if isinstance(data.get("timeline"), dict) else {}
        candidates.extend(self._find_values_by_key(timeline, "inference_runtime"))
        candidates.extend(self._find_values_by_key(data, "inference_runtime"))
        merged = self._merge_dicts(*candidates)
        for key in (
            "canonical_inference_input_artifact",
            "canonical_inference_output_artifact",
            "inference_input_doctor",
        ):
            values = [value for value in self._find_values_by_key(data, key) if isinstance(value, dict)]
            if values and key not in merged:
                merged[key] = values[-1]
        if any(bool(item) for item in candidates):
            merged.setdefault("observed", True)
        return merged

    def _patch_planning_state(self, data: dict[str, Any]) -> dict[str, Any]:
        candidates: list[Any] = [
            data.get("patch_planning"),
            data.get("patch_plan"),
            data.get("plan"),
        ]
        metadata = data.get("metadata") if isinstance(data.get("metadata"), dict) else {}
        candidates.append(metadata)
        outputs = data.get("outputs")
        if isinstance(outputs, dict):
            candidates.extend([outputs.get("patch_planning"), outputs.get("patch_plan")])
            report = outputs.get("project_analysis_report")
            if isinstance(report, dict):
                candidates.extend([report.get("patch_planning"), report.get("patch_plan")])
        task_run = data.get("task_run")
        if isinstance(task_run, dict):
            candidates.extend([task_run.get("patch_planning"), task_run.get("patch_plan")])
            task_outputs = task_run.get("outputs")
            if isinstance(task_outputs, dict):
                candidates.extend([task_outputs.get("patch_planning"), task_outputs.get("patch_plan")])
                report = task_outputs.get("project_analysis_report")
                if isinstance(report, dict):
                    candidates.extend([report.get("patch_planning"), report.get("patch_plan")])
        merged = self._merge_dicts(*candidates)
        blocked_reasons = list(merged.get("blocked_reasons") or [])
        for reason in self._find_values_by_key(data, "blocked_reasons"):
            blocked_reasons.extend(str(item) for item in self._listify(reason) if item)
        if blocked_reasons:
            merged["blocked_reasons"] = list(dict.fromkeys(str(item) for item in blocked_reasons if item))
        return merged

    def _find_values_by_key(self, value: Any, key: str) -> list[Any]:
        found: list[Any] = []
        if isinstance(value, dict):
            for item_key, item_value in value.items():
                if item_key == key:
                    found.append(item_value)
                found.extend(self._find_values_by_key(item_value, key))
        elif isinstance(value, list):
            for item in value:
                found.extend(self._find_values_by_key(item, key))
        return found

    def _timeline_events(self, data: dict[str, Any], timeline: dict[str, Any]) -> list[str]:
        events: list[str] = []
        for item in self._listify(data.get("timeline_events")):
            events.append(str(item.get("event_type") if isinstance(item, dict) else item))
        for item in self._listify(timeline.get("events")):
            events.append(str(item.get("event_type") if isinstance(item, dict) else item))
        return list(dict.fromkeys(item for item in events if item))

    def _workspace_roots(self, data: dict[str, Any], workspace_context: dict[str, Any]) -> list[str]:
        roots: list[str] = []
        roots.extend(str(item) for item in self._listify(data.get("workspace_roots")) if item)
        for key in ("project_root", "current_workspace", "workspace_path"):
            if workspace_context.get(key):
                roots.append(str(workspace_context[key]))
        for key in ("external_roots", "library_roots", "workspace_ids"):
            roots.extend(str(item) for item in self._listify(workspace_context.get(key)) if item)
        return list(dict.fromkeys(roots))

    def _merge_dicts(self, *values: Any) -> dict[str, Any]:
        merged: dict[str, Any] = {}
        for value in values:
            if value is None:
                continue
            data = _dump_model(value)
            merged.update({key: item for key, item in data.items() if item is not None})
        return merged

    def _listify(self, value: Any) -> list[Any]:
        if value is None:
            return []
        if isinstance(value, list):
            return value
        if isinstance(value, tuple | set):
            return list(value)
        return [value]

    def _normalize_path(self, value: Any) -> str:
        return str(value or "").strip().replace("\\", "/").rstrip("/").casefold()

    def _normalize_token(self, value: Any) -> str:
        return str(value or "").strip().replace("\\", "/").casefold()

    def _normalize_value(self, value: Any) -> Any:
        if isinstance(value, str):
            return self._status_token(value)
        if isinstance(value, list):
            return [self._normalize_value(item) for item in value]
        if isinstance(value, dict):
            return {key: self._normalize_value(item) for key, item in value.items()}
        return value

    def _status_token(self, value: Any) -> str:
        return str(value or "").strip().replace("-", "_").casefold()
