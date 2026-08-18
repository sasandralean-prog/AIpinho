from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from aipinho.core.paths import PATHS
from aipinho.schemas.artifacts.artifact_runtime import ArtifactRuntimeCreateRequest
from aipinho.schemas.chat.chat_request import ChatContext, ChatRequest
from aipinho.schemas.runtime_doctor import (
    RuntimeDoctorAnalysis,
    RuntimeDoctorDiff,
    RuntimeDoctorExpectedContract,
    RuntimeDoctorIteration,
    RuntimeDoctorPatchExecution,
    RuntimeDoctorPatchPlan,
    RuntimeDoctorRawSnapshot,
    RuntimeDoctorRootCause,
    RuntimeDoctorRunResult,
    RuntimeDoctorStatus,
    RuntimeDoctorTestRequest,
    RuntimeDoctorViolation,
)
from aipinho.services.artifacts.artifact_runtime_service import ArtifactRuntimeService
from aipinho.services.governance.lifecycle.canonical_public_chat_service import CanonicalPublicChatService
from aipinho.services.runtime.task_run_store import TaskRunStore
from aipinho.services.runtime.universal_task_session_service import UniversalTaskSessionService
from aipinho.schemas.events.contracts import utc_now_iso


class RuntimeDoctorEndpointClient:
    """Boundary client for the public runtime protocol.

    The implementation uses the same public services behind the API routes so
    tests can run in-process without special-casing any scenario.
    """

    def __init__(
        self,
        *,
        chat: CanonicalPublicChatService | None = None,
        sessions: UniversalTaskSessionService | None = None,
        store: TaskRunStore | None = None,
    ) -> None:
        self.chat = chat or CanonicalPublicChatService()
        self.store = store or TaskRunStore()
        self.sessions = sessions or UniversalTaskSessionService(store=self.store)

    def send_chat(self, request: RuntimeDoctorTestRequest) -> dict[str, Any]:
        response = self.chat.respond(
            ChatRequest(
                message=request.prompt,
                session_id=request.session_id,
                include_trace=True,
                context=ChatContext(surface="api", active_workspace=request.workspace),
            ),
            source_channel=request.source_channel,
        )
        return response.model_dump(mode="json")

    def runtime_raw(self, task_run_id: str | None) -> dict[str, Any]:
        if not task_run_id:
            return {}
        raw: dict[str, Any] = {}
        session = self.sessions.get_session(task_run_id)
        raw["session"] = session.model_dump(mode="json") if session else None
        raw["events"] = self.sessions.events(task_run_id) or {}
        raw["artifacts"] = self.sessions.artifacts_for_run(task_run_id) or {}
        raw["summary"] = self.sessions.summary(task_run_id) or {}
        run = self.store.get_run(task_run_id)
        result = self.store.get_result(task_run_id)
        raw["task_run"] = run.model_dump(mode="json") if run else None
        raw["result"] = result.model_dump(mode="json") if result else None
        raw["trace"] = [item.model_dump(mode="json") for item in self.store.get_trace(task_run_id)]
        return raw


class RuntimeDoctorRawCollector:
    def collect(self, *, iteration_id: str, chat_response: dict[str, Any], runtime_raw: dict[str, Any]) -> RuntimeDoctorRawSnapshot:
        lifecycle = chat_response.get("governance_lifecycle") if isinstance(chat_response.get("governance_lifecycle"), dict) else {}
        session = runtime_raw.get("session") if isinstance(runtime_raw.get("session"), dict) else {}
        metadata = session.get("metadata") if isinstance(session.get("metadata"), dict) else {}
        result_state = session.get("result_state") if isinstance(session.get("result_state"), dict) else {}
        validation_state = session.get("validation_state") if isinstance(session.get("validation_state"), dict) else {}
        artifact_state = session.get("artifact_state") if isinstance(session.get("artifact_state"), dict) else {}
        task_run = runtime_raw.get("task_run") if isinstance(runtime_raw.get("task_run"), dict) else {}
        result = runtime_raw.get("result") if isinstance(runtime_raw.get("result"), dict) else {}
        return RuntimeDoctorRawSnapshot(
            iteration_id=iteration_id,
            chat_response=chat_response,
            lifecycle=lifecycle,
            intent=chat_response.get("intent") or {},
            operation_contract=self._section(lifecycle, "operation_contract", fallback=chat_response.get("contract_preview") or {}),
            execution_plan=self._section(lifecycle, "execution_plan", fallback=(task_run.get("plan") if task_run else {})),
            approval=chat_response.get("policy") or {},
            task={
                "task_id": chat_response.get("task_id") or metadata.get("task_id"),
                "operation_id": chat_response.get("operation_id") or metadata.get("operation_id"),
                "session_id": chat_response.get("session_id") or metadata.get("session_id"),
            },
            task_run=task_run or {"task_run_id": chat_response.get("task_id")},
            artifacts=artifact_state or runtime_raw.get("artifacts") or {},
            validation=validation_state or self._section(lifecycle, "validation", fallback=result.get("validation") or {}),
            completion=self._completion(lifecycle, result_state, result),
            speaker_truth=self._section(lifecycle, "speaker_truth", fallback=metadata.get("runtime_truth") or {}),
            warnings=list(chat_response.get("warnings") or []),
            traces=list(chat_response.get("trace") or runtime_raw.get("trace") or []),
            events=list((runtime_raw.get("events") or {}).get("events") or []),
            raw={"chat": chat_response, "runtime": runtime_raw},
        )

    def _section(self, lifecycle: dict[str, Any], key: str, *, fallback: Any) -> dict[str, Any]:
        value = lifecycle.get(key)
        if isinstance(value, dict):
            return value
        return fallback if isinstance(fallback, dict) else {}

    def _completion(self, lifecycle: dict[str, Any], result_state: dict[str, Any], result: dict[str, Any]) -> dict[str, Any]:
        value = lifecycle.get("completion")
        if isinstance(value, dict):
            return value
        completion = result.get("completion") if isinstance(result.get("completion"), dict) else {}
        return {**completion, **result_state}


