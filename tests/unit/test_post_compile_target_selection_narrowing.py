from __future__ import annotations

from aipinho.schemas.artifacts.contract_perception import ObservationPlan

from tests.unit.test_post_compile_applicability_admission_control import (
    _AdmissionAdapter,
    _plan,
    _stage,
    _task,
)


def test_eligible_media_candidate_is_not_starved_behind_expected_inapplicable_sidecars() -> None:
    adapter = _AdmissionAdapter()
    sidecar_ids = [f"sidecar_{index}" for index in range(6000)]
    entity_ids = [*sidecar_ids, "track_1"]
    selected_entities = [
        {"entity_id": entity_id, "path": f"library/{entity_id}.lrc", "entity_kind": "file"}
        for entity_id in sidecar_ids
    ] + [{"entity_id": "track_1", "path": "library/song.m4a", "entity_kind": "file"}]
    checkpoints: list[str] = []

    result = _stage(adapter).execute(
        observation_plan=_plan([_task("artist", entity_ids), _task("track_title", entity_ids)]),
        selected_entities=selected_entities,
        checkpoint=lambda stage, _: checkpoints.append(stage),
    )

    planning = result.telemetry["observation_group_planning"]
    assert result.blocked_reason_code is None
    assert result.telemetry["groups_created_count"] == 1
    assert result.telemetry["physical_probe_count"] == 1
    assert result.telemetry["eligible_candidate_count"] == 2
    assert result.telemetry["expected_inapplicable_candidate_count"] == 12000
    assert result.telemetry["systemic_execution_failure_count"] == 0
    assert planning["target_entity_ref_count"] == 12002
    assert planning["target_entity_source_breakdown"] == {"entity_ref": 12002}
    assert "before_physical_probe_dispatch" in checkpoints
    assert adapter.execute_calls[0].inputs["file_path"] == "library/song.m4a"


def test_no_eligible_media_candidates_blocks_with_target_selection_reason() -> None:
    adapter = _AdmissionAdapter()
    entity_ids = [f"sidecar_{index}" for index in range(120)]
    selected_entities = [
        {"entity_id": entity_id, "path": f"library/{entity_id}.lrc", "entity_kind": "file"}
        for entity_id in entity_ids
    ]

    result = _stage(adapter).execute(
        observation_plan=_plan([_task("artist", entity_ids)]),
        selected_entities=selected_entities,
    )

    assert result.blocked_reason_code == "POST_COMPILE_TARGET_SELECTION_NO_ELIGIBLE_MEDIA_CANDIDATES"
    assert result.telemetry["physical_probe_count"] == 0
    assert result.telemetry["groups_created_count"] == 0
    assert result.telemetry["expected_inapplicable_candidate_count"] == 120
    assert result.telemetry["target_entity_source_breakdown"] == {"entity_ref": 120}
    assert result.telemetry["systemic_execution_failure_count"] == 0


def test_target_entity_source_provenance_reports_task_inputs_when_entity_ref_is_empty() -> None:
    adapter = _AdmissionAdapter()
    task = _task("artist", ["track_1"]).model_copy(update={"entity_ref": {}})

    result = _stage(adapter).execute(
        observation_plan=ObservationPlan(
            observation_strategies=_plan([task]).observation_strategies,
            observation_tasks=[task],
        ),
        selected_entities=[{"entity_id": "track_1", "path": "library/song.m4a", "entity_kind": "file"}],
    )

    planning = result.telemetry["observation_group_planning"]
    assert result.telemetry["physical_probe_count"] == 1
    assert planning["target_entity_source_breakdown"] == {"task_inputs": 1}
    assert planning["target_selection_tasks"][0]["target_entity_source"] == "task_inputs"
