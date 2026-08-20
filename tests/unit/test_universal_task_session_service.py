from __future__ import annotations

from types import SimpleNamespace

from aipinho.schemas.runtime.task_completion import TaskCompletionEvaluation
from aipinho.schemas.runtime.task_run import TaskRun
from aipinho.schemas.runtime.task_run_event import TaskRunEvent
from aipinho.schemas.runtime.task_run_plan import TaskRunPlan
from aipinho.schemas.runtime.task_run_result import TaskRunResult
from aipinho.schemas.runtime.task_run_step import TaskRunStep
from aipinho.services.runtime.universal_task_session_service import UniversalTaskSessionService


class FakeApprovals:
    def __init__(self, approval=None):
        self.approval = approval

    def get_approval(self, approval_id):
        return self.approval


class FakeArtifacts:
    def __init__(self, records=None):
        self.records = records or {}

    def by_task(self, task_id, *, limit=200):
        return []

    def get(self, artifact_id):
        return self.records.get(artifact_id)


def _run(run_id: str = "task_run_11111111111111111111111111111111", *, status: str = "created") -> TaskRun:
    return TaskRun(
        run_id=run_id,
        source_type="direct",
        session_id="chat_test",
        workspace=r"C:\Workspace\Project",
        contract_type="patch_request",
        operation_type="governed_file_write",
        runtime_profile="governed_patch",
        requested_actions=["write_files"],
        policy_snapshot={"approval_required_for": ["write_files"]},
        status=status,  # type: ignore[arg-type]
        plan=TaskRunPlan(
            plan_id="plan_test",
            contract_type="patch_request",
            steps=[
                TaskRunStep(step_id="step_01", step_type="planning", action="plan", status="completed"),
                TaskRunStep(step_id="step_02", step_type="write_file", action="write_files", status="pending"),
            ],
        ),
    )


def test_universal_task_session_uses_real_plan_progress(task_runtime_store):
    run = _run(status="running")
    task_runtime_store.create_run(run)
    service = UniversalTaskSessionService(
        store=task_runtime_store,
        approvals=FakeApprovals(),
        artifacts=FakeArtifacts(),
    )

    session = service.get_session(run.run_id)

    assert session is not None
    assert session.status == "RUNNING"
    assert session.progress.percent == 50
    assert session.progress.basis == "task_run_plan_steps"
    assert session.progress.is_estimated is False
    assert session.eta is None


def test_universal_task_session_completed_result_sets_completed_progress(task_runtime_store):
    run = _run(status="completed")
    task_runtime_store.create_run(run)
    task_runtime_store.save_result(
        run.run_id,
        TaskRunResult(
            run_id=run.run_id,
            status="completed",
            summary="done",
            completion=TaskCompletionEvaluation(
                status="completed",
                safe_to_report_success=True,
                expected_outcomes=["patch_result"],
                fulfilled_outcomes=["patch_result"],
            ),
        ),
    )
    service = UniversalTaskSessionService(
        store=task_runtime_store,
        approvals=FakeApprovals(),
        artifacts=FakeArtifacts(),
    )

    session = service.get_session(run.run_id)

    assert session is not None
    assert session.status == "COMPLETED"
    assert session.progress.percent == 100
    assert session.result_state.safe_to_report_success is True


def test_universal_task_session_exposes_pending_approval(task_runtime_store):
    run = _run(status="waiting_input")
    run.approval_id = "approval_test"
    task_runtime_store.create_run(run)
    approval = SimpleNamespace(
        status="pending",
        approval_id="approval_test",
        actions_requested=["write_files"],
        risk_level="medium",
        expires_at="2030-01-01T00:00:00+00:00",
    )
    service = UniversalTaskSessionService(
        store=task_runtime_store,
        approvals=FakeApprovals(approval),
        artifacts=FakeArtifacts(),
    )

    session = service.get_session(run.run_id)

    assert session is not None
    assert session.status == "WAITING_APPROVAL"
    assert session.approval_state.status == "pending"
    assert session.approval_state.approval_id == "approval_test"
    assert session.approval_state.required_actions == ["write_files"]


