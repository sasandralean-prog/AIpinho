from __future__ import annotations

from tests.support.runtime_fixtures import runtime_request

from aipinho.services.runtime.intelligent_planner_service import IntelligentPlannerService


def _node_ids(report):
    return {node.node_id for node in report.nodes}


def test_simple_task_creates_governed_execution_graph_strategy():
    report = IntelligentPlannerService().plan(objective="Responda uma pergunta simples com evidencias.")

    assert report.status == "ready"
    assert report.intent.task_type == "simple"
    assert _node_ids(report) >= {"node_planner", "node_executor", "node_review", "node_supervisor", "node_final"}
    assert report.strategy.review_required is True
    assert report.strategy.parallel_groups
    assert "provider_owned_graph" in " ".join(report.alternatives_discarded)


def test_android_task_adds_debugger_vision_and_ocr_parallel_nodes():
    report = IntelligentPlannerService().plan(objective="Analise este projeto Android com UI e gere plano de correcao.")

    assert report.intent.task_type == "android"
    assert _node_ids(report) >= {"node_executor", "node_debugger", "node_vision", "node_ocr", "node_review"}
    parallel = set(report.strategy.parallel_groups[0])
    assert {"node_executor", "node_debugger", "node_vision", "node_ocr"}.issubset(parallel)
    review = next(node for node in report.nodes if node.node_id == "node_review")
    assert {"node_executor", "node_debugger", "node_vision", "node_ocr"}.issubset(set(review.dependencies))


def test_python_task_adds_debugger_without_visual_nodes():
    report = IntelligentPlannerService().plan(objective="Diagnostique um projeto Python com pytest falhando.")

    assert report.intent.task_type == "python"
    assert {"node_executor", "node_debugger"}.issubset(_node_ids(report))
    assert "node_vision" not in _node_ids(report)
    assert "node_ocr" not in _node_ids(report)


def test_multimodal_ocr_task_uses_visual_specialists():
    report = IntelligentPlannerService().plan(objective="Faca OCR de screenshots e revise a UI.")

    assert report.intent.task_type in {"multimodal", "ocr", "vision"}
    assert {"node_vision", "node_ocr"}.issubset(_node_ids(report))


def test_side_effect_actions_raise_risk_and_approval_expectation():
    report = IntelligentPlannerService().plan(
        objective="Implemente uma feature e rode build.",
        requested_actions=["apply_patch", "run_command"],
    )

    assert report.intent.requires_approval is True
    assert report.strategy.approval_required is True
    assert report.strategy.risk_level == "medium"
    risky = [node for node in report.nodes if node.requires_approval]
    assert risky
    assert "approval_required_before_side_effect" in report.risks


def test_replan_after_node_failure_keeps_report_lineage():
    service = IntelligentPlannerService()
    report = service.plan(objective="Analise este projeto Android.")

    replanned = service.replan_after_node_failure(report, failed_node_id="node_executor", reason="review_requested_retry")

    assert replanned.replan_of == report.report_id
    assert replanned.replan_reason == "review_requested_retry"
    assert replanned.report_id != report.report_id
    assert "node_replan:node_executor" in replanned.risks


def test_task_runtime_builds_graph_from_intelligent_planner(task_runtime_service):
    run = task_runtime_service.create_run(runtime_request(operation_type="android_project_analysis"))

    graph = task_runtime_service.create_cooperative_execution_graph(
        run.run_id,
        objective="Analise este projeto Android com UI.",
    )

    report = task_runtime_service.get_planning_report(run.run_id)
    assert graph.planning_report
    assert report["intent"]["task_type"] == "android"
    assert {node.node_id for node in graph.nodes} >= {"node_vision", "node_ocr", "node_review"}
    assert any(event.type == "planning_report_created" for event in task_runtime_service.get_events(run.run_id))


def test_task_runtime_replan_retries_only_requested_node(task_runtime_service):
    run = task_runtime_service.create_run(runtime_request(operation_type="android_project_analysis"))
    task_runtime_service.create_cooperative_execution_graph(run.run_id, objective="Analise este projeto Android.")
    task_runtime_service.complete_execution_node(run.run_id, "node_planner", outputs={"plan": "ok"})
    task_runtime_service.complete_execution_node(run.run_id, "node_executor", outputs={"executor": "ok"})

    result = task_runtime_service.replan_execution_node(run.run_id, "node_executor", reason="review_requested_retry")

    assert result is not None
    graph = result["execution_graph"]
    statuses = {node.node_id: node.status for node in graph.nodes}
    assert statuses["node_planner"] == "completed"
    assert statuses["node_executor"] == "ready"
    assert result["planning_report"].replan_of is not None
    assert any(event.type == "execution_plan_replanned" for event in task_runtime_service.get_events(run.run_id))
