import base64
import io
import json
import zipfile

from aipinho.services.governance.runtime.readonly_analysis_artifact_runtime_service import ReadonlyAnalysisArtifactRuntimeService
from aipinho.services.artifacts.artifact_semantic_contract_service import ArtifactSemanticContractService


def test_evidence_archive_contains_semantic_diagnostic_reports() -> None:
    encoded = ReadonlyAnalysisArtifactRuntimeService()._evidence_archive_content(
        {
            "logical_path": "reports/evidence.zip",
            "task_run_id": "task_run_11111111111111111111111111111111",
            "phase_id": "phase_1",
            "analysis": {
                "observed_entity_graph": {
                    "roots_scanned_by_role": {"library_root": ["X:/library"]},
                    "entities_by_root_role": {"library_root": 1},
                    "entities": [{"entity_id": "entity_1"}],
                    "semantic_gaps": [{"reason_code": "MUSIC_INVENTORY_PARTIAL_EVIDENCE"}],
                }
            },
            "dependencies": {},
        }
    )

    with zipfile.ZipFile(io.BytesIO(base64.b64decode(encoded))) as archive:
        names = set(archive.namelist())
        assert "semantic_artifact_contract.json" in names
        assert "observation_goals.json" in names
        assert "entity_selection_report.json" in names
        assert "capability_status.json" in names
        assert "artifact_binding_report.json" in names
        assert "limitations.json" in names
        capability = json.loads(archive.read("capability_status.json").decode("utf-8"))

    assert capability["media_metadata_capability"]["status"] == "not_configured"
    assert capability["relationship_cognition"]["reason_code"] == "RELATIONSHIP_OBSERVATION_NOT_BOUND"


def test_evidence_archive_validation_decodes_runtime_base64_zip_content() -> None:
    encoded = ReadonlyAnalysisArtifactRuntimeService()._evidence_archive_content(
        {
            "logical_path": "reports/evidence.zip",
            "task_run_id": "task_run_11111111111111111111111111111111",
            "phase_id": "phase_1",
            "analysis": {"observed_entity_graph": {"entities": []}},
            "dependencies": {},
        }
    )

    validation = ArtifactSemanticContractService().validate(
        logical_path="reports/firetest5/evidence_phase1.zip",
        content=encoded,
        content_type="application/zip",
    )

    assert "artifact_evidence_entries_missing" not in validation.missing_requirements