def test_universal_task_session_missing_outputs_blocks_safe_success(task_runtime_store):
    run = _run(status="blocked")
    task_runtime_store.create_run(run)
    task_runtime_store.save_result(
        run.run_id,
        TaskRunResult(
            run_id=run.run_id,
            status="blocked",
            summary="blocked",
            completion=TaskCompletionEvaluation(
                status="blocked",
                safe_to_report_success=False,
                expected_outcomes=["patch_result", "validation_result"],
                missing_outcomes=["patch_result", "validation_result"],
            ),
        ),
    )
    service = UniversalTaskSessionService(
        store=task_runtime_store,
        approvals=FakeApprovals(),
        artifacts=FakeArtifacts(),
    )

    session = service.get_session(run.run_id)

    assert session is not None
    assert session.status == "BLOCKED"
    assert session.validation_state.status == "blocked"
    assert session.validation_state.missing_outputs == ["patch_result", "validation_result"]
    assert session.validation_state.safe_to_report_success is False
    assert session.result_state.safe_to_report_success is False


def test_universal_task_session_terminal_block_avoids_timeline_build(task_runtime_store, monkeypatch):
    run = _run(status="blocked")
    task_runtime_store.create_run(run)
    task_runtime_store.save_result(
        run.run_id,
        TaskRunResult(
            run_id=run.run_id,
            status="blocked",
            summary="blocked",
            blocked_items=["artifact:semantic_inventory"],
        ),
    )
    service = UniversalTaskSessionService(
        store=task_runtime_store,
        approvals=FakeApprovals(),
        artifacts=FakeArtifacts(),
    )

    def fail_timeline_build(run_id):
        raise AssertionError("terminal blocked session should not build heavy timeline")

    monkeypatch.setattr(service.timelines, "build", fail_timeline_build)

    session = service.get_session(run.run_id)

    assert session is not None
    assert session.status == "BLOCKED"
    assert session.metadata["timeline_source"] == "not_loaded_for_terminal_block"


def test_universal_task_summary_derives_block_reason_from_blocked_result(task_runtime_store):
    run = _run(status="blocked")
    task_runtime_store.create_run(run)
    task_runtime_store.save_result(
        run.run_id,
        TaskRunResult(
            run_id=run.run_id,
            status="blocked",
            summary="blocked",
            blocked_items=["artifact:semantic_inventory"],
            validation={
                "status": "blocked",
                "blocking_findings": ["artifact:semantic_inventory"],
            },
        ),
    )
    service = UniversalTaskSessionService(
        store=task_runtime_store,
        approvals=FakeApprovals(),
        artifacts=FakeArtifacts(),
    )

    payload = service.summary(run.run_id)

    assert payload is not None
    assert payload["result"]["block_reason_code"] == "artifact:semantic_inventory"
    assert payload["result"]["safe_to_report_success"] is False


def test_universal_task_session_uses_only_operator_runtime_statuses(task_runtime_store):
    allowed = {
        "CREATED",
        "QUEUED",
        "WAITING_DELEGATION",
        "RUNNING",
        "WAITING_APPROVAL",
        "WAITING_USER",
        "COMPLETED",
        "FAILED",
        "BLOCKED",
        "CANCELLED",
        "TIMEOUT",
    }
    statuses = ("created", "queued", "waiting_delegation", "running", "waiting_input", "completed", "failed", "blocked", "cancelled", "expired")
    for index, status in enumerate(statuses, start=1):
        run = _run(run_id=f"task_run_{index:032x}", status=status)
        task_runtime_store.create_run(run)
        service = UniversalTaskSessionService(
            store=task_runtime_store,
            approvals=FakeApprovals(),
            artifacts=FakeArtifacts(),
        )

        session = service.get_session(run.run_id)

        assert session is not None
        assert session.status in allowed
        assert session.status not in {"ALMOST_DONE", "PROCESSING", "VALIDATING", "GENERATING_ARTIFACTS", "PATCH_PREVIEW"}


