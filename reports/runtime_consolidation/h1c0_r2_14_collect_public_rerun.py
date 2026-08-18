from __future__ import annotations

import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from h1c0_r2_12_collect_public_rerun import (
    PHASE1_MESSAGE,
    collect_endpoint_set,
    events_from_endpoint,
    find_key,
    request,
)


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "reports" / "runtime_consolidation"
SOURCE_BINDING_METRIC_KEYS = {
    "input_entity_count",
    "projected_entity_count",
    "entity_count",
    "source_entity_processed_count",
    "observation_requirement_count",
    "observation_goal_count",
    "observation_strategy_count",
    "observation_task_count",
    "observation_record_count",
    "attribute_observation_attempt_count",
    "attribute_observation_count",
    "missing_observation_count",
    "unsupported_observation_count",
    "failed_observation_count",
    "observed_null_count",
    "evidence_ref_count",
    "unique_evidence_ref_count",
    "duplicate_evidence_ref_avoided_count",
    "evidence_set_count",
    "evidence_record_count",
    "evidence_record_referenced_count",
    "evidence_record_copied_count",
    "evidence_record_materialized_count",
    "provenance_ref_count",
    "source_index_entry_count",
    "capability_decision_count",
    "capability_index_entry_count",
    "candidate_fact_count",
    "observed_fact_count",
    "derived_fact_count",
    "projected_fact_count",
    "deduplicated_fact_count",
    "facts_with_evidence_count",
    "facts_with_provenance_count",
    "truth_eligible_count",
    "payload_item_count",
    "estimated_payload_bytes",
    "materialized_payload_bytes",
    "payload_ref_count",
    "bound_status",
    "reason_code",
}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def scalar(value: Any) -> bool:
    return value is None or isinstance(value, (str, int, float, bool))


def compact_event(event: dict[str, Any]) -> dict[str, Any]:
    data = event.get("metadata") if isinstance(event.get("metadata"), dict) else {}
    if not data:
        data = event.get("data") if isinstance(event.get("data"), dict) else {}
    payload_metrics = data.get("payload_metrics") if isinstance(data.get("payload_metrics"), dict) else {}
    metrics: dict[str, Any] = {}
    for key in SOURCE_BINDING_METRIC_KEYS:
        value = data.get(key)
        if scalar(value):
            metrics[key] = value
        payload_value = payload_metrics.get(key)
        if key not in metrics and scalar(payload_value):
            metrics[key] = payload_value
    stage = data.get("stage") or data.get("checkpoint_stage")
    if not stage and isinstance(event.get("message"), str) and " during " in event["message"]:
        stage = event["message"].rsplit(" during ", 1)[-1].rstrip(".")
    return {
        "sequence": event.get("sequence"),
        "type": event.get("type"),
        "status": event.get("status"),
        "stage": stage,
        "reason_code": data.get("reason_code") or event.get("reason_code"),
        "internal_reason_code": data.get("internal_reason_code"),
        "logical_path": data.get("logical_path") or data.get("artifact_logical_path"),
        "artifact_attempt_id": data.get("artifact_attempt_id"),
        "bounded": data.get("bounded"),
        "metrics": metrics,
    }


def latest_metrics(checkpoints: list[dict[str, Any]]) -> dict[str, Any]:
    for event in reversed(checkpoints):
        metrics = event.get("metrics") if isinstance(event.get("metrics"), dict) else {}
        if any(value is not None for value in metrics.values()):
            return metrics
    return {}


