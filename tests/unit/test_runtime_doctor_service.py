from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from aipinho.core.paths import PATHS
from aipinho.schemas.runtime.runtime_doctor import ExpectedRuntimeContract
from aipinho.services.artifacts.artifact_interaction_core import ArtifactRegistryRepository
from aipinho.services.artifacts.artifact_runtime_service import ArtifactRuntimeService
from aipinho.services.artifacts.universal_artifact_registry_service import UniversalArtifactRegistryService
from aipinho.services.runtime.runtime_doctor_service import RuntimeDoctorService


def _doctor(tmp_path: Path) -> tuple[RuntimeDoctorService, ArtifactRuntimeService]:
    root = PATHS.project_root / "data" / "tmp_runtime_doctor_tests" / f"{tmp_path.name}_{uuid4().hex}"
    root.mkdir(parents=True, exist_ok=True)
    registry = ArtifactRegistryRepository(root / "artifact_registry.json")
    universal = UniversalArtifactRegistryService(registry=registry, store_root=root / "artifacts")
    artifact_runtime = ArtifactRuntimeService(registry=universal)
    return RuntimeDoctorService(artifact_runtime=artifact_runtime), artifact_runtime


def _assert_artifacts_registered(report, artifact_runtime: ArtifactRuntimeService) -> None:
    refs = report.artifact_refs
    artifact_ids = [
        refs.report_json_artifact_id,
        refs.report_markdown_artifact_id,
        refs.regression_matrix_csv_artifact_id,
    ]
    assert all(artifact_ids)
    for artifact_id in artifact_ids:
        artifact = artifact_runtime.get(str(artifact_id))
        assert artifact is not None
        assert artifact["status"] == "ready"
        assert artifact["source_agent"] == "aipinho_runtime_doctor"
        assert artifact["logical_path"].startswith("runtime_doctor/")


def _finding_types(report) -> set[str]:
    return {finding.regression_type for finding in report.findings}


def test_runtime_doctor_detects_intent_regression(tmp_path: Path) -> None:
    doctor, artifacts = _doctor(tmp_path)

    report = doctor.diagnose(
        expected=ExpectedRuntimeContract(
            expected_intent={"intent_type": "workspace_analysis_readonly"},
        ),
        runtime={"intent": {"intent_type": "conversation"}},
    )

    assert report.status == "FAIL"
    assert report.matrix.intent == "FAIL"
    assert "INTENT_REGRESSION" in _finding_types(report)
    assert all(finding.deterministic for finding in report.findings)
    _assert_artifacts_registered(report, artifacts)


def test_runtime_doctor_detects_missing_required_task(tmp_path: Path) -> None:
    doctor, artifacts = _doctor(tmp_path)

    report = doctor.diagnose(
        expected=ExpectedRuntimeContract(
            expected_intent={"requires_task": True},
        ),
        runtime={"intent": {"requires_task": False}},
    )

    assert report.matrix.lifecycle == "FAIL"
    assert "TASK_LIFECYCLE_REGRESSION" in _finding_types(report)
    _assert_artifacts_registered(report, artifacts)


def test_runtime_doctor_detects_workspace_binding_regression(tmp_path: Path) -> None:
    doctor, artifacts = _doctor(tmp_path)

    report = doctor.diagnose(
        expected=ExpectedRuntimeContract(
            expected_workspace_roots=[
                r"C:\ProjectRoot",
                r"D:\LibraryRoot",
            ],
        ),
        runtime={
            "workspace_context": {
                "library_roots": [r"D:\LibraryRoot"],
            }
        },
    )

    assert report.matrix.workspace_binding == "FAIL"
    assert "WORKSPACE_BINDING_REGRESSION" in _finding_types(report)
    _assert_artifacts_registered(report, artifacts)