def test_universal_task_session_artifacts_merge_result_refs(task_runtime_store):
    run = _run(status="completed")
    task_runtime_store.create_run(run)
    task_runtime_store.save_result(
        run.run_id,
        TaskRunResult(
            run_id=run.run_id,
            status="completed",
            summary="artifact ready",
            outputs={"artifact_id": "artifact_abc123"},
        ),
    )
    service = UniversalTaskSessionService(
        store=task_runtime_store,
        approvals=FakeApprovals(),
        artifacts=FakeArtifacts({"artifact_abc123": {"artifact_id": "artifact_abc123", "status": "ready"}}),
    )

    payload = service.artifacts_for_run(run.run_id)

    assert payload is not None
    assert payload["artifact_state"]["status"] == "available"
    assert payload["artifact_state"]["artifact_ids"] == ["artifact_abc123"]


def test_universal_task_session_does_not_treat_result_container_name_as_artifact_id(task_runtime_store):
    run = _run(status="blocked")
    task_runtime_store.create_run(run)
    task_runtime_store.save_result(
        run.run_id,
        TaskRunResult(
            run_id=run.run_id,
            status="blocked",
            summary="blocked",
            outputs={"artifact_result": {"artifact_ids": [], "logical_paths": []}},
        ),
    )
    service = UniversalTaskSessionService(
        store=task_runtime_store,
        approvals=FakeApprovals(),
        artifacts=FakeArtifacts(),
    )

    payload = service.artifacts_for_run(run.run_id)

    assert payload is not None
    assert payload["artifact_state"]["artifact_ids"] == []


def test_universal_task_artifacts_expose_partial_rows_from_result(task_runtime_store):
    run = _run(status="blocked")
    task_runtime_store.create_run(run)
    task_runtime_store.save_result(
        run.run_id,
        TaskRunResult(
            run_id=run.run_id,
            status="blocked",
            summary="artifact interrupted",
            outputs={
                "artifact_result": {
                    "artifacts": [
                        {
                            "logical_path": "reports/firetest5/music_inventory.csv",
                            "status": "interrupted",
                            "reason_code": "ARTIFACT_RENDER_TIMEOUT",
                            "safe_to_use": False,
                            "visible_in_endpoint": True,
                        }
                    ]
                }
            },
        ),
    )
    service = UniversalTaskSessionService(
        store=task_runtime_store,
        approvals=FakeApprovals(),
        artifacts=FakeArtifacts(),
    )

    payload = service.artifacts_for_run(run.run_id)

    assert payload is not None
    assert payload["artifact_state"]["status"] == "partial"
    assert payload["artifacts"][0]["logical_path"] == "reports/firetest5/music_inventory.csv"
    assert payload["artifacts"][0]["status"] == "interrupted"
    assert payload["artifacts"][0]["safe_to_use"] is False