class RuntimeDoctorContractValidator:
    def validate(self, expected: RuntimeDoctorExpectedContract, observed: RuntimeDoctorRawSnapshot) -> RuntimeDoctorAnalysis:
        violations: list[RuntimeDoctorViolation] = []
        violations.extend(self._required_sections(expected, observed))
        violations.extend(self._expected_fields(expected, observed))
        violations.extend(self._runtime_invariants(observed))
        status: RuntimeDoctorStatus = "PASS" if not violations else "FAIL"
        return RuntimeDoctorAnalysis(
            status=status,
            violations=violations,
            summary="Runtime contract passed." if status == "PASS" else f"{len(violations)} runtime contract violation(s) detected.",
        )

    def _required_sections(self, expected: RuntimeDoctorExpectedContract, observed: RuntimeDoctorRawSnapshot) -> list[RuntimeDoctorViolation]:
        rows: list[RuntimeDoctorViolation] = []
        data = observed.model_dump(mode="json")
        for section in expected.required_raw_sections:
            value = data.get(section)
            if value in (None, {}, []):
                rows.append(self._violation("raw_section_missing", f"Required RAW section missing: {section}", section, value, f"raw.{section}"))
        return rows

    def _expected_fields(self, expected: RuntimeDoctorExpectedContract, observed: RuntimeDoctorRawSnapshot) -> list[RuntimeDoctorViolation]:
        rows: list[RuntimeDoctorViolation] = []
        chat = observed.chat_response
        intent = observed.intent
        task = observed.task
        task_run = observed.task_run
        completion = observed.completion
        artifacts = observed.artifacts
        if expected.expected_status and chat.get("status") != expected.expected_status:
            rows.append(self._violation("status_mismatch", "Chat status does not match expected contract.", expected.expected_status, chat.get("status"), "chat_response.status"))
        for key, source, observed_value in [
            ("intent_type", intent, intent.get("intent_type")),
            ("operation_type", chat, chat.get("operation_type") or intent.get("operation_type")),
            ("contract_type", observed.operation_contract, observed.operation_contract.get("contract_type") or task_run.get("contract_type")),
            ("runtime_profile", observed.operation_contract, observed.operation_contract.get("runtime_profile") or task_run.get("runtime_profile")),
        ]:
            expected_value = getattr(expected, key)
            if expected_value and observed_value != expected_value:
                rows.append(self._violation(f"{key}_mismatch", f"{key} does not match expected contract.", expected_value, observed_value, key))
        if expected.requires_task is True and not (task.get("task_id") or task_run.get("run_id") or task_run.get("task_run_id")):
            rows.append(self._violation("task_missing", "Expected task identity was not created.", True, False, "task.task_id"))
        if expected.requires_approval is True and not observed.approval.get("approval_id") and not chat.get("approval_id"):
            rows.append(self._violation("approval_missing", "Expected approval was not created.", True, False, "approval.approval_id"))
        missing_outputs = set(expected.required_outputs)
        output_sources = [completion, observed.validation, observed.task_run, observed.chat_response.get("contract_preview") or {}]
        for source in output_sources:
            if isinstance(source, dict):
                for key in list(source.keys()):
                    missing_outputs.discard(str(key))
                for key in source.get("fulfilled_outcomes", []) or []:
                    missing_outputs.discard(str(key))
        for output in sorted(missing_outputs):
            rows.append(self._violation("required_output_missing", f"Required output missing: {output}", output, None, f"outputs.{output}"))
        missing_artifacts = set(expected.required_artifacts)
        artifact_rows = artifacts.get("artifacts") if isinstance(artifacts.get("artifacts"), list) else []
        for item in artifact_rows:
            if isinstance(item, dict):
                missing_artifacts.discard(str(item.get("logical_path")))
                missing_artifacts.discard(str(item.get("artifact_id")))
        for artifact in sorted(item for item in missing_artifacts if item and item != "None"):
            rows.append(self._violation("required_artifact_missing", f"Required artifact missing: {artifact}", artifact, None, f"artifacts.{artifact}"))
        return rows

    def _runtime_invariants(self, observed: RuntimeDoctorRawSnapshot) -> list[RuntimeDoctorViolation]:
        rows: list[RuntimeDoctorViolation] = []
        lifecycle_status = self._status(observed.lifecycle)
        validation_status = self._status(observed.validation)
        completion_status = self._status(observed.completion)
        truth = observed.speaker_truth
        truth_status = str(truth.get("status") or truth.get("speaker_truth_status") or "")
        canonical = (observed.task_run.get("canonical_state") if isinstance(observed.task_run.get("canonical_state"), dict) else {})
        canonical_status = str(canonical.get("status") or "")
        if completion_status in {"completed", "COMPLETED"} and validation_status in {"blocked", "failed", "incomplete", "missing"}:
            rows.append(self._violation("completion_validation_divergence", "Completion cannot be completed while validation is not successful.", completion_status, validation_status, "completion.validation"))
        semantic_states = self._artifact_semantic_states(observed.validation, observed.completion)
        incomplete_semantics = [
            item
            for item in semantic_states
            if item.get("status") in {"blocked", "partial", "not_applicable"}
            or item.get("semantic_status") in {"blocked", "partial", "not_applicable"}
        ]
        if validation_status in {"passed", "PASS", "validated"} and incomplete_semantics:
            rows.append(
                self._violation(
                    "artifact_semantic_validation_incomplete",
                    "Validation cannot pass while required artifact semantic profiles are incomplete.",
                    "artifact_semantic_profiles:passed",
                    incomplete_semantics,
                    "validation.artifact_semantic_profiles",
                )
            )
        if completion_status in {"completed", "COMPLETED"} and incomplete_semantics:
            rows.append(
                self._violation(
                    "completion_artifact_semantic_divergence",
                    "Completion cannot be completed while artifact semantic profiles are incomplete.",
                    "semantic_completion_safe",
                    incomplete_semantics,
                    "completion.artifact_semantic_profiles",
                )
            )
        if canonical_status and canonical_status == "COMPLETED" and truth.get("safe_to_report_success") is False:
            rows.append(self._violation("speaker_truth_inconsistent", "Canonical state is completed but Speaker Truth is not safe.", "safe", truth, "speaker_truth"))
        if lifecycle_status in {"running", "RUNNING"} and completion_status in {"completed", "COMPLETED"}:
            rows.append(self._violation("lifecycle_completion_divergence", "Lifecycle is running but completion is completed.", lifecycle_status, completion_status, "lifecycle.completion"))
        return rows

    def _status(self, value: dict[str, Any]) -> str:
        return str(value.get("status") or value.get("chat_response_status") or value.get("completion_status") or value.get("validation_status") or "")

    def _artifact_semantic_states(self, validation: dict[str, Any], completion: dict[str, Any]) -> list[dict[str, Any]]:
        states: list[dict[str, Any]] = []
        for source in (validation, completion.get("metadata") if isinstance(completion.get("metadata"), dict) else {}):
            if not isinstance(source, dict):
                continue
            for key in ("artifact_semantic_validations", "artifact_semantic_profiles"):
                rows = source.get(key)
                if isinstance(rows, list):
                    states.extend(item for item in rows if isinstance(item, dict))
        return states

    def _violation(self, violation_type: str, summary: str, expected: Any, observed: Any, evidence_path: str) -> RuntimeDoctorViolation:
        return RuntimeDoctorViolation(
            violation_type=violation_type,
            summary=summary,
            expected=expected,
            observed=observed,
            evidence_path=evidence_path,
            evidence={"path": evidence_path, "observed": observed},
        )