def test_runtime_doctor_detects_artifact_contract_regression(tmp_path: Path) -> None:
    doctor, artifacts = _doctor(tmp_path)

    report = doctor.diagnose(
        expected=ExpectedRuntimeContract(
            expected_artifacts=["phase1_discovery.md", "music_inventory.csv"],
        ),
        runtime={"artifacts": []},
    )

    assert report.matrix.artifact_contract == "FAIL"
    assert "ARTIFACT_CONTRACT_REGRESSION" in _finding_types(report)
    _assert_artifacts_registered(report, artifacts)


def test_runtime_doctor_detects_validation_pass_with_missing_outputs(tmp_path: Path) -> None:
    doctor, artifacts = _doctor(tmp_path)

    report = doctor.diagnose(
        expected=ExpectedRuntimeContract(
            expected_validation={"status": "passed"},
        ),
        runtime={
            "validation": {"status": "passed"},
            "completion": {"missing_outputs": ["patch_result", "validation_result"]},
        },
    )

    assert report.matrix.validation == "FAIL"
    assert "VALIDATION_CONTRACT_REGRESSION" in _finding_types(report)
    _assert_artifacts_registered(report, artifacts)


def test_runtime_doctor_detects_validation_pass_with_blocked_artifact_semantics(tmp_path: Path) -> None:
    doctor, artifacts = _doctor(tmp_path)

    report = doctor.diagnose(
        expected=ExpectedRuntimeContract(),
        runtime={
            "validation": {
                "status": "passed",
                "artifact_semantic_validations": [
                    {
                        "logical_path": "reports/evidence_bundle.zip",
                        "status": "blocked",
                        "profile": {
                            "semantic_status": "blocked",
                            "material_status": "blocked",
                            "semantic_gaps": [{"gap_type": "artifact_material_kind_mismatch"}],
                        },
                    }
                ],
            },
            "completion": {
                "status": "completed",
                "metadata": {
                    "artifact_semantic_profiles": [
                        {
                            "artifact_path": "reports/evidence_bundle.zip",
                            "semantic_status": "blocked",
                        }
                    ]
                },
            },
        },
    )

    assert report.status == "FAIL"
    assert "ARTIFACT_SEMANTIC_VALIDATION_INCOMPLETE" in _finding_types(report)
    assert "COMPLETION_ARTIFACT_SEMANTIC_DIVERGENCE" in _finding_types(report)
    _assert_artifacts_registered(report, artifacts)


def test_runtime_doctor_classifies_contract_perception_reason_codes(tmp_path: Path) -> None:
    doctor, artifacts = _doctor(tmp_path)

    report = doctor.diagnose(
        expected=ExpectedRuntimeContract(),
        runtime={
            "validation": {
                "status": "blocked",
                "artifact_semantic_validations": [
                    {
                        "status": "blocked",
                        "profile": {
                            "semantic_status": "blocked",
                            "semantic_gaps": [
                                {
                                    "gap_type": "ATTRIBUTE_NOT_OBSERVED:codec",
                                    "reason_code": "NO_MATCHING_CAPABILITY",
                                    "perception_domain": "capability_matching",
                                }
                            ],
                        },
                    }
                ],
            },
        },
    )

    assert report.matrix.schema_coverage == "FAIL"
    assert report.matrix.capability_matching == "FAIL"
    assert "ARTIFACT_SCHEMA_COVERAGE_GAP" in _finding_types(report)
    assert "NO_MATCHING_CAPABILITY" in _finding_types(report)
    _assert_artifacts_registered(report, artifacts)