def test_universal_task_summary_exposes_observational_cognition_block(task_runtime_store):
    run = _run(status="blocked")
    run.policy_snapshot = {"approval_required_for": []}
    task_runtime_store.create_run(run)
    task_runtime_store.save_result(
        run.run_id,
        TaskRunResult(
            run_id=run.run_id,
            status="blocked",
            summary="blocked by semantic coverage",
            outputs={"artifact_id": "artifact_observation"},
            validation={"status": "blocked"},
            completion=TaskCompletionEvaluation(
                status="blocked",
                safe_to_report_success=False,
                expected_outcomes=["semantic_coverage"],
                missing_outcomes=["artifact_semantic_contract:reports/entities.csv:ATTRIBUTE_NOT_OBSERVED:codec"],
            ),
        ),
    )
    artifact = {
        "artifact_id": "artifact_observation",
        "status": "ready",
        "metadata": {
            "declared_contract": {
                "runtime_semantic_gaps": [
                    {"gap_type": "ATTRIBUTE_NOT_OBSERVED:codec", "reason_code": "NO_MATCHING_CAPABILITY"}
                ],
                "perception": {
                    "semantic_coverage_report": {
                        "structural_coverage": 1.0,
                        "entity_coverage": 1.0,
                        "attribute_coverage": 0.5,
                        "capability_coverage": 0.5,
                        "evidence_coverage": 0.5,
                        "missing_attributes": ["codec"],
                        "missing_capabilities": ["codec"],
                        "blocking_reasons": ["NO_MATCHING_CAPABILITY"],
                    },
                    "semantic_coverage_2": {
                        "knowledge_coverage": 0.5,
                        "truth_coverage": 0.5,
                        "semantic_coverage": 0.65,
                    },
                    "knowledge_records": [{"knowledge_id": "knowledge_name", "canonical_key": "name"}],
                    "semantic_assertions": [
                        {"assertion_id": "assertion_name", "canonical_key": "name", "truth_eligible": True},
                        {"assertion_id": "assertion_codec", "canonical_key": "codec", "truth_eligible": False},
                    ],
                    "semantic_self_review": {
                        "truth_readiness": "blocked",
                        "can_speaker_claim": False,
                        "reason_codes": ["NO_MATCHING_CAPABILITY"],
                    },
                    "observation_plan": {
                        "observation_goals": [{"goal_id": "goal_codec"}],
                        "capability_decisions": [{"goal_id": "goal_codec", "decision_status": "BLOCKED_NO_CAPABILITY"}],
                    },
                },
            }
        },
    }
    service = UniversalTaskSessionService(
        store=task_runtime_store,
        approvals=FakeApprovals(),
        artifacts=FakeArtifacts({"artifact_observation": artifact}),
    )

    payload = service.summary(run.run_id)

    assert payload is not None
    assert payload["status"] == "BLOCKED"
    assert payload["approval"]["status"] == "not_required"
    assert payload["observational_cognition"]["status"] == "blocked"
    assert payload["observational_cognition"]["blocking_reason"] == "NO_MATCHING_CAPABILITY"
    assert payload["observational_cognition"]["missing_attributes"] == ["codec"]
    assert payload["observational_cognition"]["missing_capabilities"] == ["codec"]
    assert payload["observational_cognition"]["observation_goals"] == {"total": 1, "blocked": 1, "ready": 0}
    assert payload["observational_cognition"]["semantic_coverage"]["knowledge"] == 0.5
    assert payload["observational_cognition"]["semantic_coverage"]["truth"] == 0.5
    assert payload["observational_cognition"]["knowledge"]["records"] == 1
    assert payload["observational_cognition"]["knowledge"]["assertions"] == 2
    assert payload["observational_cognition"]["knowledge"]["truth_eligible_assertions"] == 1
    assert payload["observational_cognition"]["knowledge"]["self_review_can_speaker_claim"] is False


def test_universal_task_summary_does_not_report_media_metadata_not_configured_when_bound_observations_exist(task_runtime_store):
    run = _run(status="blocked")
    run.policy_snapshot = {"approval_required_for": []}
    task_runtime_store.create_run(run)
    task_runtime_store.save_result(
        run.run_id,
        TaskRunResult(
            run_id=run.run_id,
            status="blocked",
            summary="blocked",
            outputs={"artifact_id": "artifact_metadata_binding"},
            validation={"status": "blocked"},
            completion=TaskCompletionEvaluation(status="blocked", safe_to_report_success=False),
        ),
    )
    artifact = {
        "artifact_id": "artifact_metadata_binding",
        "status": "ready",
        "metadata": {
            "declared_contract": {
                "artifact_observation_binding": {
                    "bound_counts_by_canonical_key": {"codec": 9, "duration": 8, "metadata": 8}
                },
                "perception": {},
            }
        },
    }
    service = UniversalTaskSessionService(
        store=task_runtime_store,
        approvals=FakeApprovals(),
        artifacts=FakeArtifacts({"artifact_metadata_binding": artifact}),
    )

    payload = service.summary(run.run_id)

    assert payload is not None
    media = payload["observational_cognition"]["media_metadata_capability"]
    assert media["status"] == "unknown_due_to_payload_ref"
    assert media["attributes_observed"] == ["codec", "duration", "metadata"]
    assert payload["observational_cognition"]["evidence"]["total_bound_observations"] == 25


