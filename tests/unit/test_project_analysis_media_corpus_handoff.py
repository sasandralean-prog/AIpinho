from __future__ import annotations

from aipinho.schemas.analysis.project_analysis_request import ProjectAnalysisRequest
from aipinho.services.analysis.project_analysis_service import ProjectAnalysisService


def test_project_analysis_hands_media_corpus_to_artifact_runtime_without_source_reads(tmp_path):
    library = tmp_path / "library"
    library.mkdir()
    (library / "track_one.m4a").write_bytes(b"media")
    (library / "track_two.flac").write_bytes(b"media")

    result = ProjectAnalysisService().analyze_project(
        ProjectAnalysisRequest(
            workspace=str(library),
            prompt="Gere um inventario governado da biblioteca de musicas.",
            workspace_context={"library_roots": [str(library)]},
        )
    )

    assert result.status == "partial"
    assert result.reason_code == "MEDIA_CORPUS_ROOT_HANDOFF_READY"
    assert result.safe_to_continue is True
    assert result.files_selected == 0
    assert result.files_read == 0
    assert result.partial_readiness is not None
    assert result.partial_readiness["safe_to_continue_to_artifact_runtime"] is True
    assert "MEDIA_CORPUS_ROOT_HANDOFF_READY" in result.partial_readiness["reason_codes"]
    assert result.corpus_handoff is not None
    assert result.corpus_handoff["artifact_runtime_allowed"] is True
    assert result.corpus_handoff["source_reading_required"] is False
    assert result.corpus_handoff["inventory_eligible_entities_count"] == 2
    assert result.file_selection_plan is not None
    assert result.file_selection_plan["source_rejected_inventory_eligible_count"] == 2


def test_project_analysis_does_not_treat_extension_hint_as_metadata_truth(tmp_path):
    library = tmp_path / "library"
    library.mkdir()
    (library / "track_one.m4a").write_bytes(b"media")

    result = ProjectAnalysisService().analyze_project(
        ProjectAnalysisRequest(
            workspace=str(library),
            prompt="Inventariar corpus de audio sem inferir metadata final.",
            workspace_context={"library_roots": [str(library)]},
        )
    )

    assert result.corpus_handoff is not None
    assert "extension_used_only_as_capability_routing_hint" in result.corpus_handoff["limitations"]
    assert "codec" not in result.corpus_handoff
    assert "container" not in result.corpus_handoff
