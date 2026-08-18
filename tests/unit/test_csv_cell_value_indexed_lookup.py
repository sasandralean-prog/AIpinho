from __future__ import annotations

from pathlib import Path
from typing import Any

from aipinho.services.artifacts.observed_entity_compilation_service import ObservedEntityCompilationService
from aipinho.services.governance.runtime.readonly_analysis_artifact_runtime_service import (
    Phase1RuntimeBudget,
    ReadonlyAnalysisArtifactRuntimeService,
)
from aipinho.services.runtime.task_runtime_service import TaskRuntimeService
from tests.support.runtime_fixtures import runtime_run


class CountingList(list):
    def __init__(self, values: list[dict[str, Any]]) -> None:
        super().__init__(values)
        self.iteration_count = 0

    def __iter__(self):
        self.iteration_count += 1
        return super().__iter__()


def _metadata_payload(entity_count: int, attributes_per_entity: int) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    observations: list[dict[str, Any]] = []
    selected_entities: list[dict[str, Any]] = []
    for entity_index in range(entity_count):
        entity_id = f"entity-{entity_index}"
        selected_entities.append({"entity_id": entity_id})
        for attribute_index in range(attributes_per_entity):
            observations.append(
                {
                    "entity_id": entity_id,
                    "capability_id": "media_metadata_reader",
                    "canonical_key": f"attribute_{attribute_index}",
                    "attribute_name": f"attribute_{attribute_index}",
                    "observation_state": "missing",
                }
            )
    return {"attribute_observations": observations}, selected_entities


def test_indexed_metadata_lookup_matches_reference_semantics() -> None:
    service = ReadonlyAnalysisArtifactRuntimeService()
    payload, selected_entities = _metadata_payload(entity_count=12, attributes_per_entity=8)
    payload["attribute_observations"][0]["observation_state"] = "observed"
    payload["attribute_observations"][0]["canonical_key"] = "codec"
    payload["attribute_observations"][0]["observed_value"] = "observed-codec"
    payload["attribute_observations"][0]["provenance"] = {"backend_id": "governed_backend"}
    context = service._build_csv_cell_lookup_context(
        perception_payload=payload,
        selected_entities=selected_entities,
        render_columns=[
            {"canonical_key": "metadata_status"},
            {"canonical_key": "metadata_source"},
            {"canonical_key": "probe_status"},
        ],
    )

    for entity in selected_entities:
        assert service._metadata_status_for_entity(entity, perception_payload=payload, lookup_context=context) == service._metadata_status_for_entity(entity, perception_payload=payload)
        assert service._metadata_source_for_entity(entity, perception_payload=payload, lookup_context=context) == service._metadata_source_for_entity(entity, perception_payload=payload)
        assert service._metadata_probe_status_for_entity(entity, perception_payload=payload, lookup_context=context) == service._metadata_probe_status_for_entity(entity, perception_payload=payload)


def test_indexed_metadata_lookup_does_not_rescan_observation_list() -> None:
    service = ReadonlyAnalysisArtifactRuntimeService()
    payload, selected_entities = _metadata_payload(entity_count=20, attributes_per_entity=5)
    payload["attribute_observations"] = CountingList(payload["attribute_observations"])
    context = service._build_csv_cell_lookup_context(
        perception_payload=payload,
        selected_entities=selected_entities,
        render_columns=[
            {"canonical_key": "metadata_status"},
            {"canonical_key": "metadata_source"},
            {"canonical_key": "probe_status"},
        ],
    )
    payload["attribute_observations"].iteration_count = 0

    for entity in selected_entities:
        service._metadata_status_for_entity(entity, perception_payload=payload, lookup_context=context)
        service._metadata_source_for_entity(entity, perception_payload=payload, lookup_context=context)
        service._metadata_probe_status_for_entity(entity, perception_payload=payload, lookup_context=context)

    assert payload["attribute_observations"].iteration_count == 0

    service._metadata_status_for_entity(selected_entities[0], perception_payload=payload)
    assert payload["attribute_observations"].iteration_count > 0


def test_csv_render_emits_bounded_lookup_metrics_and_column_cost(tmp_path: Path, task_runtime_store) -> None:
    project = tmp_path / "app"
    library = tmp_path / "library"
    project.mkdir()
    library.mkdir()
    for index in range(3):
        (library / f"Track{index}.any").write_text("media", encoding="utf-8")
    observed = ObservedEntityCompilationService()
    graph = observed.compile(
        workspace=str(project),
        workspace_context={"project_root": str(project), "library_roots": [str(library)]},
    ).model_dump(mode="json")
    run = runtime_run(status="running")
    task_runtime_store.create_run(run)
    service = ReadonlyAnalysisArtifactRuntimeService(
        runtime=TaskRuntimeService(store=task_runtime_store),
        observed_entities=observed,
        budget=Phase1RuntimeBudget(max_artifact_entities=10),
    )
    fields = ["entity_id", "filename", "metadata_status", "metadata_source", "probe_status", "evidence_ref"]

    service._contract_tabular_collection_content(
        expected_schema=fields,
        request_text="Inventariar biblioteca generica com evidencia.",
        run_id=run.run_id,
        analysis_payload={"observed_entity_graph": graph},
        declared_contract={
            "task_run_id": run.run_id,
            "artifact_logical_path": "reports/generic_inventory.csv",
            "contract_id": "generic_tabular_collection_artifact",
            "expected_kind": "tabular_collection",
            "expected_schema": fields,
            "workspace_context": {"project_root": str(project), "library_roots": [str(library)]},
        },
    )

    checkpoints = [
        event.metadata
        for event in task_runtime_store.get_events(run.run_id)
        if event.type == "artifact_render_checkpoint"
    ]
    row_binding = next(item for item in checkpoints if item.get("stage") == "after_row_binding")

    assert row_binding["cell_value_lookup_count"] == row_binding["csv_cells_rendered"]
    assert row_binding["cell_normalization_count"] == row_binding["csv_cells_rendered"]
    assert row_binding["cell_fallback_scan_count"] >= 0
    assert row_binding["index_entry_count"] > 0
    assert isinstance(row_binding["column_cost_summary"], dict)
    assert row_binding["column_cost_summary"]["metadata_status"]["lookup_count"] == 3
    assert row_binding["csv_cell_serialization_elapsed_ms"] <= row_binding["csv_cell_render_elapsed_ms"]