def test_universal_task_summary_uses_post_compile_physical_telemetry_before_artifact_materialization(task_runtime_store):
    run = _run(status="blocked")
    run.policy_snapshot = {"approval_required_for": []}
    task_runtime_store.create_run(run)
    task_runtime_store.save_result(
        run.run_id,
        TaskRunResult(
            run_id=run.run_id,
            status="blocked",
            summary="blocked",
            outputs={},
            validation={"status": "blocked"},
            completion=TaskCompletionEvaluation(status="blocked", safe_to_report_success=False),
        ),
    )
    task_runtime_store.append_event(
        run.run_id,
        TaskRunEvent(
            event_id="event_post_compile",
            run_id=run.run_id,
            sequence=1,
            type="artifact_render_checkpoint",
            status="running",
            message="checkpoint",
            metadata={
                "checkpoint_stage": "after_post_compile_observation_execution",
                "media_metadata_capability": {
                    "status": "partial",
                    "configured": True,
                    "available": True,
                    "execution_status": "partial",
                    "primary_backend": "mutagen",
                    "attempted_backends": {"mutagen": 1},
                    "successful_backends": {"mutagen": 1},
                    "fallback_backends_used": {},
                    "backend_error_counts": {},
                    "evidence_counts_by_canonical_key": {"artist": 1},
                    "evidence_counts_by_backend": {"mutagen": 1},
                    "semantic_identity_evidence_counts": {
                        "track_title": 0,
                        "artist": 1,
                        "album": 0,
                        "album_artist": 0,
                    },
                },
                "evidence_counts_by_canonical_key": {"artist": 1},
            },
        ),
    )
    service = UniversalTaskSessionService(
        store=task_runtime_store,
        approvals=FakeApprovals(),
        artifacts=FakeArtifacts(),
    )

    payload = service.summary(run.run_id)

    assert payload is not None
    media = payload["observational_cognition"]["media_metadata_capability"]
    assert media["status"] == "partial"
    assert media["configured"] is True
    assert media["available"] is True
    assert media["execution_status"] == "partial"
    assert media["attempted_backends"] == ["mutagen"]
    assert media["successful_backends"] == ["mutagen"]
    assert media["semantic_identity_evidence_counts"]["artist"] == 1


def test_universal_task_events_support_polling_cursor(task_runtime_store):
    run = _run()
    task_runtime_store.create_run(run)
    task_runtime_store.append_event(
        run.run_id,
        TaskRunEvent(event_id="event_1", run_id=run.run_id, sequence=1, type="created", status="created", message="created"),
    )
    task_runtime_store.append_event(
        run.run_id,
        TaskRunEvent(event_id="event_2", run_id=run.run_id, sequence=2, type="running", status="running", message="running"),
    )
    service = UniversalTaskSessionService(
        store=task_runtime_store,
        approvals=FakeApprovals(),
        artifacts=FakeArtifacts(),
    )

    payload = service.events(run.run_id, after_sequence=1)

    assert payload is not None
    assert payload["count"] == 1
    assert payload["events"][0]["event_id"] == "event_2"


def test_universal_task_events_are_paginated_without_deep_payload(task_runtime_store):
    run = _run()
    task_runtime_store.create_run(run)
    for sequence in range(1, 6):
        task_runtime_store.append_event(
            run.run_id,
            TaskRunEvent(
                event_id=f"event_{sequence}",
                run_id=run.run_id,
                sequence=sequence,
                type="step",
                status="running",
                message="running",
                metadata={"large": "x" * 100},
            ),
        )
    service = UniversalTaskSessionService(
        store=task_runtime_store,
        approvals=FakeApprovals(),
        artifacts=FakeArtifacts(),
    )

    payload = service.events(run.run_id, limit=2)

    assert payload is not None
    assert payload["count"] == 2
    assert payload["event_count_total"] == 5
    assert payload["events_truncated"] is True
    assert payload["next_cursor"] == 2
