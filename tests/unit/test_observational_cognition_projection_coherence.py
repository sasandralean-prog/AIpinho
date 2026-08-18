from aipinho.schemas.runtime.task_run_result import TaskRunResult
from aipinho.services.runtime.universal_task_session_service import UniversalTaskSessionService
from tests.support.runtime_fixtures import runtime_run


def test_summary_uses_row_evidence_projection_without_payload_hydration(task_runtime_store) -> None:
    run = runtime_run(status="blocked")
    task_runtime_store.create_run(run)
    task_runtime_store.save_result(
        run.run_id,
        TaskRunResult(
            run_id=run.run_id,
            status="blocked",
            summary="semantic partial",
            outputs={
                "artifact_result": {
                    "artifacts": [
                        {
                            "artifact_id": "artifact_inventory",
                            "logical_path": "reports/corpus/inventory.csv",
                            "status": "partial",
                            "reason_code": "MUSIC_INVENTORY_PARTIAL_EVIDENCE",
                            "selected_rows": 2,
                            "bound_rows": 2,
                            "evidence_ref_count": 2,
                            "row_evidence_coverage": {"status": "satisfied", "evidence_ref_count": 2},
                            "row_validation_summary": {
                                "row_count": 2,
                                "value_counts_by_column": {
                                    "entity_id": 2,
                                    "source_root_role": 2,
                                    "evidence_ref": 2,
                                },
                            },
                        }
                    ]
                }
            },
        ),
    )

    summary = UniversalTaskSessionService(store=task_runtime_store).summary(run.run_id)

    assert summary is not None
    assert summary["finished_at"] is not None
    cognition = summary["observational_cognition"]
    assert cognition["status"] == "blocked"
    assert cognition["evidence"]["total_bound_observations"] >= 2
    assert cognition["evidence"]["by_attribute"]["entity_id"] == 2
    assert cognition["observation_goals"]["total"] >= 1
