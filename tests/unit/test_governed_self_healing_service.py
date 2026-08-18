from __future__ import annotations

from aipinho.schemas.multi_agent_observability import StateConsistencyIssue, StateConsistencyReport
from aipinho.schemas.self_healing import SelfHealingApplyRequest, SelfHealingScanRequest, SelfHealingTriageRequest
from aipinho.services.self_healing.self_healing_service import SelfHealingService, SelfHealingStore, StateConsistencyDetector


class _FakeObservability:
    def state_consistency(self):
        return StateConsistencyReport(
            status="degraded",
            issues=[
                StateConsistencyIssue(
                    issue_id="active_run_without_events:run_x",
                    issue_type="active_run_without_events",
                    severity="warning",
                    entity_type="run",
                    entity_id="run_x",
                    summary="Run ativo sem eventos rastreaveis.",
                    evidence_refs=["run:run_x"],
                )
            ],
        )

    def dashboard(self):
        class Dashboard:
            active_runs = []

        return Dashboard()

    def debugger_events(self, *args, **kwargs):
        class Events:
            events = []

        return Events()


def test_self_healing_scan_generates_candidates_from_consistency_issues(tmp_path):
    service = SelfHealingService(
        store=SelfHealingStore(tmp_path),
        observability=_FakeObservability(),
        detectors=[StateConsistencyDetector()],
    )
    candidates = service.scan(SelfHealingScanRequest())
    assert len(candidates) == 1
    candidate = candidates[0]
    assert candidate.issue_type == "active_run_without_events"
    assert candidate.risk_level == "low"
    assert candidate.approval_required is False
    assert candidate.recommended_actions[0].action_type == "create_diagnostic_report"


def test_self_healing_triage_and_low_risk_apply_are_auditable(tmp_path, monkeypatch):
    service = SelfHealingService(
        store=SelfHealingStore(tmp_path),
        observability=_FakeObservability(),
        detectors=[StateConsistencyDetector()],
    )
    candidate = service.scan(SelfHealingScanRequest())[0]
    triaged = service.triage(candidate.candidate_id, SelfHealingTriageRequest(decision="approve", reason="baixo risco"))
    assert triaged.status == "approved"

    monkeypatch.setattr(service, "_create_diagnostic_report", lambda candidate: ("artifact_test", "/api/v1/artifacts/artifact_test/download"))
    run = service.apply(candidate.candidate_id, SelfHealingApplyRequest())
    assert run.status == "completed"
    assert run.validation_status == "passed"
    assert run.artifact_ids == ["artifact_test"]
    assert service.candidate(candidate.candidate_id).status == "applied"


def test_self_healing_medium_risk_requires_approval(tmp_path):
    service = SelfHealingService(
        store=SelfHealingStore(tmp_path),
        observability=_FakeObservability(),
        detectors=[StateConsistencyDetector()],
    )
    candidate = service.scan(SelfHealingScanRequest())[0].model_copy(update={"risk_level": "medium", "approval_required": True})
    service.store.save_candidate(candidate)
    run = service.apply(candidate.candidate_id, SelfHealingApplyRequest())
    assert run.status == "pending_approval"
    assert run.validation_status == "pending"
    assert "approval_required" in run.warnings