def test_runtime_doctor_classifies_capability_arbitration_reason_codes(tmp_path: Path) -> None:
    doctor, artifacts = _doctor(tmp_path)

    report = doctor.diagnose(
        expected=ExpectedRuntimeContract(),
        runtime={
            "validation": {
                "status": "blocked",
                "artifact_semantic_validations": [
                    {
                        "status": "blocked",
                        "profile": {
                            "semantic_status": "blocked",
                            "semantic_gaps": [
                                {
                                    "gap_type": "ATTRIBUTE_NOT_OBSERVED:generic_signal",
                                    "reason_code": "MULTIPLE_CAPABILITIES_AVAILABLE",
                                    "perception_domain": "capability_arbitration",
                                }
                            ],
                        },
                    }
                ],
            },
        },
    )

    assert report.matrix.capability_arbitration == "FAIL"
    assert "MULTIPLE_CAPABILITIES_AVAILABLE" in _finding_types(report)
    _assert_artifacts_registered(report, artifacts)


def test_runtime_doctor_classifies_semantic_self_review_reason_codes(tmp_path: Path) -> None:
    doctor, artifacts = _doctor(tmp_path)

    report = doctor.diagnose(
        expected=ExpectedRuntimeContract(),
        runtime={
            "validation": {
                "status": "blocked",
                "artifact_semantic_validations": [
                    {
                        "status": "blocked",
                        "profile": {
                            "semantic_status": "blocked",
                            "declared_contract": {
                                "perception": {
                                    "semantic_self_review": {
                                        "truth_readiness": "blocked",
                                        "can_speaker_claim": False,
                                        "reason_codes": ["CONFIDENCE_OR_EVIDENCE_INSUFFICIENT"],
                                    },
                                    "semantic_coverage_2": {
                                        "truth_coverage": 0.0,
                                        "blocking_reasons": ["CONFIDENCE_OR_EVIDENCE_INSUFFICIENT"],
                                    },
                                }
                            },
                        },
                    }
                ],
            },
        },
    )

    assert report.matrix.semantic_self_review == "FAIL"
    assert "CONFIDENCE_OR_EVIDENCE_INSUFFICIENT" in _finding_types(report)
    _assert_artifacts_registered(report, artifacts)


def test_runtime_doctor_detects_truth_consistency_regression(tmp_path: Path) -> None:
    doctor, artifacts = _doctor(tmp_path)

    report = doctor.diagnose(
        expected=ExpectedRuntimeContract(
            expected_completion={"status": "READY"},
        ),
        runtime={
            "completion": {"status": "READY"},
            "speaker_truth": {"status": "blocked"},
        },
    )

    assert report.matrix.completion == "PASS"
    assert report.matrix.speaker_truth == "FAIL"
    assert "TRUTH_CONSISTENCY_REGRESSION" in _finding_types(report)
    _assert_artifacts_registered(report, artifacts)


def test_runtime_doctor_detects_patch_candidate_without_diagnosis(tmp_path: Path) -> None:
    doctor, artifacts = _doctor(tmp_path)

    report = doctor.diagnose(
        expected=ExpectedRuntimeContract(),
        runtime={
            "patch_planning": {
                "patch_candidates": [
                    {
                        "candidate_id": "candidate_1",
                        "target_file": "src/app.py",
                    }
                ]
            }
        },
    )

    assert report.matrix.patch_planning == "FAIL"
    assert "PATCH_CANDIDATE_WITHOUT_DIAGNOSIS" in _finding_types(report)
    _assert_artifacts_registered(report, artifacts)


def test_runtime_doctor_explains_empty_model_replacement(tmp_path: Path) -> None:
    doctor, artifacts = _doctor(tmp_path)

    report = doctor.diagnose(
        expected=ExpectedRuntimeContract(),
        runtime={
            "metadata": {
                "canonical_inference_output_artifact": {
                    "empty_output": True,
                    "replacement_detected": False,
                    "diagnostics": ["legacy_edits_empty"],
                },
                "inference_input_doctor": {
                    "reason_codes": [
                        "PATCH_MODEL_EMPTY_OUTPUT",
                        "PROMPT_CODE_SNIPPET_MISSING",
                    ]
                },
            }
        },
    )

    assert report.matrix.inference == "FAIL"
    assert report.matrix.prompt == "FAIL"
    assert "PATCH_MODEL_EMPTY_OUTPUT" in _finding_types(report)
    assert "PROMPT_CODE_SNIPPET_MISSING" in _finding_types(report)
    _assert_artifacts_registered(report, artifacts)