class RuntimeDoctorRootCauseEngine:
    COMPONENT_MAP = {
        "raw_section_missing": ("runtime_observability", ["src/aipinho/services/runtime/universal_task_session_service.py"], ["get_session"]),
        "task_missing": ("task_bootstrap_runtime", ["src/aipinho/services/runtime/task_bootstrap_runtime_service.py"], ["bootstrap"]),
        "approval_missing": ("approval_runtime", ["src/aipinho/services/approvals/approval_service.py"], ["create_approval_for_preview"]),
        "required_artifact_missing": ("artifact_runtime", ["src/aipinho/services/artifacts/artifact_runtime_service.py"], ["create", "by_task"]),
        "required_output_missing": ("completion_runtime", ["src/aipinho/services/runtime/canonical_operation_state_service.py"], ["derive"]),
        "completion_validation_divergence": ("validation_ordering", ["src/aipinho/services/runtime/runtime_truth_engine.py"], ["evaluate"]),
        "artifact_semantic_validation_incomplete": ("artifact_semantic_validation", ["src/aipinho/services/artifacts/artifact_semantic_contract_service.py"], ["profile", "validate_artifact"]),
        "completion_artifact_semantic_divergence": ("artifact_semantic_validation", ["src/aipinho/services/governance/runtime/readonly_analysis_artifact_runtime_service.py"], ["_validate_outputs", "_completion"]),
        "ENTITY_NOT_OBSERVED": ("entity_compilation", ["src/aipinho/services/artifacts/observed_entity_compilation_service.py"], ["compile"]),
        "ENTITY_SOURCE_NOT_OBSERVED": ("entity_compilation", ["src/aipinho/services/artifacts/observed_entity_compilation_service.py"], ["compile"]),
        "ENTITY_CARDINALITY_TRUNCATED": ("entity_compilation", ["src/aipinho/services/artifacts/observed_entity_compilation_service.py"], ["compile"]),
        "ATTRIBUTE_NOT_OBSERVED": ("schema_coverage", ["src/aipinho/services/artifacts/observed_entity_compilation_service.py", "src/aipinho/services/artifacts/artifact_semantic_contract_service.py"], ["value_for_field", "profile"]),
        "NO_ENTITY_OVERLAPS_CONTRACT_ATTRIBUTES": ("entity_selection", ["src/aipinho/services/artifacts/contract_driven_perception_service.py"], ["candidate_entity_set"]),
        "ENTITY_SELECTION_EMPTY": ("entity_selection", ["src/aipinho/services/artifacts/contract_driven_perception_service.py"], ["candidate_entity_set"]),
        "ENTITY_SELECTION_POLICY_NOT_APPLIED": ("entity_selection", ["src/aipinho/services/artifacts/contract_driven_perception_service.py"], ["candidate_entity_set", "_entity_selection_contract"]),
        "ROOT_ROLE_METADATA_MISSING": ("entity_selection", ["src/aipinho/services/artifacts/observed_entity_compilation_service.py", "src/aipinho/services/artifacts/contract_driven_perception_service.py"], ["_root_descriptors", "candidate_entity_set"]),
        "ENTITY_SELECTED_FROM_UNCLASSIFIED_ROOT": ("entity_selection", ["src/aipinho/services/artifacts/observed_entity_compilation_service.py", "src/aipinho/services/artifacts/contract_driven_perception_service.py"], ["_file_entity", "candidate_entity_set"]),
        "WORKSPACE_ROLE_MISMATCH": ("entity_selection", ["src/aipinho/services/artifacts/observed_entity_compilation_service.py", "src/aipinho/services/artifacts/contract_driven_perception_service.py"], ["_entity_policy_rejections"]),
        "OBSERVER_CAPABILITY_MISSING": ("observer_capability", ["src/aipinho/services/artifacts/contract_driven_perception_service.py"], ["observation_plan"]),
        "NO_MATCHING_CAPABILITY": ("capability_matching", ["src/aipinho/services/artifacts/contract_driven_perception_service.py"], ["capability_matches"]),
        "CAPABILITY_REJECTED": ("capability_arbitration", ["src/aipinho/services/artifacts/contract_driven_perception_service.py"], ["capability_decisions"]),
        "LOW_CONFIDENCE": ("capability_arbitration", ["src/aipinho/services/artifacts/contract_driven_perception_service.py"], ["capability_decisions"]),
        "MULTIPLE_CAPABILITIES_AVAILABLE": ("capability_arbitration", ["src/aipinho/services/artifacts/contract_driven_perception_service.py"], ["capability_decisions"]),
        "ENCODING_MOJIBAKE_SUSPECTED": (
            "encoding",
            ["src/aipinho/services/semantic_runtime/semantic_ingress_doctor_service.py", "src/aipinho/services/governance/intent/intent_normalizer.py"],
            ["semantic_ingress_doctor.prompt_normalization"],
        ),
        "STATE_EFFECT_UNRESOLVED": (
            "state_effects",
            ["src/aipinho/services/semantic_runtime/semantic_ingress_doctor_service.py", "src/aipinho/services/semantic_runtime/semantic_proposition_normalization_service.py"],
            ["semantic_ingress_doctor.state_effects"],
        ),
        "STATE_EFFECT_CONTRACT_MISMATCH": (
            "operation_contract_selection",
            ["src/aipinho/services/semantic_runtime/semantic_ingress_doctor_service.py", "src/aipinho/services/governance/lifecycle/governance_lifecycle_service.py"],
            ["semantic_ingress_doctor.intent_decision", "semantic_ingress_doctor.operation_contract_decision"],
        ),
        "OPERATION_CONTRACT_STATE_EFFECT_MISMATCH": (
            "operation_contract_selection",
            ["src/aipinho/services/semantic_runtime/semantic_ingress_doctor_service.py", "src/aipinho/services/governance/lifecycle/governance_lifecycle_service.py"],
            ["semantic_ingress_doctor.operation_contract_decision"],
        ),
        "READONLY_CONTRACT_PROMOTED_TO_MUTATION": (
            "operation_contract_selection",
            ["src/aipinho/services/semantic_runtime/semantic_ingress_doctor_service.py", "src/aipinho/services/governance/lifecycle/governance_lifecycle_service.py"],
            ["semantic_ingress_doctor.operation_contract_decision"],
        ),
        "EXECUTION_FAILED": ("observer_execution", ["src/aipinho/services/artifacts/observation_execution_boundary_service.py"], ["execute"]),
        "OBSERVER_NOT_BOUND": ("observer_execution", ["src/aipinho/services/artifacts/observation_execution_boundary_service.py"], ["execute"]),
        "OBSERVER_INPUT_SCHEMA_INVALID": ("observer_execution", ["src/aipinho/services/artifacts/observation_execution_boundary_service.py"], ["execute"]),
        "OBSERVER_OUTPUT_SCHEMA_INVALID": ("observer_execution", ["src/aipinho/services/artifacts/observation_execution_boundary_service.py"], ["execute"]),
        "OBSERVER_TIMEOUT": ("observer_execution", ["src/aipinho/services/artifacts/observation_execution_boundary_service.py"], ["execute"]),
        "OBSERVER_RUNTIME_ERROR": ("observer_execution", ["src/aipinho/services/artifacts/observation_execution_boundary_service.py"], ["execute"]),
        "OBSERVER_POLICY_BLOCKED": ("observer_execution", ["src/aipinho/services/artifacts/observation_execution_boundary_service.py"], ["execute"]),
        "OBSERVER_PRODUCED_NO_EVIDENCE": ("observer_execution", ["src/aipinho/services/artifacts/observation_execution_boundary_service.py"], ["execute"]),
        "OBSERVER_CONFIDENCE_TOO_LOW": ("observer_execution", ["src/aipinho/services/artifacts/observation_execution_boundary_service.py"], ["execute"]),
        "MEDIA_BACKEND_NOT_AVAILABLE": ("observer_execution", ["src/aipinho/capabilities/media_metadata/backends/mutagen_backend.py", "src/aipinho/capabilities/media_metadata/policy.py"], ["probe", "observe"]),
        "MEDIA_BACKEND_UNSUPPORTED_FORMAT": ("observer_execution", ["src/aipinho/capabilities/media_metadata/backends/native_minimal_backend.py", "src/aipinho/capabilities/media_metadata/policy.py"], ["probe", "observe"]),
        "MEDIA_BACKEND_NO_EVIDENCE": ("observer_execution", ["src/aipinho/capabilities/media_metadata/policy.py", "src/aipinho/capabilities/media_metadata/normalizer.py"], ["observe", "evidence_set"]),
        "MEDIA_BACKEND_PARTIAL_EVIDENCE": ("observer_execution", ["src/aipinho/capabilities/media_metadata/policy.py", "src/aipinho/capabilities/media_metadata/normalizer.py"], ["observe", "evidence_set"]),
        "MEDIA_BACKEND_CONTRADICTION": ("observer_execution", ["src/aipinho/capabilities/media_metadata/policy.py"], ["observe"]),
        "MEDIA_BACKEND_LOW_CONFIDENCE": ("observer_execution", ["src/aipinho/capabilities/media_metadata/normalizer.py"], ["evidence_set"]),
        "MEDIA_BACKEND_RUNTIME_ERROR": ("observer_execution", ["src/aipinho/capabilities/media_metadata/backends/mutagen_backend.py", "src/aipinho/capabilities/media_metadata/backends/native_minimal_backend.py"], ["probe"]),
        "MUTAGEN_NOT_IMPORTABLE": ("observer_execution", ["src/aipinho/capabilities/media_metadata/backends/mutagen_backend.py", "pyproject.toml"], ["descriptor", "probe", "dependency_sync"]),
        "MUTAGEN_DECLARED_BUT_NOT_INSTALLED": ("observer_execution", ["pyproject.toml", "src/aipinho/capabilities/media_metadata/backends/mutagen_backend.py"], ["dependency_sync"]),
        "MUTAGEN_RUNTIME_ENV_MISMATCH": ("observer_execution", ["scripts/dev/start_aipinho_9088.ps1", "pyproject.toml"], ["runtime_environment"]),
        "DEPENDENCY_SYNC_REQUIRED": ("observer_execution", ["pyproject.toml"], ["dependency_sync"]),
        "MEDIA_METADATA_DEPENDENCY_MISSING": ("observer_execution", ["src/aipinho/capabilities/media_metadata/policy.py"], ["payload_for_boundary"]),
        "MEDIA_METADATA_BACKEND_NOT_AVAILABLE": ("observer_execution", ["src/aipinho/capabilities/media_metadata/policy.py"], ["observe"]),
        "MEDIA_METADATA_READY_PARTIAL": ("evidence_coverage", ["src/aipinho/services/artifacts/contract_driven_perception_service.py"], ["semantic_coverage_report"]),
        "MEDIA_METADATA_READY_FULL": ("evidence_coverage", ["src/aipinho/services/artifacts/contract_driven_perception_service.py"], ["semantic_coverage_report"]),
        "MEDIA_METADATA_BACKEND_PARTIAL": ("observer_execution", ["src/aipinho/capabilities/media_metadata/policy.py"], ["observe"]),
        "MEDIA_METADATA_EVIDENCE_PARTIAL": ("evidence_coverage", ["src/aipinho/services/artifacts/contract_driven_perception_service.py"], ["evidence_set", "semantic_coverage_report"]),
        "MEDIA_METADATA_EVIDENCE_COVERAGE_INSUFFICIENT": ("evidence_coverage", ["src/aipinho/services/artifacts/contract_driven_perception_service.py"], ["semantic_coverage_report"]),
        "FFPROBE_NOT_AVAILABLE": ("observer_execution", ["src/aipinho/capabilities/media_metadata/backends/ffprobe_backend.py"], ["probe"]),
        "FFPROBE_TIMEOUT": ("observer_execution", ["src/aipinho/capabilities/media_metadata/backends/ffprobe_backend.py"], ["probe"]),
        "FFPROBE_INVALID_JSON": ("observer_execution", ["src/aipinho/capabilities/media_metadata/backends/ffprobe_backend.py"], ["probe"]),
        "FFPROBE_RUNTIME_ERROR": ("observer_execution", ["src/aipinho/capabilities/media_metadata/backends/ffprobe_backend.py"], ["probe"]),
        "ATTRIBUTE_VALUE_NOT_OBSERVED": ("attribute_observation", ["src/aipinho/services/artifacts/contract_driven_perception_service.py"], ["attribute_observations"]),
        "EVIDENCE_MISSING": ("evidence_recording", ["src/aipinho/schemas/artifacts/contract_perception.py", "src/aipinho/services/artifacts/contract_driven_perception_service.py"], ["evidence_set", "semantic_self_review"]),
        "TRACEABILITY_MISSING": ("semantic_self_review", ["src/aipinho/schemas/artifacts/contract_perception.py", "src/aipinho/services/artifacts/contract_driven_perception_service.py"], ["semantic_self_review"]),
        "CONFIDENCE_OR_EVIDENCE_INSUFFICIENT": ("semantic_self_review", ["src/aipinho/schemas/artifacts/contract_perception.py", "src/aipinho/services/artifacts/contract_driven_perception_service.py"], ["semantic_self_review"]),
        "UNSUPPORTED_ASSERTION_PROMOTED": ("semantic_assertions", ["src/aipinho/schemas/artifacts/contract_perception.py", "src/aipinho/services/artifacts/contract_driven_perception_service.py"], ["semantic_assertions"]),
        "EVIDENCE_CONFLICT": ("semantic_assertions", ["src/aipinho/schemas/artifacts/contract_perception.py", "src/aipinho/services/artifacts/contract_driven_perception_service.py"], ["semantic_assertions"]),
        "KNOWLEDGE_MISSING": ("knowledge_representation", ["src/aipinho/schemas/artifacts/contract_perception.py", "src/aipinho/services/artifacts/contract_driven_perception_service.py"], ["knowledge_records"]),
        "TRUTH_NOT_READY": ("truth_readiness", ["src/aipinho/schemas/artifacts/contract_perception.py", "src/aipinho/services/artifacts/contract_driven_perception_service.py", "src/aipinho/services/runtime/runtime_truth_engine.py"], ["semantic_coverage_2", "speaker_truth"]),
        "CVL_PROFILE_MISSING": ("firetest_lab", ["src/aipinho/services/cvl/cognitive_validation_laboratory_service.py"], ["suite"]),
        "PREDICTED_CAPABILITY_MISSING": ("prediction", ["src/aipinho/services/cvl/cognitive_validation_laboratory_service.py"], ["predict"]),
        "PREDICTED_EVIDENCE_AVAILABILITY_GAP": ("evidence_recording", ["src/aipinho/services/cvl/cognitive_validation_laboratory_service.py", "src/aipinho/services/artifacts/contract_driven_perception_service.py"], ["predict", "evidence_set"]),
        "PREDICTED_KNOWLEDGE_AVAILABILITY_GAP": ("knowledge_representation", ["src/aipinho/services/cvl/cognitive_validation_laboratory_service.py", "src/aipinho/services/artifacts/contract_driven_perception_service.py"], ["predict", "knowledge_records"]),
        "PREDICTED_SEMANTIC_COMPLETION_GAP": ("semantic_self_review", ["src/aipinho/services/cvl/cognitive_validation_laboratory_service.py", "src/aipinho/services/artifacts/contract_driven_perception_service.py"], ["predict", "semantic_self_review"]),
        "PREDICTED_TRUTH_READINESS_GAP": ("truth_readiness", ["src/aipinho/services/cvl/cognitive_validation_laboratory_service.py", "src/aipinho/services/runtime/runtime_truth_engine.py"], ["predict", "speaker_truth"]),
        "PREDICTED_VALIDATION_PROBABILITY_LOW": ("validation", ["src/aipinho/services/cvl/cognitive_validation_laboratory_service.py", "src/aipinho/services/runtime/canonical_operation_state_service.py"], ["predict", "validation"]),
        "PREDICTED_ARTIFACT_CONTRACT_GAP": ("prediction", ["src/aipinho/services/cvl/cognitive_validation_laboratory_service.py"], ["predict"]),
        "DEPENDENCY_GRAPH_INCOMPLETE": ("dependency_graph", ["src/aipinho/services/cvl/cognitive_validation_laboratory_service.py"], ["build"]),
        "COGNITIVE_COVERAGE_GAP": ("coverage", ["src/aipinho/services/cvl/cognitive_validation_laboratory_service.py"], ["report"]),
        "SIMULATION_PREDICTED_BLOCK": ("simulation", ["src/aipinho/services/cvl/cognitive_validation_laboratory_service.py"], ["simulate"]),
        "PREDICTION_ACCURACY_UNKNOWN": ("prediction_accuracy", ["src/aipinho/services/cvl/cognitive_validation_laboratory_service.py"], ["predict"]),
        "SIMULATION_ACCURACY_UNKNOWN": ("simulation_accuracy", ["src/aipinho/services/cvl/cognitive_validation_laboratory_service.py"], ["simulate"]),
        "speaker_truth_inconsistent": ("speaker_truth", ["src/aipinho/services/runtime/runtime_truth_engine.py"], ["evaluate"]),
        "lifecycle_completion_divergence": ("lifecycle_runtime", ["src/aipinho/services/runtime/task_run_lifecycle_service.py"], ["transition"]),
    }

    def diagnose(self, analysis: RuntimeDoctorAnalysis) -> list[RuntimeDoctorRootCause]:
        causes: list[RuntimeDoctorRootCause] = []
        for violation in analysis.violations:
            component, files, functions = self.COMPONENT_MAP.get(
                violation.violation_type,
                ("runtime_contract", ["src/aipinho/services/runtime"], []),
            )
            causes.append(
                RuntimeDoctorRootCause(
                    violation_id=violation.violation_id,
                    probable_component=component,
                    probable_files=files,
                    probable_functions=functions,
                    confidence="medium" if component == "runtime_contract" else "high",
                    impact=violation.severity,
                    evidence=violation.evidence,
                )
            )
        return causes