def summarize_run(run_id: str, endpoints: dict[str, Any]) -> dict[str, Any]:
    events = events_from_endpoint(endpoints.get("events", {}).get("body"))
    compact_events = [compact_event(event) for event in events]
    artifact_events = [event for event in compact_events if str(event.get("type") or "").startswith("artifact_")]
    checkpoints = [event for event in compact_events if event.get("type") == "artifact_render_checkpoint"]
    inventory_checkpoints = [
        event for event in checkpoints if event.get("logical_path") == "reports/firetest5/music_inventory.csv"
    ]
    terminal_events = [
        event
        for event in compact_events
        if event.get("type") in {"run_completed", "run_blocked", "run_failed", "run_cancelled"}
    ]
    result_body = endpoints.get("result", {}).get("body")
    result = result_body if isinstance(result_body, dict) else {}
    validation = result.get("validation") if isinstance(result.get("validation"), dict) else {}
    completion = result.get("completion") if isinstance(result.get("completion"), dict) else {}
    summary_body = endpoints.get("summary", {}).get("body")
    summary = summary_body if isinstance(summary_body, dict) else {}
    truth_body = endpoints.get("truth", {}).get("body")
    truth = truth_body if isinstance(truth_body, dict) else {}
    stages = [event.get("stage") for event in inventory_checkpoints if event.get("stage")]
    metrics = latest_metrics(inventory_checkpoints)
    return {
        "task_run_id": run_id,
        "result_json_exists": endpoints.get("result", {}).get("status_code") == 200,
        "result_endpoint_status_code": endpoints.get("result", {}).get("status_code"),
        "result_status": result.get("status"),
        "result_top_level_reason_code": result.get("reason_code"),
        "result_reason_code": result.get("reason_code") or validation.get("reason_code") or find_key(summary, "block_reason_code"),
        "completion_reason_code": find_key(completion, "reason_code"),
        "internal_reason_code": find_key(result, "internal_reason_code"),
        "finished_at": result.get("finished_at") or summary.get("finished_at"),
        "truth_safe_to_report_success": find_key(truth, "safe_to_report_success"),
        "terminal_event_count": len(terminal_events),
        "terminal_event_types": [event.get("type") for event in terminal_events],
        "terminal_events": terminal_events,
        "artifact_creation_started_count": sum(1 for event in artifact_events if event.get("type") == "artifact_creation_started"),
        "artifact_created_count": sum(1 for event in artifact_events if event.get("type") == "artifact_created"),
        "artifact_failed_count": sum(1 for event in artifact_events if event.get("type") == "artifact_failed"),
        "artifact_partial_count": sum(1 for event in artifact_events if event.get("type") == "artifact_partial"),
        "artifact_blocked_count": sum(1 for event in artifact_events if event.get("type") == "artifact_blocked"),
        "music_inventory_reached": bool(inventory_checkpoints)
        or any(event.get("logical_path") == "reports/firetest5/music_inventory.csv" for event in artifact_events),
        "source_binding_stages_reached": {
            "before_fact_source_binding": "before_fact_source_binding" in stages,
            "before_source_index_build": "before_source_index_build" in stages,
            "after_source_index_build": "after_source_index_build" in stages,
            "before_attribute_observation_projection": "before_attribute_observation_projection" in stages,
            "after_attribute_observation_projection": "after_attribute_observation_projection" in stages,
            "before_evidence_ref_resolution": "before_evidence_ref_resolution" in stages,
            "after_evidence_ref_resolution": "after_evidence_ref_resolution" in stages,
            "before_evidence_set_materialization": "before_evidence_set_materialization" in stages,
            "after_evidence_set_materialization": "after_evidence_set_materialization" in stages,
            "before_source_provenance_binding": "before_source_provenance_binding" in stages,
            "after_source_provenance_binding": "after_source_provenance_binding" in stages,
            "before_source_binding_bound_check": "before_source_binding_bound_check" in stages,
            "after_source_binding_bound_check": "after_source_binding_bound_check" in stages,
            "fact_source_binding_completed": "fact_source_binding_completed" in stages,
            "after_fact_source_binding": "after_fact_source_binding" in stages,
        },
        "after_fact_projection_reached": "after_fact_projection" in stages,
        "before_payload_assembly_reached": "before_payload_assembly" in stages,
        "after_payload_assembly_reached": "after_payload_assembly" in stages,
        "metadata_coverage_reached": any(stage in {"before_metadata_coverage_summary", "after_metadata_coverage_summary"} for stage in stages),
        "inventory_sufficiency_reached": any(stage in {"before_inventory_sufficiency", "after_inventory_sufficiency"} for stage in stages),
        "evidence_phase1_reached": any(event.get("logical_path") == "reports/firetest5/evidence_phase1.zip" for event in artifact_events),
        "last_completed_stage": stages[-1] if stages else None,
        "music_inventory_checkpoints": inventory_checkpoints,
        "source_binding_metrics": metrics,
        "endpoint_timings": {
            name: {"status_code": value.get("status_code"), "elapsed_ms": value.get("elapsed_ms"), "ok": value.get("ok")}
            for name, value in endpoints.items()
        },
        "queue_hygiene": endpoints.get("queue_hygiene", {}).get("body"),
        "queue_runtime": endpoints.get("queue_runtime", {}).get("body"),
    }


