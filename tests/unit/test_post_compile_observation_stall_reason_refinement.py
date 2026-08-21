from __future__ import annotations

from aipinho.services.governance.runtime.readonly_analysis_artifact_runtime_service import _MEDIA_INVENTORY_STAGE_STALL_REASONS as SERVICE_REASONS
from aipinho.services.runtime.task_run_store import _MEDIA_INVENTORY_STAGE_STALL_REASONS as STORE_REASONS


def test_post_compile_dark_zone_checkpoints_have_specific_stall_reasons() -> None:
    expected = {
        "before_observation_physical_group_planning": "POST_COMPILE_OBSERVATION_GROUP_PLANNING_STALLED",
        "observation_task_scan_checkpoint": "POST_COMPILE_OBSERVATION_TASK_SCAN_STALLED",
        "before_capability_applicability_resolution": "POST_COMPILE_CAPABILITY_APPLICABILITY_RESOLUTION_STALLED",
        "capability_applicability_resolution_checkpoint": "POST_COMPILE_CAPABILITY_APPLICABILITY_RESOLUTION_STALLED",
        "before_backend_availability_snapshot": "POST_COMPILE_BACKEND_AVAILABILITY_SNAPSHOT_STALLED",
        "after_backend_availability_snapshot": "POST_COMPILE_PHYSICAL_PROBE_DISPATCH_STALLED",
        "before_physical_probe_dispatch": "POST_COMPILE_PHYSICAL_PROBE_DISPATCH_STALLED",
    }
    for stage, reason in expected.items():
        assert SERVICE_REASONS[stage] == reason
        assert STORE_REASONS[stage] == reason


def test_generic_post_compile_stall_is_no_longer_the_only_grouping_reason() -> None:
    assert SERVICE_REASONS["before_post_compile_observation_execution"] == "POST_COMPILE_OBSERVATION_GROUP_PLANNING_STALLED"
    assert STORE_REASONS["before_post_compile_observation_execution"] == "POST_COMPILE_OBSERVATION_GROUP_PLANNING_STALLED"

