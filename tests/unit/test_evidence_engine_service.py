from aipinho.services.runtime.evidence_engine_service import (
    DecisionAuditService,
    DecisionBuilder,
    EvidenceEngineService,
    EvidenceIndexService,
    EvidenceReasoner,
    EvidenceScoreService,
)
from aipinho.schemas.runtime.evidence_engine import EvidenceItem
from tests.support.runtime_fixtures import runtime_request


def test_evidence_engine_collects_task_run_graph_and_memory(task_runtime_service):
    run = task_runtime_service.create_run(runtime_request())
    memory = task_runtime_service.get_operational_memory(run.run_id)
    engine = EvidenceEngineService()

    decision, audit = engine.decide_from_task_run(
        run,
        subject="task_run_start",
        decision="continue_governed_runtime",
        required_kinds=["task_run", "task_run_plan", "execution_graph"],
        operational_memory=memory,
    )

    assert decision.status == "accepted"
    assert decision.evidence_score.status == "sufficient"
    assert audit.status == "passed"
    assert {"task_run", "task_run_plan", "execution_graph", "operational_memory"}.issubset(
        set(decision.reasoning.present_kinds)
    )


def test_task_runtime_service_builds_evidence_backed_decision(task_runtime_service):
    run = task_runtime_service.create_run(runtime_request())

    result = task_runtime_service.build_evidence_decision(
        run.run_id,
        subject="runtime_admission",
        decision="continue",
        required_kinds=["task_run", "task_run_plan", "execution_graph"],
    )

    assert result is not None
    decision, audit = result
    assert decision.status == "accepted"
    assert audit.status == "passed"


def test_evidence_engine_blocks_decision_when_required_evidence_is_missing():
    index = EvidenceIndexService().build(
        [
            EvidenceItem(
                kind="task_run",
                source_id="task_run_test",
                summary="Only task run evidence is present.",
                strength="strong",
            )
        ]
    )
    score = EvidenceScoreService().score(index, required_kinds=["task_run", "execution_graph"])
    reasoning = EvidenceReasoner().reason(index, score, required_kinds=["task_run", "execution_graph"])

    decision = DecisionBuilder().build(
        subject="unsafe_decision",
        decision="proceed",
        index=index,
        score=score,
        reasoning=reasoning,
    )
    audit = DecisionAuditService().audit(decision)

    assert decision.status == "blocked"
    assert score.status == "insufficient"
    assert "execution_graph" in score.missing_required_kinds
    assert audit.status == "failed"


def test_evidence_index_groups_by_kind():
    index = EvidenceIndexService().build(
        [
            EvidenceItem(kind="task_run", source_id="run", summary="run", strength="strong"),
            EvidenceItem(kind="task_run_plan", source_id="plan", summary="plan", strength="strong"),
            EvidenceItem(kind="execution_graph", source_id="graph", summary="graph", strength="strong"),
        ]
    )

    assert sorted(index.by_kind) == ["execution_graph", "task_run", "task_run_plan"]
    assert len(index.by_kind["task_run"]) == 1
