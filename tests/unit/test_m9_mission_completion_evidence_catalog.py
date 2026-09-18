from __future__ import annotations

from types import SimpleNamespace

from aipinho.schemas.runtime.mission_completion import (
    MissionCompletionSnapshot,
)
from aipinho.services.runtime.mission_completion_evidence_catalog_service import (
    MissionCompletionEvidenceCatalogService,
)


class _Outcomes:
    def __init__(self, rows):
        self.rows = list(rows)

    def list_for_mission(self, *, mission_id: str, limit: int = 1000):
        return list(self.rows)[:limit]


def _snapshot():
    return MissionCompletionSnapshot(
        mission_id="mission_catalog",
        status="ready",
        completion_requirements=["validated_change"],
        validation_requirements=["tests_pass"],
        task_run_ids=["task_run_a", "task_run_b"],
        terminal_task_run_ids=["task_run_a", "task_run_b"],
        phase_outcome_run_ids=["task_run_a", "task_run_b"],
        phase_outcome_authority_sha256s=["a" * 64, "b" * 64],
        evidence_refs=[
            "task_run:task_run_a",
            "artifact_patch",
            "evidence:tests",
        ],
        authority_sha256="c" * 64,
    )


def _outcome(
    run_id,
    *,
    phase_id,
    authority_sha,
    evidence_refs,
    safe=True,
    limitations=None,
):
    return SimpleNamespace(
        producer_task_run_id=run_id,
        phase_id=phase_id,
        authority_sha256=authority_sha,
        runtime_status="completed",
        result_status="completed",
        reason_code=None,
        semantic_properties={
            "runtime_truth_status": "completed",
            "runtime_truth_safe_to_report_success": safe,
        },
        phase_dependency={"status": "satisfied"},
        limitations=list(limitations or []),
        missing_truth=[],
        use_safety={"safe_for_truth_claim": safe},
        evidence_refs=list(evidence_refs),
        artifacts=[
            {
                "artifact_id": "artifact_patch",
                "logical_path": "src/example.py",
                "status": "completed",
                "validation_status": "passed",
                "evidence_refs": ["evidence:patch"],
                "content": "must_not_enter_catalog",
                "metadata": {
                    "producer_step": "apply_patch",
                    "raw": "must_not_enter_catalog",
                },
            }
        ],
    )


def test_catalog_is_stable_and_does_not_copy_raw_artifact_payloads() -> None:
    snapshot = _snapshot()
    first_outcome = _outcome(
        "task_run_a",
        phase_id="implementation",
        authority_sha="a" * 64,
        evidence_refs=["task_run:task_run_a", "artifact_patch"],
    )
    second_outcome = _outcome(
        "task_run_b",
        phase_id="validation",
        authority_sha="b" * 64,
        evidence_refs=["evidence:tests"],
        limitations=["coverage_limited"],
    )

    first = MissionCompletionEvidenceCatalogService(
        outcomes=_Outcomes([second_outcome, first_outcome]),  # type: ignore[arg-type]
    ).build(snapshot)
    restarted = MissionCompletionEvidenceCatalogService(
        outcomes=_Outcomes([first_outcome, second_outcome]),  # type: ignore[arg-type]
    ).build(snapshot)

    assert first.authority_sha256 == restarted.authority_sha256
    assert first.model_dump() == restarted.model_dump()
    assert [item.producer_task_run_id for item in first.items] == [
        "task_run_a",
        "task_run_a",
        "task_run_b",
    ]
    serialized = str(first.model_dump())
    assert "must_not_enter_catalog" not in serialized
    assert first.items[0].artifact_descriptors[0]["logical_path"] == "src/example.py"


def test_catalog_excludes_outcomes_outside_snapshot_authority() -> None:
    snapshot = _snapshot()
    valid = _outcome(
        "task_run_a",
        phase_id="implementation",
        authority_sha="a" * 64,
        evidence_refs=["artifact_patch"],
    )
    foreign = _outcome(
        "task_run_b",
        phase_id="validation",
        authority_sha="f" * 64,
        evidence_refs=["evidence:forged"],
    )

    catalog = MissionCompletionEvidenceCatalogService(
        outcomes=_Outcomes([valid, foreign]),  # type: ignore[arg-type]
    ).build(snapshot)

    assert [item.evidence_ref for item in catalog.items] == ["artifact_patch"]
    assert "evidence:forged" not in {
        item.evidence_ref for item in catalog.items
    }
