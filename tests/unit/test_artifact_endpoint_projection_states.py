from __future__ import annotations

from aipinho.schemas.runtime.task_run_result import TaskRunResult
from aipinho.services.runtime.universal_task_session_service import UniversalTaskSessionService
from tests.support.runtime_fixtures import runtime_run


class _ArtifactIndex:
    def __init__(self, rows):
        self.rows = rows

    def by_task(self, task_id, *, limit=200):
        return list(self.rows)

    def get(self, artifact_id):
        return next((row for row in self.rows if row.get("artifact_id") == artifact_id), None)


def test_artifact_endpoint_projects_blocked_music_inventory_state(task_runtime_store) -> None:
    run = runtime_run(status="blocked")
    task_runtime_store.create_run(run)
    task_runtime_store.save_result(
        run.run_id,
        TaskRunResult(
            run_id=run.run_id,
            status="blocked",
            summary="artifact blocked",
            outputs={
                "artifact_result": {
                    "artifact_state": {
                        "status": "partial",
                        "count": 1,
                        "safe_to_use": False,
                        "reason_code": "MUSIC_INVENTORY_SEMANTIC_EVIDENCE_INSUFFICIENT",
                    },
                    "artifacts": [
                        {
                            "logical_path": "reports/media/inventory.csv",
                            "status": "blocked",
                            "semantic_contract_status": "insufficient",
                            "reason_code": "MUSIC_INVENTORY_SEMANTIC_EVIDENCE_INSUFFICIENT",
                            "limitations": ["media inventory semantic evidence insufficient"],
                            "safe_to_use": False,
                            "expected_rows": 5,
                            "selected_rows": 2,
                            "bound_rows": 1,
                            "evidence_ref_count": 1,
                            "visible_in_endpoint": True,
                        }
                    ],
                }
            },
        ),
    )

    payload = UniversalTaskSessionService(store=task_runtime_store).artifacts_for_run(run.run_id)

    assert payload is not None
    assert payload["artifact_state"]["status"] == "partial"
    assert payload["artifact_state"]["reason_code"] == "MUSIC_INVENTORY_SEMANTIC_EVIDENCE_INSUFFICIENT"
    assert payload["artifacts"][0]["status"] == "blocked"
    assert payload["artifacts"][0]["semantic_contract_status"] == "insufficient"
    assert payload["artifacts"][0]["safe_to_use"] is False
    assert payload["artifacts"][0]["expected_rows"] == 5
    assert payload["artifacts"][0]["selected_rows"] == 2
    assert payload["artifacts"][0]["bound_rows"] == 1
    assert payload["artifacts"][0]["evidence_ref_count"] == 1


def test_artifact_endpoint_prefers_runtime_semantic_state_over_ready_index_row(task_runtime_store) -> None:
    run = runtime_run(status="blocked")
    task_runtime_store.create_run(run)
    artifact_id = "artifact_semantic_blocked"
    task_runtime_store.save_result(
        run.run_id,
        TaskRunResult(
            run_id=run.run_id,
            status="blocked",
            summary="artifact blocked by semantic contract",
            outputs={
                "artifact_result": {
                    "artifacts": [
                        {
                            "artifact_id": artifact_id,
                            "logical_path": "reports/media/inventory.csv",
                            "status": "blocked",
                            "validation_status": "blocked",
                            "semantic_contract_status": "insufficient",
                            "reason_code": "MUSIC_INVENTORY_SEMANTIC_EVIDENCE_INSUFFICIENT",
                            "safe_to_use": False,
                        }
                    ]
                }
            },
        ),
    )
    service = UniversalTaskSessionService(
        store=task_runtime_store,
        artifacts=_ArtifactIndex(
            [
                {
                    "artifact_id": artifact_id,
                    "logical_path": "reports/media/inventory.csv",
                    "status": "ready",
                    "validation_status": "blocked",
                    "source": "artifact_index",
                }
            ]
        ),
    )

    payload = service.artifacts_for_run(run.run_id)

    assert payload is not None
    row = payload["artifacts"][0]
    assert row["status"] == "blocked"
    assert row["validation_status"] == "blocked"
    assert row["semantic_contract_status"] == "insufficient"
    assert row["safe_to_use"] is False
    assert payload["artifact_state"]["status"] == "partial"
