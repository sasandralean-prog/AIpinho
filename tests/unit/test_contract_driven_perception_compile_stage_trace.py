from pathlib import Path

from aipinho.schemas.artifacts.contract_perception import ObservationCapability
from aipinho.services.artifacts.contract_driven_perception_service import (
    CapabilityRegistry,
    ContractDrivenPerceptionService,
)
from aipinho.services.artifacts.observed_entity_compilation_service import ObservedEntityCompilationService


def _observed_entity_service() -> ObservedEntityCompilationService:
    return ObservedEntityCompilationService(
        policy={
            "max_files": 1000,
            "max_bytes_per_file": 128,
            "include_extensions": [".txt", ".dat", ".bin"],
        }
    )


def _graph(tmp_path: Path, *, count: int = 3, with_paths: bool = True) -> tuple[ObservedEntityCompilationService, dict]:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    for index in range(count):
        name = f"entity_{index}.dat" if with_paths else f"entity_{index}.txt"
        (workspace / name).write_text(f"value {index}", encoding="utf-8")
    observed = _observed_entity_service()
    return observed, observed.compile(workspace=str(workspace)).model_dump(mode="json")


def test_compile_emits_generic_bounded_stage_trace(tmp_path: Path) -> None:
    observed, graph = _graph(tmp_path, count=2)
    seen: list[dict] = []
    service = ContractDrivenPerceptionService(observed_entities=observed)

    result = service.compile(
        graph=graph,
        declared_contract={
            "expected_kind": "tabular_collection",
            "expected_schema": ["name", "extension"],
            "perception_compile_policy": {"mode": "compile_only", "execute_observers": False},
        },
        stage_observer=seen.append,
    )

    stages = [item["stage"] for item in result.compile_stage_trace]
    assert stages[:2] == ["before_compile_request_normalization", "after_compile_request_normalization"]
    assert "before_requirement_resolution" in stages
    assert "after_entity_projection" in stages
    assert "before_observation_binding" in stages
    assert "after_payload_bound_check" in stages
    assert stages[-1] == "perception_compile_completed"
    assert seen
    assert all(item.get("bounded") is True for item in seen)
    assert all("entities" not in item and "rows" not in item for item in seen)
    assert 0 < result.payload_metrics["projected_entity_count"] <= 2
    assert result.compile_policy["mode"] == "compile_only"


def test_compile_only_defers_observer_execution_without_calling_filesystem_probe(tmp_path: Path) -> None:
    observed, graph = _graph(tmp_path, count=4)
    registry = CapabilityRegistry(
        capabilities=[
            ObservationCapability(
                capability_id="generic_declared_probe",
                name="Generic declared probe",
                observable_attributes=["external_signal"],
                compatible_entity_kinds=["file"],
                supported_strategies=["execute_observer"],
                typical_confidence=0.8,
            )
        ]
    )
    service = ContractDrivenPerceptionService(observed_entities=observed, observer_registry=registry)

    def _fail_execute(**_: object) -> object:
        raise AssertionError("compiler must not execute observer in compile_only mode")

    service.observation_boundary.execute = _fail_execute  # type: ignore[method-assign]
    result = service.compile(
        graph=graph,
        declared_contract={
            "expected_kind": "tabular_collection",
            "expected_schema": ["external_signal"],
            "perception_compile_policy": {"mode": "compile_only", "execute_observers": False},
        },
    )

    assert result.observation_execution_results == []
    assert result.observation_plan.observation_tasks[0].status == "PLANNED"
    assert result.observation_plan.requirements[0].gap_reason == "OBSERVER_EXECUTION_DEFERRED_BY_COMPILE_POLICY"
    assert result.semantic_coverage_report.is_semantically_complete is False


def test_payload_bound_exceeded_blocks_with_generic_internal_reason(tmp_path: Path) -> None:
    observed, graph = _graph(tmp_path, count=12)
    service = ContractDrivenPerceptionService(observed_entities=observed)

    result = service.compile(
        graph=graph,
        declared_contract={
            "expected_kind": "tabular_collection",
            "expected_schema": ["name", "extension", "size_bytes"],
            "perception_compile_policy": {
                "mode": "compile_only",
                "execute_observers": False,
                "max_payload_items": 1,
            },
        },
    )

    assert result.internal_reason_code == "PERCEPTION_PAYLOAD_BOUND_EXCEEDED"
    assert result.payload_metrics["bound_status"] == "blocked"
    assert result.payload_metrics["payload_item_count"] > 1
    assert result.semantic_self_review.can_speaker_claim is False


def test_compile_handles_generic_entities_without_media_specific_authority(tmp_path: Path) -> None:
    observed, graph = _graph(tmp_path, count=3, with_paths=False)
    service = ContractDrivenPerceptionService(observed_entities=observed)

    result = service.compile(
        graph=graph,
        declared_contract={
            "expected_kind": "tabular_collection",
            "expected_schema": ["name", "size_bytes"],
            "perception_compile_policy": {"mode": "compile_only"},
        },
    )

    assert result.candidate_entity_set.selected_entity_ids
    assert result.media_metadata_capability["status"] == "configured_but_deferred"
    assert result.media_metadata_capability["execution_status"] == "deferred"
    assert result.media_metadata_capability["files_attempted"] == 0
    assert result.relationship_summary["truth_eligible"] is False
    assert result.internal_reason_code is None