def test_runtime_doctor_classifies_missing_repair_intent(tmp_path: Path) -> None:
    doctor, artifacts = _doctor(tmp_path)

    report = doctor.diagnose(
        expected=ExpectedRuntimeContract(),
        runtime={
            "patch_planning": {
                "status": "blocked",
                "blocked_reasons": [
                    "REPAIR_INTENT_MISSING",
                    "TARGET_SPECIFIC_EXPECTED_BEHAVIOR_MISSING",
                ],
            }
        },
    )

    assert report.matrix.patch_planning == "FAIL"
    assert report.matrix.repair_intent == "FAIL"
    assert "REPAIR_INTENT_MISSING" in _finding_types(report)
    assert "TARGET_SPECIFIC_EXPECTED_BEHAVIOR_MISSING" in _finding_types(report)
    _assert_artifacts_registered(report, artifacts)


def test_runtime_doctor_classifies_incremental_diagnosis_frontier_failures(tmp_path: Path) -> None:
    doctor, artifacts = _doctor(tmp_path)

    report = doctor.diagnose(
        expected=ExpectedRuntimeContract(),
        runtime={
            "patch_planning": {
                "status": "blocked",
                "blocked_reasons": [
                    "SEMANTIC_EVIDENCE_MISSING",
                    "BEHAVIOR_LOCALIZATION_MISSING",
                    "BEHAVIOR_JUSTIFICATION_MISSING",
                    "TRANSFORMATION_MISSING",
                ],
            }
        },
    )

    assert report.matrix.patch_planning == "FAIL"
    assert report.matrix.semantic_evidence == "FAIL"
    assert report.matrix.behavior_localization == "FAIL"
    assert report.matrix.behavior_justification == "FAIL"
    assert report.matrix.candidate_transformation == "FAIL"
    assert "SEMANTIC_EVIDENCE_MISSING" in _finding_types(report)
    assert "TRANSFORMATION_MISSING" in _finding_types(report)
    _assert_artifacts_registered(report, artifacts)


def test_runtime_doctor_passes_when_contract_matches_runtime(tmp_path: Path) -> None:
    doctor, artifacts = _doctor(tmp_path)

    report = doctor.diagnose(
        expected=ExpectedRuntimeContract(
            expected_intent={"intent_type": "workspace_analysis_readonly", "requires_task": True},
            expected_operation={"operation_type": "readonly_analysis"},
            expected_runtime_profile="readonly_analysis",
            expected_workspace_roots=[r"C:\Project", r"D:\Library"],
            expected_artifacts=["reports/phase1.md"],
            expected_validation={"status": "passed"},
            expected_completion={"status": "completed"},
            expected_speaker_truth={"status": "completed"},
            expected_dispatcher_state={"dispatcher_status": "available"},
            expected_timeline_events=["task_created", "validation_completed"],
        ),
        runtime={
            "intent": {"intent_type": "workspace_analysis_readonly", "requires_task": True},
            "operation_contract": {"operation_type": "readonly_analysis", "runtime_profile": "readonly_analysis"},
            "workspace_context": {"project_root": r"C:\Project", "library_roots": [r"D:\Library"]},
            "artifacts": [{"logical_path": "reports/phase1.md"}],
            "validation": {"status": "passed"},
            "completion": {"status": "completed", "missing_outputs": []},
            "speaker_truth": {"status": "completed"},
            "dispatcher": {"dispatcher_status": "available"},
            "timeline": {"events": [{"event_type": "task_created"}, {"event_type": "validation_completed"}]},
        },
    )

    assert report.status == "PASS"
    assert report.findings == []
    assert report.matrix.intent == "PASS"
    assert report.matrix.timeline == "PASS"
    _assert_artifacts_registered(report, artifacts)