def run_public(output_name: str) -> dict[str, Any]:
    observation_path = OUT / output_name
    observation: dict[str, Any] = {
        "verdict": None,
        "captured_at": now_iso(),
        "phase0": {
            "runtime_executed": False,
            "task_created": False,
            "task_run_created": False,
            "operation_created": False,
            "operational_artifacts_created": False,
            "predicted_frontier": "PERCEPTION_FACT_SOURCE_BINDING_FRONTIER",
            "predicted_component": "ContractDrivenPerceptionService",
            "predicted_reason_code": "PERCEPTION_FACT_SOURCE_BINDING_FRONTIER",
        },
        "precheck": {
            "health": request("GET", "/api/v1/health", timeout=8),
            "queue_hygiene": request("GET", "/api/v1/runtime/hygiene/queue-health", timeout=8),
            "queue_runtime": request("GET", "/api/v1/task-runtime/queue", timeout=8),
        },
    }
    chat = request(
        "POST",
        "/api/v1/chat",
        payload={
            "message": PHASE1_MESSAGE,
            "context": {
                "surface": "api",
                "active_workspace": "C:\\Users\\rafae\\Documents\\PinhoabacaxiMusicasDesktop",
            },
        },
        timeout=20,
    )
    body = chat.get("body")
    run_id = find_key(body, "task_run_id")
    operation_id = find_key(body, "operation_id")
    observation["phase1_client"] = {
        "client_response_status_code": chat.get("status_code"),
        "client_response_time_ms": chat.get("elapsed_ms"),
        "client_response_status": find_key(body, "status"),
        "task_run_id": run_id,
        "operation_id": operation_id,
        "response_body_bounded": body,
    }
    if not run_id:
        observation["verdict"] = "phase1_public_observation_incomplete"
        observation["error"] = "task_run_id_not_found_in_chat_response"
        observation_path.write_text(json.dumps(observation, indent=2, ensure_ascii=False), encoding="utf-8")
        return observation

    endpoints: dict[str, Any] = {}
    summary: dict[str, Any] = {}
    deadline = time.time() + 600
    while time.time() < deadline:
        endpoints = collect_endpoint_set(str(run_id))
        summary = summarize_run(str(run_id), endpoints)
        if summary.get("result_endpoint_status_code") == 200 and summary.get("finished_at"):
            break
        time.sleep(5)

    observation["phase1"] = summary
    observation["endpoints"] = endpoints
    reason = summary.get("result_reason_code") or "PHASE1_NO_TERMINAL_RESULT"
    observation["phase2_to_6"] = {
        f"phase{i}": {
            "status": "skipped_due_to_prior_block"
            if summary.get("result_status") not in {"completed", "completed_with_limitations"}
            else "not_called",
            "api_called": False,
            "skip_reason": reason,
        }
        for i in range(2, 7)
    }
    observation["verdict"] = (
        "phase1_completed_public_observed"
        if summary.get("result_status") in {"completed", "completed_with_limitations"}
        else "phase1_terminal_blocked_or_failed_public_observed"
        if summary.get("result_json_exists") and summary.get("terminal_event_count") == 1
        else "phase1_public_observation_incomplete"
    )
    observation_path.write_text(json.dumps(observation, indent=2, ensure_ascii=False), encoding="utf-8")
    return observation


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    output_name = sys.argv[1] if len(sys.argv) > 1 else "firetest5_h1c0_r2_14_clean_phase0_to_6_validation_rerun.json"
    observation = run_public(output_name)
    phase1 = observation.get("phase1") if isinstance(observation.get("phase1"), dict) else {}
    run_id = (observation.get("phase1_client") or {}).get("task_run_id") if isinstance(observation.get("phase1_client"), dict) else None
    operation_id = (observation.get("phase1_client") or {}).get("operation_id") if isinstance(observation.get("phase1_client"), dict) else None
    stage_trace = {
        "task_run_id": run_id,
        "operation_id": operation_id,
        "music_inventory_reached": phase1.get("music_inventory_reached"),
        "source_binding_stages_reached": phase1.get("source_binding_stages_reached"),
        "after_fact_projection_reached": phase1.get("after_fact_projection_reached"),
        "before_payload_assembly_reached": phase1.get("before_payload_assembly_reached"),
        "last_completed_stage": phase1.get("last_completed_stage"),
        "checkpoints": phase1.get("music_inventory_checkpoints"),
    }
    metrics = {
        "task_run_id": run_id,
        "operation_id": operation_id,
        "source_binding_metrics": phase1.get("source_binding_metrics"),
        "checkpoint_metrics": [
            {"stage": item.get("stage"), "metrics": item.get("metrics")}
            for item in phase1.get("music_inventory_checkpoints", []) or []
        ],
    }
    terminal = {
        "task_run_id": run_id,
        "operation_id": operation_id,
        "result_status": phase1.get("result_status"),
        "result_top_level_reason_code": phase1.get("result_top_level_reason_code"),
        "result_reason_code": phase1.get("result_reason_code"),
        "completion_reason_code": phase1.get("completion_reason_code"),
        "terminal_event_count": phase1.get("terminal_event_count"),
        "terminal_event_types": phase1.get("terminal_event_types"),
        "reason_projection_consistent": bool(
            phase1.get("result_top_level_reason_code")
            and phase1.get("result_top_level_reason_code") == phase1.get("result_reason_code")
        ),
    }
    (OUT / "firetest5_h1c0_r2_14_source_binding_stage_trace.json").write_text(
        json.dumps(stage_trace, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    (OUT / "firetest5_h1c0_r2_14_source_binding_metrics.json").write_text(
        json.dumps(metrics, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    (OUT / "firetest5_h1c0_r2_14_terminal_reason_consistency.json").write_text(
        json.dumps(terminal, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(json.dumps({"task_run_id": run_id, "verdict": observation.get("verdict"), "result_reason_code": phase1.get("result_reason_code")}, ensure_ascii=False))
    return 0 if observation.get("verdict") else 2


if __name__ == "__main__":
    raise SystemExit(main())
