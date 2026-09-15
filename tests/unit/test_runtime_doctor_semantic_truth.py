from __future__ import annotations

from aipinho.schemas.runtime_doctor import (
    RuntimeDoctorExpectedContract,
    RuntimeDoctorRawSnapshot,
)
from aipinho.services.runtime_doctor.runtime_doctor_service import (
    RuntimeDoctorContractValidator,
)


def _snapshot(
    *,
    semantic_status: str,
    semantic_safe: bool,
    speaker_safe: bool,
):
    return RuntimeDoctorRawSnapshot(
        iteration_id="runtime_doctor_iteration_semantic_truth",
        lifecycle={"status": "completed"},
        validation={"status": "passed"},
        completion={"status": "completed"},
        speaker_truth={
            "status": "completed",
            "safe_to_report_success": speaker_safe,
            "semantic_truth_status": semantic_status,
            "semantic_truth_safe_to_report_success": semantic_safe,
            "semantic_truth_reason_codes": [
                f"semantic_truth_{semantic_status}"
            ],
            "semantic_graph_id": "semantic_graph_current",
            "semantic_graph_authority_sha256": "graph_sha_current",
            "semantic_truth_facet_id": "semantic_truth_facet_current",
            "semantic_truth_facet_authority_sha256": "facet_sha_current",
            "evidence": [
                {
                    "evidence_type": "semantic_truth_facet",
                    "evidence_id": "semantic_truth_facet_current",
                    "metadata": {
                        "semantic_graph_id": "semantic_graph_current",
                        "semantic_graph_authority_sha256": "graph_sha_current",
                        "active_revision_id": "semantic_graph_revision_current",
                        "authority_sha256": "facet_sha_current",
                    },
                }
            ],
        },
    )


def _analyze(snapshot):
    return RuntimeDoctorContractValidator().validate(
        RuntimeDoctorExpectedContract(required_raw_sections=[]),
        snapshot,
    )


def test_doctor_flags_speaker_success_when_semantic_truth_is_unsafe() -> None:
    analysis = _analyze(
        _snapshot(
            semantic_status="blocked",
            semantic_safe=False,
            speaker_safe=True,
        )
    )

    violation_types = {
        item.violation_type for item in analysis.violations
    }
    assert "speaker_truth_semantic_inconsistent" in violation_types
    assert "completion_semantic_truth_divergence" in violation_types
    semantic = next(
        item
        for item in analysis.violations
        if item.violation_type
        == "speaker_truth_semantic_inconsistent"
    )
    assert semantic.evidence_path == "speaker_truth.semantic_truth"
    assert semantic.observed["semantic_truth_status"] == "blocked"
    assert semantic.observed["semantic_graph_id"] == "semantic_graph_current"
    assert semantic.observed["semantic_graph_authority_sha256"] == "graph_sha_current"
    assert semantic.observed["semantic_truth_facet_id"] == "semantic_truth_facet_current"
    assert semantic.observed["active_revision_id"] == "semantic_graph_revision_current"


def test_doctor_flags_semantic_truth_evidence_binding_mismatch() -> None:
    snapshot = _snapshot(
        semantic_status="ready",
        semantic_safe=True,
        speaker_safe=True,
    )
    snapshot.speaker_truth["semantic_truth_facet_authority_sha256"] = (
        "facet_sha_tampered"
    )
    snapshot.speaker_truth["semantic_graph_id"] = "semantic_graph_foreign"

    analysis = _analyze(snapshot)

    violation = next(
        item
        for item in analysis.violations
        if item.violation_type == "semantic_truth_evidence_binding_invalid"
    )
    assert violation.evidence_path == "speaker_truth.semantic_truth_evidence"
    mismatches = violation.observed["binding_mismatches"]
    assert mismatches["semantic_truth_facet_authority_sha256"] == {
        "runtime_truth": "facet_sha_tampered",
        "evidence": "facet_sha_current",
    }
    assert mismatches["semantic_graph_id"] == {
        "runtime_truth": "semantic_graph_foreign",
        "evidence": "semantic_graph_current",
    }


def test_doctor_flags_completed_but_unresolved_semantic_truth() -> None:
    analysis = _analyze(
        _snapshot(
            semantic_status="insufficient_evidence",
            semantic_safe=False,
            speaker_safe=False,
        )
    )

    violation_types = {
        item.violation_type for item in analysis.violations
    }
    assert "completion_semantic_truth_divergence" in violation_types
    assert "speaker_truth_semantic_inconsistent" not in violation_types


def test_constrained_semantic_truth_with_unsafe_success_is_not_doctor_error() -> None:
    analysis = _analyze(
        _snapshot(
            semantic_status="constrained",
            semantic_safe=False,
            speaker_safe=False,
        )
    )

    semantic_violations = [
        item
        for item in analysis.violations
        if item.violation_type
        in {
            "speaker_truth_semantic_inconsistent",
            "completion_semantic_truth_divergence",
        }
    ]
    assert semantic_violations == []
