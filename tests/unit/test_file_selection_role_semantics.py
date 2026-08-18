from __future__ import annotations

from aipinho.schemas.analysis.file_selection import FileSelectionRequest
from aipinho.services.analysis.file_selection_service import FileSelectionService


def test_media_file_rejected_for_source_reading_can_be_inventory_eligible(tmp_path):
    library = tmp_path / "library"
    library.mkdir()
    (library / "sample.m4a").write_bytes(b"media")

    result = FileSelectionService().select_files(
        FileSelectionRequest(
            workspace=str(library),
            semantic_query="inventariar biblioteca de musicas",
            root_role="library_root",
            candidate_files=["sample.m4a"],
        )
    )

    assert result.status == "partial"
    assert result.selected_files == []
    assert result.omitted_files[0].blocked_reason == "EXTENSION_NOT_ALLOWED_FOR_SOURCE_READING"
    assert result.omitted_files[0].inventory_eligible is True
    assert result.omitted_files[0].entity_role == "media_asset_candidate"
    assert result.omitted_files[0].routing_hints == ["media_metadata_observation"]
    assert result.plan is not None
    assert result.plan["inventory_eligible_entities_count"] == 1
    assert result.plan["source_readable_selected_count"] == 0
    assert "MEDIA_CORPUS_ROOT_HANDOFF_READY" in result.plan["selection_reason_codes"]


def test_source_project_keeps_media_file_as_text_read_rejection_not_inventory(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    (project / "sample.m4a").write_bytes(b"media")

    result = FileSelectionService().select_files(
        FileSelectionRequest(
            workspace=str(project),
            semantic_query="analise o projeto",
            root_role="source_project",
            candidate_files=["sample.m4a"],
        )
    )

    assert result.status == "blocked"
    assert result.selected_files == []
    assert result.omitted_files[0].blocked_reason == "extension_not_allowed"
    assert result.omitted_files[0].inventory_eligible is False
    assert result.plan is not None
    assert result.plan["inventory_eligible_entities_count"] == 0
