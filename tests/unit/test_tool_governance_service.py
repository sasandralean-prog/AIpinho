from __future__ import annotations

from aipinho.schemas.runtime.task_run_result import TaskRunResult
from aipinho.services.runtime.tool_governance_service import ToolGovernanceService
from tests.support.runtime_fixtures import allowed_policy, runtime_request, runtime_run


def test_tool_governance_trail_tracks_canonical_stage_order(task_runtime_service):
    run = task_runtime_service.create_run(runtime_request())
    result = TaskRunResult(
        run_id=run.run_id,
        status="completed",
        summary="Completed with validation.",
        outputs={"final_response": "ok"},
        validation={"status": "passed"},
        trace_ref=f"task-runs/{run.run_id}/trace",
    )

    trail, audit = ToolGovernanceService().build_and_audit(run, result=result)

    assert [checkpoint.stage for checkpoint in trail.checkpoints] == list(ToolGovernanceService.STAGES)
    assert trail.traceable is True
    assert trail.status == "ready"
    assert audit.status == "passed"
    assert audit.reason == "tool_governance_trail_traceable"


def test_tool_governance_fails_when_policy_is_missing():
    run = runtime_run(policy={})
    run.policy_snapshot = {}
    run.runtime_profile = "in_chat_final_report"
    service = ToolGovernanceService()

    trail, audit = service.build_and_audit(run)

    assert trail.status == "incomplete"
    assert "policy" in trail.missing_required_stages
    assert audit.status == "failed"
    assert audit.reason == "tool_governance_incomplete"


def test_tool_governance_blocks_when_approval_required_but_not_linked():
    run = runtime_run(
        action="apply_patch",
        contract_type="patch_request",
        runtime_profile="patch",
        policy=allowed_policy(
            contract_type="patch_request",
            allowed_actions=["patch_preview"],
            approval_required_for=["apply_patch"],
        ),
    )

    trail, audit = ToolGovernanceService().build_and_audit(run)

    assert "approval" in trail.blocked_stages
    assert trail.traceable is False
    assert audit.status == "failed"
    assert audit.reason == "tool_governance_blocked"


def test_tool_governance_uses_execution_graph_worker_routes(task_runtime_service):
    run = task_runtime_service.create_run(runtime_request())

    trail, _audit = ToolGovernanceService().build_and_audit(run)
    tool_router = next(checkpoint for checkpoint in trail.checkpoints if checkpoint.stage == "tool_router")

    assert tool_router.status == "present"
    assert tool_router.evidence_refs
    assert all("route" in item for item in tool_router.evidence_refs)


def test_task_runtime_service_exposes_tool_governance_trail(task_runtime_service):
    run = task_runtime_service.create_run(runtime_request())

    result = task_runtime_service.build_tool_governance_trail(run.run_id)

    assert result is not None
    trail, audit = result
    assert trail.run_id == run.run_id
    assert audit.run_id == run.run_id
