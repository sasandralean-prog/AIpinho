from __future__ import annotations

from pathlib import Path

from aipinho.services.artifacts.observed_entity_compilation_service import ObservedEntityCompilationService
from aipinho.services.governance.runtime.readonly_analysis_artifact_runtime_service import (
    Phase1RuntimeBudget,
    ReadonlyAnalysisArtifactRuntimeService,
)
from aipinho.services.runtime.task_runtime_service import TaskRuntimeService
from tests.support.runtime_fixtures import runtime_run


FIELDS = ["entity_id", "filename", "extension", "evidence_ref", "validation_status"]


def test_csv_render_emits_cardinality_chain_and_stable_digests(tmp_path: Path, task_runtime_store) -> None:
    project = tmp_path / "app"
    library = tmp_path / "library"
    project.mkdir()
    library.mkdir()
    for index in range(4):
        (library / f"Track{index}.any").write_text("media", encoding="utf-8")
    observed = ObservedEntityCompilationService()
    graph = observed.compile(
        workspace=str(project),
        workspace_context={"project_root": str(project), "library_roots": [str(library)]},
    ).model_dump(mode="json")
    run = runtime_run(status="running")
    task_runtime_store.create_run(run)
    runtime = TaskRuntimeService(store=task_runtime_store)
    service = ReadonlyAnalysisArtifactRuntimeService(
        runtime=runtime,
        observed_entities=observed,
        budget=Phase1RuntimeBudget(max_artifact_entities=10),
    )

    service._contract_tabular_collection_content(
        expected_schema=FIELDS,
        request_text="Inventariar biblioteca com evidencia.",
        run_id=run.run_id,
        analysis_payload={"observed_entity_graph": graph},
        declared_contract={
            "task_run_id": run.run_id,
            "artifact_logical_path": "reports/generic_inventory.csv",
            "contract_id": "media_corpus_inventory_artifact",
            "expected_kind": "tabular_collection",
            "expected_schema": FIELDS,
            "workspace_context": {"project_root": str(project), "library_roots": [str(library)]},
        },
    )

    checkpoints = [
        event.metadata
        for event in task_runtime_store.get_events(run.run_id)
        if event.type == "artifact_render_checkpoint"
    ]
    row_binding = next(item for item in checkpoints if item.get("stage") == "after_row_binding")

    assert row_binding["source_input_entity_count"] == 4
    assert row_binding["projected_entity_count"] == 4
    assert row_binding["row_model_accepted_count"] == 4
    assert row_binding["csv_rows_expected_at_stream_start"] == 4
    assert row_binding["csv_rows_written"] == 4
    assert row_binding["csv_cells_expected"] == 20
    assert row_binding["csv_cells_written"] == 20
    assert len(row_binding["input_entity_set_digest"]) == 64
    assert len(row_binding["row_model_digest"]) == 64
    assert len(row_binding["render_order_digest"]) == 64
    assert row_binding["progress_semantics"] == "completed"