class RuntimeDoctorPatchPlanner:
    def plan(self, causes: list[RuntimeDoctorRootCause]) -> RuntimeDoctorPatchPlan:
        files = list(dict.fromkeys(file for cause in causes for file in cause.probable_files))
        functions = list(dict.fromkeys(fn for cause in causes for fn in cause.probable_functions))
        status = "no_patch_needed" if not causes else "approval_required"
        return RuntimeDoctorPatchPlan(
            status=status,
            files=files,
            functions=functions,
            risks=["Patch must preserve Runtime Truth, Artifact Binding and approval gates."] if causes else [],
            rollback=["Revert only the files listed in this patch plan."] if causes else [],
            strategy=[
                "Patch only the component linked to observed contract violations.",
                "Add or update regression for the violated architectural invariant.",
                "Rerun the same Runtime Doctor contract after patch.",
            ] if causes else [],
            requires_approval=bool(causes),
            blocked_reason=None if causes else "no_violations",
        )


class RuntimeDoctorPatchExecutor:
    def execute(self, patch: RuntimeDoctorPatchPlan, *, approved: bool) -> RuntimeDoctorPatchExecution:
        if not patch.requires_approval:
            return RuntimeDoctorPatchExecution(status="not_required", patch_id=patch.patch_id, approval_required=False, message="No patch required.")
        if not approved:
            patch.status = "pending_approval"
            return RuntimeDoctorPatchExecution(
                status="pending_approval",
                patch_id=patch.patch_id,
                approval_required=True,
                approval_id=patch.approval_id,
                message="Patch plan produced; approval required before code changes.",
            )
        if not patch.files:
            return RuntimeDoctorPatchExecution(status="blocked", patch_id=patch.patch_id, message="No target files in patch plan.")
        return RuntimeDoctorPatchExecution(
            status="blocked",
            patch_id=patch.patch_id,
            approval_required=True,
            message="Automated patch execution requires concrete patch operations; none were generated from RAW evidence.",
        )


