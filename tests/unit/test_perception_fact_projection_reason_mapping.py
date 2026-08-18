from aipinho.services.governance.runtime.readonly_analysis_artifact_runtime_service import (
    _MEDIA_INVENTORY_STAGE_STALL_REASONS as RUNTIME_STAGE_REASONS,
)
from aipinho.services.runtime.task_run_store import (
    _MEDIA_INVENTORY_STAGE_STALL_REASONS as STORE_STAGE_REASONS,
)


def test_fact_projection_substage_reason_mapping_is_generic() -> None:
    expected = {
        "before_fact_source_binding": "PERCEPTION_FACT_SOURCE_BINDING_STALLED",
        "before_fact_candidate_projection": "PERCEPTION_FACT_CANDIDATE_PROJECTION_STALLED",
        "before_fact_derivation": "PERCEPTION_FACT_DERIVATION_STALLED",
        "before_fact_provenance_binding": "PERCEPTION_FACT_PROVENANCE_BINDING_STALLED",
        "before_fact_deduplication": "PERCEPTION_FACT_DEDUPLICATION_STALLED",
        "before_fact_validation_projection": "PERCEPTION_FACT_VALIDATION_PROJECTION_STALLED",
    }

    for stage, reason in expected.items():
        assert RUNTIME_STAGE_REASONS[stage] == reason
        assert STORE_STAGE_REASONS[stage] == reason
        assert not reason.startswith("MUSIC_")
