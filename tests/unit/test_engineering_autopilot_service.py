from aipinho.services.runtime.engineering_autopilot_service import EngineeringAutopilotService
from tests.support.runtime_fixtures import runtime_request


def test_engineering_autopilot_creates_supervised_mission(tmp_path):
    service = EngineeringAutopilotService(root=tmp_path / "missions")

    mission = service.create_mission(
        objective="Build governed feature",
        session_id="session_test",
        workspace="C:\\Project",
    )

    assert mission.lifecycle.status == "planned"
    assert mission.decision_log
    assert mission.decision_log[0].chosen_option == "governed_mission"
    assert mission.dashboard is not None
    assert service.get(mission.mission_id).mission_id == mission.mission_id


def test_engineering_autopilot_attaches_run_and_updates_dashboard(task_runtime_service):
    run = task_runtime_service.create_run(runtime_request())

    mission = task_runtime_service.create_engineering_mission_from_run(
        run.run_id,
        objective="Continuous governed mission",
    )

    assert mission is not None
    assert run.run_id in mission.run_ids
    assert mission.lifecycle.status == "running"
    assert mission.dashboard.run_count == 1
    assert mission.dashboard.evidence_count >= 2
    assert mission.reviews
    assert mission.reports


def test_mission_decision_log_contains_required_fields(task_runtime_service):
    run = task_runtime_service.create_run(runtime_request())
    mission = task_runtime_service.create_engineering_mission_from_run(run.run_id)

    entry = mission.decision_log[-1]

    assert entry.decision_id
    assert entry.reason
    assert entry.evidence
    assert entry.alternatives
    assert entry.chosen_option
    assert entry.rejected_options
    assert entry.impact
    assert entry.risk
    assert entry.rollback
    assert entry.worker
    assert entry.contracts
    assert entry.capabilities
    assert entry.validation
    assert entry.timestamp


def test_mission_resume_reflects_waiting_approval(task_runtime_service):
    run = task_runtime_service.create_run(runtime_request(policy={}))
    mission = task_runtime_service.create_engineering_mission_from_run(run.run_id)
    resume = task_runtime_service.engineering_autopilot.resume(mission)

    assert mission.lifecycle.status == "blocked"
    assert resume.next_action == "surface_block_reason"
    assert mission.dashboard.blocked_count == 1
