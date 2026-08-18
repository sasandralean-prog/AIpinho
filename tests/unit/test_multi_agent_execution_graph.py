from __future__ import annotations

from tests.support.runtime_fixtures import runtime_request


def test_cooperative_graph_simple_pipeline_created_by_aipinho(task_runtime_service):
    run = task_runtime_service.create_run(runtime_request(operation_type="android_project_analysis"))

    graph = task_runtime_service.create_cooperative_execution_graph(
        run.run_id,
        objective="Analise este projeto Android.",
    )

    assert graph is not None
    assert graph.graph_type == "cooperative"
    assert graph.supervisor["authority"] == "aipinho"
    assert graph.supervisor["providers_can_create_nodes"] is False
    assert graph.supervisor["providers_can_finish_graph"] is False
    assert graph.speakertruth["node_output_validation"] is True
    assert graph.speakertruth["graph_output_validation"] is True
    assert [node.node_id for node in graph.nodes][0] == "node_planner"
    assert {node.node_id for node in graph.nodes} >= {
        "node_planner",
        "node_executor",
        "node_debugger",
        "node_review",
        "node_memory",
        "node_supervisor",
        "node_final",
    }
    assert any(event.type == "execution_graph_created" for event in task_runtime_service.get_events(run.run_id))


def test_cooperative_graph_parallel_nodes_wait_for_planner(task_runtime_service):
    run = task_runtime_service.create_run(runtime_request(operation_type="android_project_analysis"))
    task_runtime_service.create_cooperative_execution_graph(run.run_id, objective="Analise este projeto Android com UI.")

    graph = task_runtime_service.complete_execution_node(
        run.run_id,
        "node_planner",
        outputs={"plan": "executor, debugger, vision and ocr can run in parallel"},
        speakertruth={"status": "passed"},
    )

    statuses = {node.node_id: node.status for node in graph.nodes}
    assert statuses["node_executor"] == "ready"
    assert statuses["node_debugger"] == "ready"
    assert statuses["node_vision"] == "ready"
    assert statuses["node_ocr"] == "ready"
    assert statuses["node_review"] == "waiting"
    assert any(event.type == "edge_completed" for event in task_runtime_service.get_events(run.run_id))


def test_cooperative_graph_review_waits_for_parallel_outputs(task_runtime_service):
    run = task_runtime_service.create_run(runtime_request(operation_type="android_project_analysis"))
    task_runtime_service.create_cooperative_execution_graph(run.run_id, objective="Analise este projeto Android com tela.")
    task_runtime_service.complete_execution_node(run.run_id, "node_planner", outputs={"plan": "ok"})

    for node_id in ("node_executor", "node_debugger", "node_vision", "node_ocr"):
        graph = task_runtime_service.complete_execution_node(
            run.run_id,
            node_id,
            outputs={"node": node_id, "status": "ok"},
            artifact_refs=[{"artifact_id": f"artifact_{node_id}", "owner_node_id": node_id}],
            memory_candidates=[{"source_node_id": node_id, "summary": "candidate"}],
            speakertruth={"status": "passed"},
        )

    statuses = {node.node_id: node.status for node in graph.nodes}
    assert statuses["node_review"] == "ready"
    assert len(graph.artifacts) == 4
    assert len(graph.memory_candidates) == 4


def test_retry_node_resets_only_downstream_nodes(task_runtime_service):
    run = task_runtime_service.create_run(runtime_request(operation_type="android_project_analysis"))
    task_runtime_service.create_cooperative_execution_graph(run.run_id, objective="Analise este projeto Android.")
    task_runtime_service.complete_execution_node(run.run_id, "node_planner", outputs={"plan": "ok"})
    task_runtime_service.complete_execution_node(run.run_id, "node_executor", outputs={"executor": "ok"})
    task_runtime_service.complete_execution_node(run.run_id, "node_debugger", outputs={"debugger": "ok"})
    task_runtime_service.complete_execution_node(run.run_id, "node_vision", outputs={"vision": "ok"})
    task_runtime_service.complete_execution_node(run.run_id, "node_ocr", outputs={"ocr": "ok"})
    task_runtime_service.complete_execution_node(run.run_id, "node_review", outputs={"review": "ok"})

    graph = task_runtime_service.retry_execution_node(run.run_id, "node_executor", reason="review_requested_retry")

    statuses = {node.node_id: node.status for node in graph.nodes}
    retry_counts = {node.node_id: node.retry_count for node in graph.nodes}
    assert statuses["node_planner"] == "completed"
    assert statuses["node_executor"] == "ready"
    assert statuses["node_debugger"] == "completed"
    assert statuses["node_review"] in {"pending", "waiting"}
    assert statuses["node_memory"] in {"pending", "waiting"}
    assert retry_counts["node_executor"] == 1
    assert any(event.type == "node_waiting" and event.status == "retry" for event in task_runtime_service.get_events(run.run_id))


def test_cooperative_graph_can_complete_with_node_outputs(task_runtime_service):
    run = task_runtime_service.create_run(runtime_request(operation_type="android_project_analysis"))
    task_runtime_service.create_cooperative_execution_graph(run.run_id, objective="Analise este projeto Android.")
    for node_id in (
        "node_planner",
        "node_executor",
        "node_debugger",
        "node_vision",
        "node_ocr",
        "node_review",
        "node_memory",
        "node_supervisor",
        "node_final",
    ):
        graph = task_runtime_service.complete_execution_node(
            run.run_id,
            node_id,
            outputs={"node_id": node_id, "status": "ok"},
            speakertruth={"status": "passed"},
            validation={"status": "passed"} if node_id == "node_supervisor" else {},
        )

    assert graph.status == "completed"
    assert graph.lifecycle.completed_node_ids
    assert any(event.type == "graph_completed" for event in task_runtime_service.get_events(run.run_id))


def test_node_failure_and_cancel_emit_graph_events(task_runtime_service):
    run = task_runtime_service.create_run(runtime_request(operation_type="android_project_analysis"))
    task_runtime_service.create_cooperative_execution_graph(run.run_id, objective="Analise este projeto Android.")

    failed = task_runtime_service.fail_execution_node(run.run_id, "node_planner", reason="planner_failed")
    assert failed.status == "failed"
    assert any(event.type == "graph_failed" for event in task_runtime_service.get_events(run.run_id))

    retried = task_runtime_service.retry_execution_node(run.run_id, "node_planner")
    assert next(node for node in retried.nodes if node.node_id == "node_planner").status == "ready"

    cancelled = task_runtime_service.cancel_execution_node(run.run_id, "node_planner", reason="operator_cancelled_node")
    assert next(node for node in cancelled.nodes if node.node_id == "node_planner").status == "cancelled"
