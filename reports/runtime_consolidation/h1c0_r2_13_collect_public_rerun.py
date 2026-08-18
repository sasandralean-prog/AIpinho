from __future__ import annotations

import json
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
FACT_METRIC_KEYS = {
    "observations_in",
    "relationships_in",
    "candidate_fact_count",
    "observed_fact_count",
    "derived_fact_count",
    "projected_fact_count",
    "deduplicated_fact_count",
    "facts_with_evidence_count",
    "facts_with_provenance_count",
    "truth_eligible_count",
    "fact_provenance_issue_count",
    "fact_projection_elapsed_ms",
    "payload_item_count",
    "estimated_payload_bytes",
    "materialized_payload_bytes",
    "payload_ref_count",
    "reason_code",
}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def compact_event(event: dict[str, Any]) -> dict[str, Any]:
    data = event.get("metadata") if isinstance(event.get("metadata"), dict) else {}
    if not data:
        data = event.get("data") if isinstance(event.get("data"), dict) else {}
    stage = data.get("stage") or data.get("checkpoint_stage")
    if not stage and isinstance(event.get("message"), str) and " during " in event["message"]:
        stage = event["message"].rsplit(" during ", 1)[-1].rstrip(".")
    fact_metrics = {
        key: data.get(key)
        for key in FACT_METRIC_KEYS
        if isinstance(data.get(key), (str, int, float, bool)) or data.get(key) is None
    }
    payload_metrics = data.get("payload_metrics") if isinstance(data.get("payload_metrics"), dict) else {}
    for key in FACT_METRIC_KEYS:
        value = payload_metrics.get(key)
        if key not in fact_metrics and (isinstance(value, (str, int, float, bool)) or value is None):
            fact_metrics[key] = value
    return {
        "sequence": event.get("sequence"),
        "type": event.get("type"),
        "status": event.get("status"),
        "reason_code": data.get("reason_code") or event.get("reason_code"),
        "stage": stage,
        "logical_path": data.get("logical_path") or data.get("artifact_logical_path"),
        "artifact_attempt_id": data.get("artifact_attempt_id"),
        "internal_reason_code": data.get("internal_reason_code"),
        "bounded": data.get("bounded"),
        "fact_metrics": fact_metrics,
    }


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
    summary_body = endpoints.get("summary", {}).get("body")
    summary = summary_body if isinstance(summary_body, dict) else {}
    truth_body = endpoints.get("truth", {}).get("body")
    truth = truth_body if isinstance(truth_body, dict) else {}
    stages = [event.get("stage") for event in inventory_checkpoints if event.get("stage")]
    latest_metrics = {}
    for event in reversed(inventory_checkpoints):
        if event.get("fact_metrics"):
            latest_metrics = event["fact_metrics"]
            break
    return {
        "task_run_id": run_id,
        "result_json_exists": endpoints.get("result", {}).get("status_code") == 200,
        "result_endpoint_status_code": endpoints.get("result", {}).get("status_code"),
        "result_status": result.get("status"),
        "result_reason_code": result.get("reason_code") or validation.get("reason_code") or find_key(summary, "block_reason_code"),
        "internal_reason_code": find_key(result, "internal_reason_code"),
        "finished_at": result.get("finished_at") or summary.get("finished_at"),
        "truth_safe_to_report_success": find_key(truth, "safe_to_report_success"),
        "terminal_event_count": len(terminal_events),
        "terminal_events": terminal_events,
        "artifact_creation_started_count": sum(1 for event in artifact_events if event.get("type") == "artifact_creation_started"),
        "artifact_created_count": sum(1 for event in artifact_events if event.get("type") == "artifact_created"),
        "artifact_failed_count": sum(1 for event in artifact_events if event.get("type") == "artifact_failed"),
        "artifact_partial_count": sum(1 for event in artifact_events if event.get("type") == "artifact_partial"),
        "artifact_blocked_count": sum(1 for event in artifact_events if event.get("type") == "artifact_blocked"),
        "music_inventory_reached": bool(inventory_checkpoints)
        or any(event.get("logical_path") == "reports/firetest5/music_inventory.csv" for event in artifact_events),
        "before_fact_projection_reached": "before_fact_projection" in stages,
        "after_fact_projection_reached": "after_fact_projection" in stages,
        "before_payload_assembly_reached": "before_payload_assembly" in stages,
        "after_payload_assembly_reached": "after_payload_assembly" in stages,
        "last_completed_fact_stage": stages[-1] if stages else None,
        "metadata_coverage_reached": any(stage in {"before_metadata_coverage_summary", "after_metadata_coverage_summary"} for stage in stages),
        "inventory_sufficiency_reached": any(stage in {"before_inventory_sufficiency", "after_inventory_sufficiency"} for stage in stages),
        "evidence_phase1_reached": any(event.get("logical_path") == "reports/firetest5/evidence_phase1.zip" for event in artifact_events),
        "music_inventory_checkpoints": inventory_checkpoints,
        "fact_metrics": latest_metrics,
        "endpoint_timings": {
            name: {"status_code": value.get("status_code"), "elapsed_ms": value.get("elapsed_ms"), "ok": value.get("ok")}
            for name, value in endpoints.items()
        },
        "queue_hygiene": endpoints.get("queue_hygiene", {}).get("body"),
        "queue_runtime": endpoints.get("queue_runtime", {}).get("body"),
    }


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    observation_path = OUT / "firetest5_h1c0_r2_13_clean_phase0_to_6_rerun_observation.json"
    stage_trace_path = OUT / "firetest5_h1c0_r2_13_fact_projection_stage_trace.json"
    metrics_path = OUT / "firetest5_h1c0_r2_13_fact_projection_metrics.json"

    observation: dict[str, Any] = {
        "verdict": None,
        "captured_at": now_iso(),
        "phase0": {
            "runtime_executed": False,
            "task_created": False,
            "task_run_created": False,
            "operation_created": False,
            "operational_artifacts_created": False,
            "predicted_frontier": "PERCEPTION_FACT_PROJECTION_FRONTIER",
            "predicted_component": "ContractDrivenPerceptionService",
            "predicted_reason_code": "PERCEPTION_FACT_PROJECTION_FRONTIER",
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
        observation["error"] = "task_run_id_not_found_in_chat_response"
        observation_path.write_text(json.dumps(observation, indent=2, ensure_ascii=False), encoding="utf-8")
        return 2

    endpoints: dict[str, Any] = {}
    summary: dict[str, Any] = {}
    deadline = time.time() + 600
    while time.time() < deadline:
        endpoints = collect_endpoint_set(str(run_id))
        summary = summarize_run(str(run_id), endpoints)
        if summary["result_endpoint_status_code"] == 200 and summary["finished_at"]:
            break
        time.sleep(5)

    observation["phase1"] = summary
    observation["endpoints"] = endpoints
    reason = summary.get("result_reason_code") or "PHASE1_NO_TERMINAL_RESULT"
    observation["verdict"] = (
        "phase1_completed_public_observed"
        if summary.get("result_status") == "completed"
        else "phase1_terminal_blocked_or_failed_public_observed"
        if summary.get("result_json_exists") and summary.get("terminal_event_count") == 1
        else "phase1_public_observation_incomplete"
    )
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
    stage_trace = {
        "task_run_id": run_id,
        "operation_id": operation_id,
        "music_inventory_reached": summary.get("music_inventory_reached"),
        "before_fact_projection_reached": summary.get("before_fact_projection_reached"),
        "after_fact_projection_reached": summary.get("after_fact_projection_reached"),
        "before_payload_assembly_reached": summary.get("before_payload_assembly_reached"),
        "last_completed_fact_stage": summary.get("last_completed_fact_stage"),
        "checkpoints": summary.get("music_inventory_checkpoints"),
    }
    metrics = {
        "task_run_id": run_id,
        "operation_id": operation_id,
        "fact_metrics": summary.get("fact_metrics"),
        "checkpoint_metrics": [
            {"stage": item.get("stage"), "fact_metrics": item.get("fact_metrics")}
            for item in summary.get("music_inventory_checkpoints", [])
        ],
    }
    observation_path.write_text(json.dumps(observation, indent=2, ensure_ascii=False), encoding="utf-8")
    stage_trace_path.write_text(json.dumps(stage_trace, indent=2, ensure_ascii=False), encoding="utf-8")
    metrics_path.write_text(json.dumps(metrics, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({"task_run_id": run_id, "verdict": observation["verdict"], "observation": str(observation_path)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