class RuntimeDoctorRegressionRunner:
    def diff(self, before: RuntimeDoctorAnalysis, after: RuntimeDoctorAnalysis | None) -> RuntimeDoctorDiff:
        if after is None:
            return RuntimeDoctorDiff(status="not_run")
        before_types = {item.violation_type for item in before.violations}
        after_types = {item.violation_type for item in after.violations}
        return RuntimeDoctorDiff(
            status="compared",
            removed_violations=sorted(before_types - after_types),
            new_violations=sorted(after_types - before_types),
            unchanged_violations=sorted(before_types & after_types),
        )


class RuntimeDoctorReportWriter:
    def __init__(self, root: Path | None = None, artifacts: ArtifactRuntimeService | None = None) -> None:
        self.root = root or PATHS.project_root / "data" / "runtime" / "runtime_doctor"
        self.artifacts = artifacts or ArtifactRuntimeService()

    def save(self, result: RuntimeDoctorRunResult) -> RuntimeDoctorRunResult:
        self.root.mkdir(parents=True, exist_ok=True)
        path = self.root / f"{result.doctor_run_id}.json"
        path.write_text(json.dumps(result.model_dump(mode="json"), ensure_ascii=False, indent=2), encoding="utf-8")
        result.report_path = str(path)
        try:
            artifact = self.artifacts.create(
                ArtifactRuntimeCreateRequest(
                    source_agent="runtime_doctor",
                    task_id=result.doctor_run_id,
                    task_run_id=result.doctor_run_id,
                    logical_path=f"runtime_doctor/{result.doctor_run_id}.json",
                    artifact_type="runtime_doctor_report",
                    content_type="application/json",
                    content=path.read_text(encoding="utf-8"),
                    producer_step="runtime_doctor_report_writer",
                    event_id=f"{result.doctor_run_id}:runtime_doctor_report_writer",
                    validation_status="validated",
                    status="ready",
                    evidence_refs=[f"runtime_doctor_run:{result.doctor_run_id}"],
                    metadata={
                        "runtime_doctor": True,
                        "binding_source": "runtime_doctor_run",
                        "runtime_doctor_run_id": result.doctor_run_id,
                    },
                )
            )
            result.report_artifact_id = artifact.artifact_id
            path.write_text(json.dumps(result.model_dump(mode="json"), ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception:
            pass
        return result


class RuntimeDoctorService:
    def __init__(
        self,
        *,
        endpoint_client: RuntimeDoctorEndpointClient | None = None,
        collector: RuntimeDoctorRawCollector | None = None,
        validator: RuntimeDoctorContractValidator | None = None,
        root_cause_engine: RuntimeDoctorRootCauseEngine | None = None,
        patch_planner: RuntimeDoctorPatchPlanner | None = None,
        patch_executor: RuntimeDoctorPatchExecutor | None = None,
        regression_runner: RuntimeDoctorRegressionRunner | None = None,
        report_writer: RuntimeDoctorReportWriter | None = None,
    ) -> None:
        self.endpoint_client = endpoint_client or RuntimeDoctorEndpointClient()
        self.collector = collector or RuntimeDoctorRawCollector()
        self.validator = validator or RuntimeDoctorContractValidator()
        self.root_cause_engine = root_cause_engine or RuntimeDoctorRootCauseEngine()
        self.patch_planner = patch_planner or RuntimeDoctorPatchPlanner()
        self.patch_executor = patch_executor or RuntimeDoctorPatchExecutor()
        self.regression_runner = regression_runner or RuntimeDoctorRegressionRunner()
        self.report_writer = report_writer or RuntimeDoctorReportWriter()

    def run(self, request: RuntimeDoctorTestRequest) -> RuntimeDoctorRunResult:
        iterations: list[RuntimeDoctorIteration] = []
        previous_analysis: RuntimeDoctorAnalysis | None = None
        final_status: RuntimeDoctorStatus = "FAIL"
        max_iterations = max(1, min(request.max_iterations, 5))
        for index in range(1, max_iterations + 1):
            iteration = RuntimeDoctorIteration(index=index)
            chat_response = self.endpoint_client.send_chat(request)
            task_run_id = chat_response.get("task_id")
            runtime_raw = self.endpoint_client.runtime_raw(str(task_run_id) if task_run_id else None)
            snapshot = self.collector.collect(
                iteration_id=iteration.iteration_id,
                chat_response=chat_response,
                runtime_raw=runtime_raw,
            )
            analysis = self.validator.validate(request.expected_contract, snapshot)
            root_causes = self.root_cause_engine.diagnose(analysis)
            patch_plan = self.patch_planner.plan(root_causes)
            patch_execution = self.patch_executor.execute(patch_plan, approved=request.auto_apply_patch)
            iteration.raw_snapshot = snapshot
            iteration.analysis = analysis
            iteration.root_causes = root_causes
            iteration.patch_plan = patch_plan
            iteration.patch_execution = patch_execution
            iteration.status = analysis.status
            iteration.task_id = snapshot.task.get("task_id")
            iteration.task_run_id = str(task_run_id) if task_run_id else snapshot.task_run.get("run_id") or snapshot.task_run.get("task_run_id")
            iteration.operation_id = snapshot.task.get("operation_id") or chat_response.get("operation_id")
            iteration.approval_ids = [item for item in [chat_response.get("approval_id"), snapshot.approval.get("approval_id")] if item]
            iteration.artifact_ids = self._artifact_ids(snapshot)
            if previous_analysis is not None:
                iteration.regression_diff = self.regression_runner.diff(previous_analysis, analysis)
            iteration.finished_at = utc_now_iso()
            iterations.append(iteration)
            previous_analysis = analysis
            if analysis.status == "PASS":
                final_status = "PASS"
                break
            if patch_execution.status == "pending_approval":
                final_status = "PENDING_APPROVAL"
                break
            if not root_causes:
                final_status = "BLOCKED"
                break
        result = RuntimeDoctorRunResult(
            status=final_status,
            iterations=iterations,
            final_summary=self._summary(final_status, iterations),
        )
        return self.report_writer.save(result)

    def status(self) -> dict[str, Any]:
        return {
            "status": "ok",
            "service": "runtime_doctor",
            "hardcoded_test_cases": False,
            "uses_contracts": True,
            "patch_requires_approval": True,
        }

    def _artifact_ids(self, snapshot: RuntimeDoctorRawSnapshot) -> list[str]:
        rows = snapshot.artifacts.get("artifacts") if isinstance(snapshot.artifacts.get("artifacts"), list) else []
        ids = [str(item.get("artifact_id")) for item in rows if isinstance(item, dict) and item.get("artifact_id")]
        ids.extend(link.get("artifact_id") for link in snapshot.chat_response.get("artifact_links", []) if isinstance(link, dict) and link.get("artifact_id"))
        return list(dict.fromkeys(ids))

    def _summary(self, status: RuntimeDoctorStatus, iterations: list[RuntimeDoctorIteration]) -> str:
        last = iterations[-1] if iterations else None
        if status == "PASS":
            return "RUNTIME_DOCTOR_READY: runtime contract passed."
        if status == "PENDING_APPROVAL":
            count = len(last.analysis.violations) if last and last.analysis else 0
            return f"Runtime Doctor found {count} violation(s) and produced a patch plan awaiting approval."
        return "Runtime Doctor stopped without PASS; inspect iteration diagnostics."
