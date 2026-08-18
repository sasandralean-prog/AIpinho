from aipinho.schemas.runtime.task_run_result import TaskRunResult
from aipinho.services.runtime.universal_task_session_service import UniversalTaskSessionService


def test_task_run_result_has_canonical_top_level_reason_code() -> None:
    result = TaskRunResult(
        run_id="task_run_generic",
        status="blocked",
        reason_code="PERCEPTION_FACT_SOURCE_BINDING_STALLED",
        summary="blocked",
        validation={"status": "blocked", "reason_code": "OLDER_VALIDATION_REASON"},
    )

    assert result.reason_code == "PERCEPTION_FACT_SOURCE_BINDING_STALLED"
    assert UniversalTaskSessionService()._result_block_reason_code(result) == "PERCEPTION_FACT_SOURCE_BINDING_STALLED"
