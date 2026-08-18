from aipinho.services.governance.runtime.readonly_analysis_artifact_runtime_service import (
    ReadonlyAnalysisArtifactRuntimeService,
)


def test_late_artifact_row_preserves_specific_terminal_reason() -> None:
    service = ReadonlyAnalysisArtifactRuntimeService()

    row = service._interrupted_artifact_row(
        "task_run_generic",
        {
            "logical_path": "reports/generic/output.csv",
            "phase": "artifact_render",
            "frontier": "ARTIFACT_RENDER_TERMINALITY",
            "terminal_reason_code": "PERCEPTION_FACT_SOURCE_BINDING_STALLED",
        },
    )

    assert row is not None
    assert row["status"] == "rejected"
    assert row["reason_code"] == "PERCEPTION_FACT_SOURCE_BINDING_STALLED"
    assert row["safe_to_use"] is False
