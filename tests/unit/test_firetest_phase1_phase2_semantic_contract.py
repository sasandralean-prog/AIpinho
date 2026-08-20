from __future__ import annotations

import csv
import io

from aipinho.services.artifacts.artifact_semantic_contract_service import ArtifactSemanticContractService
from aipinho.services.governance.runtime.readonly_analysis_artifact_runtime_service import (
    ReadonlyAnalysisArtifactRuntimeService,
)

from tests.unit.test_media_relationship_foundation import _entity, _graph


def _header(content: str) -> list[str]:
    return list(csv.reader(io.StringIO(content)).__next__())


def test_media_inventory_contract_is_generic_and_declares_observation_visibility() -> None:
    contract = ArtifactSemanticContractService().compile_contract(
        logical_path="reports/media/corpus_inventory.csv",
        content_type="text/csv",
    )

    assert contract["contract_id"] == "media_corpus_inventory_artifact"
    assert "entity_id" in contract["expected_schema"]
    assert "evidence_ref" in contract["expected_schema"]
    assert contract["expected_semantics"]["media_corpus_inventory_required"] is True
    assert contract["expected_semantics"]["relationship_candidates_optional"] is True
    assert contract["relationship_goal"]["truth_policy"]["truth_eligible"] is False


def test_phase1_media_inventory_materialization_uses_contract_schema_not_findings_fallback() -> None:
    runtime = ReadonlyAnalysisArtifactRuntimeService()
    contract = runtime.artifact_semantic_contracts.compile_contract(
        logical_path="reports/media/corpus_inventory.csv",
        content_type="text/csv",
    )
    graph = _graph(
        _entity("track", "album/song.media", role="media_asset_candidate"),
        _entity("text", "album/song.text", role="text_sidecar_candidate"),
    )

    render = runtime._contract_tabular_collection_content(  # noqa: SLF001 - artifact semantic contract slice
        expected_schema=contract["expected_schema"],
        analysis_payload={"observed_entity_graph": graph},
        declared_contract={
            **contract,
            "artifact_logical_path": "reports/media/corpus_inventory.csv",
            "task_run_id": "task_run_semantic_contract",
            "entity_selection_contract": {"allowed_root_roles": ["library_root"]},
        },
        run_id="task_run_semantic_contract",
    )

    header = _header(render.content)
    assert header[:3] == ["entity_id", "source_root_role", "relative_path"]
    assert header != ["severity", "title", "summary"]
    assert "metadata_status" in header
    assert "relationship_candidate_refs" in header
    assert render.entity_summary["perception"]["media_metadata_capability"]["status"] in {
        "available",
        "partial",
        "blocked",
        "not_configured",
        "missing_dependency",
        "not_observed_in_this_run",
        "configured_but_deferred",
        "unknown_due_to_payload_ref",
    }
    assert render.entity_summary["perception"]["relationship_rendering"]["truth_eligible"] is False


def test_rendered_media_inventory_with_unavailable_metadata_is_not_semantic_success() -> None:
    runtime = ReadonlyAnalysisArtifactRuntimeService()
    contract = runtime.artifact_semantic_contracts.compile_contract(
        logical_path="reports/media/corpus_inventory.csv",
        content_type="text/csv",
    )
    graph = _graph(_entity("track", "album/song.media", role="media_asset_candidate"))

    render = runtime._contract_tabular_collection_content(  # noqa: SLF001 - artifact semantic contract slice
        expected_schema=contract["expected_schema"],
        analysis_payload={"observed_entity_graph": graph},
        declared_contract={
            **contract,
            "artifact_logical_path": "reports/media/corpus_inventory.csv",
            "task_run_id": "task_run_semantic_contract",
            "entity_selection_contract": {"allowed_root_roles": ["library_root"]},
        },
        run_id="task_run_semantic_contract",
    )
    result = runtime.artifact_semantic_contracts.validate(
        logical_path="reports/media/corpus_inventory.csv",
        content_type="text/csv",
        declared_contract=contract,
        content=render.content,
    )

    assert result.status == "blocked"
    assert "media_inventory_metadata_capability_unavailable" in result.missing_requirements
