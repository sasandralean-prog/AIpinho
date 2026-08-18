from __future__ import annotations

import json
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
BASE_URL = "http://127.0.0.1:9088"
OUT = ROOT / "reports" / "runtime_consolidation"

PHASE1_MESSAGE = (
    "FireTest 5 Phase 1 — Discovery Governado.\n"
    "Trabalhe em modo read-only. Nao modifique o workspace nem a biblioteca.\n"
    "Workspace do app: C:\\Users\\rafae\\Documents\\PinhoabacaxiMusicasDesktop.\n"
    "Corpus/biblioteca de musicas: D:\\rafa\\pinho music.\n"
    "Gere artifacts governados:\n"
    "- reports/firetest5/phase1_discovery.md\n"
    "- reports/firetest5/project_inventory.md\n"
    "- reports/firetest5/music_inventory.csv\n"
    "- reports/firetest5/evidence_phase1.zip\n"
    "O inventario musical deve respeitar o contrato semantico de media corpus inventory; "
    "se a evidencia for insuficiente, bloqueie ou marque partial com reason_code explicito. "
    "Nao transforme findings CSV em inventario musical."
)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def request(method: str, path: str, payload: dict[str, Any] | None = None, timeout: float = 8.0) -> dict[str, Any]:
    url = f"{BASE_URL}{path}"
    data = None
    headers = {"Accept": "application/json"}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    started = time.perf_counter()
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            raw = response.read()
            elapsed_ms = round((time.perf_counter() - started) * 1000)
            try:
                body: Any = json.loads(raw.decode("utf-8")) if raw else None
            except json.JSONDecodeError:
                body = {"_non_json_preview": raw[:500].decode("utf-8", errors="replace")}
            return {"ok": True, "status_code": response.status, "elapsed_ms": elapsed_ms, "body": body}
    except urllib.error.HTTPError as exc:
        elapsed_ms = round((time.perf_counter() - started) * 1000)
        raw = exc.read()
        try:
            body = json.loads(raw.decode("utf-8")) if raw else None
        except json.JSONDecodeError:
            body = {"_non_json_preview": raw[:500].decode("utf-8", errors="replace")}
        return {"ok": False, "status_code": exc.code, "elapsed_ms": elapsed_ms, "body": body}
    except Exception as exc:
        elapsed_ms = round((time.perf_counter() - started) * 1000)
        return {
            "ok": False,
            "status_code": None,
            "elapsed_ms": elapsed_ms,
            "error": type(exc).__name__,
            "message": str(exc)[:500],
        }


def find_key(value: Any, key: str) -> Any:
    if isinstance(value, dict):
        if key in value and value[key] not in (None, ""):
            return value[key]
        for child in value.values():
            found = find_key(child, key)
            if found not in (None, ""):
                return found
    elif isinstance(value, list):
        for child in value:
            found = find_key(child, key)
            if found not in (None, ""):
                return found
    return None


def compact_event(event: dict[str, Any]) -> dict[str, Any]:
    data = event.get("metadata") if isinstance(event.get("metadata"), dict) else {}
    if not data:
        data = event.get("data") if isinstance(event.get("data"), dict) else {}
    stage = data.get("stage") or data.get("checkpoint_stage")
    if not stage and isinstance(event.get("message"), str) and " during " in event["message"]:
        stage = event["message"].rsplit(" during ", 1)[-1].rstrip(".")
    return {
        "sequence": event.get("sequence"),
        "type": event.get("type"),
        "status": event.get("status"),
        "reason_code": data.get("reason_code") or event.get("reason_code"),
        "stage": stage,
        "logical_path": data.get("logical_path") or data.get("artifact_logical_path"),
        "artifact_attempt_id": data.get("artifact_attempt_id"),
        "internal_reason_code": data.get("internal_reason_code"),
        "payload_metrics": data.get("payload_metrics"),
        "bounded": data.get("bounded"),
    }


def events_from_endpoint(body: Any) -> list[dict[str, Any]]:
    if isinstance(body, dict):
        events = body.get("events") or body.get("timeline") or []
        if isinstance(events, dict):
            events = events.get("events") or events.get("items") or []
        if isinstance(events, list):
            return [item for item in events if isinstance(item, dict)]
    return []


def collect_endpoint_set(run_id: str) -> dict[str, Any]:
    return {
        "summary": request("GET", f"/api/v1/task-runs/{run_id}/summary", timeout=12),
        "events": request("GET", f"/api/v1/task_runs/{run_id}/events?limit=300", timeout=12),
        "result": request("GET", f"/api/v1/task-runs/{run_id}/result", timeout=12),
        "truth": request("GET", f"/api/v1/task-runs/{run_id}/truth", timeout=12),
        "artifacts": request("GET", f"/api/v1/task-runs/{run_id}/artifacts", timeout=12),
        "session": request("GET", f"/api/v1/task-runs/{run_id}/session", timeout=12),
        "queue_hygiene": request("GET", "/api/v1/runtime/hygiene/queue-health", timeout=12),
        "queue_runtime": request("GET", "/api/v1/task-runtime/queue", timeout=12),
    }


def summarize_run(run_id: str, endpoints: dict[str, Any]) -> dict[str, Any]:
    events = events_from_endpoint(endpoints.get("events", {}).get("body"))
    compact_events = [compact_event(event) for event in events]
    artifact_events = [
        event for event in compact_events if str(event.get("type") or "").startswith("artifact_")
    ]
    render_checkpoints = [
        event for event in compact_events if event.get("type") == "artifact_render_checkpoint"
    ]
    music_checkpoints = [
        event
        for event in render_checkpoints
        if event.get("logical_path") == "reports/firetest5/music_inventory.csv"
    ]
    terminal_events = [
        event for event in compact_events if event.get("type") in {"run_completed", "run_blocked", "run_failed", "run_cancelled"}
    ]
    result_body = endpoints.get("result", {}).get("body")
    result = result_body if isinstance(result_body, dict) else {}
    validation = result.get("validation") if isinstance(result.get("validation"), dict) else {}
    outputs = result.get("outputs") if isinstance(result.get("outputs"), dict) else {}
    guard_output = outputs.get("artifact_worker_terminalization_guard") if isinstance(outputs.get("artifact_worker_terminalization_guard"), dict) else {}
    summary = endpoints.get("summary", {}).get("body")
    summary = summary if isinstance(summary, dict) else {}
    truth = endpoints.get("truth", {}).get("body")
    truth = truth if isinstance(truth, dict) else {}

    return {
        "task_run_id": run_id,
        "result_json_exists": endpoints.get("result", {}).get("status_code") == 200,
        "result_endpoint_status_code": endpoints.get("result", {}).get("status_code"),
        "result_status": result.get("status"),
        "result_reason_code": (
            result.get("reason_code")
            or validation.get("reason_code")
            or guard_output.get("reason_code")
            or find_key(summary, "block_reason_code")
        ),
        "result_source": result.get("source"),
        "internal_reason_code": find_key(result, "internal_reason_code"),
        "finished_at": result.get("finished_at") or summary.get("finished_at"),
        "truth_safe_to_report_success": find_key(truth, "safe_to_report_success"),
        "terminal_event_count": len(terminal_events),
        "terminal_events": terminal_events,
        "artifact_creation_started_count": sum(1 for e in artifact_events if e.get("type") == "artifact_creation_started"),
        "artifact_created_count": sum(1 for e in artifact_events if e.get("type") == "artifact_created"),
        "artifact_failed_count": sum(1 for e in artifact_events if e.get("type") == "artifact_failed"),
        "artifact_partial_count": sum(1 for e in artifact_events if e.get("type") == "artifact_partial"),
        "artifact_blocked_count": sum(1 for e in artifact_events if e.get("type") == "artifact_blocked"),
        "music_inventory_reached": bool(music_checkpoints)
        or any(e.get("logical_path") == "reports/firetest5/music_inventory.csv" for e in artifact_events),
        "music_inventory_checkpoints": music_checkpoints,
        "before_perception_payload_compile_reached": any(
            e.get("stage") == "before_perception_payload_compile" for e in music_checkpoints
        ),
        "after_perception_payload_compile_reached": any(
            e.get("stage") == "after_perception_payload_compile" for e in music_checkpoints
        ),
        "perception_compile_completed_reached": any(
            e.get("stage") == "perception_compile_completed" for e in music_checkpoints
        ),
        "internal_compile_checkpoints": [
            e for e in music_checkpoints if str(e.get("stage") or "").startswith(("before_", "after_", "perception_", "entity_projection"))
        ],
        "last_completed_internal_compile_stage": music_checkpoints[-1].get("stage") if music_checkpoints else None,
        "metadata_coverage_reached": any(
            e.get("stage") in {"before_metadata_coverage_summary", "after_metadata_coverage_summary"}
            for e in music_checkpoints
        ),
        "inventory_sufficiency_reached": any(
            e.get("stage") in {"before_inventory_sufficiency", "after_inventory_sufficiency"}
            for e in music_checkpoints
        ),
        "evidence_phase1_reached": any(e.get("logical_path") == "reports/firetest5/evidence_phase1.zip" for e in artifact_events),
        "endpoint_timings": {
            name: {"status_code": value.get("status_code"), "elapsed_ms": value.get("elapsed_ms"), "ok": value.get("ok")}
            for name, value in endpoints.items()
        },
        "queue_hygiene": endpoints.get("queue_hygiene", {}).get("body"),
        "queue_runtime": endpoints.get("queue_runtime", {}).get("body"),
    }


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    observation_path = OUT / "firetest5_h1c0_r2_12_clean_phase0_to_6_rerun_observation.json"
    stage_trace_path = OUT / "firetest5_h1c0_r2_12_perception_compile_stage_trace.json"
    metrics_path = OUT / "firetest5_h1c0_r2_12_perception_payload_metrics.json"

    observation: dict[str, Any] = {
        "verdict": None,
        "captured_at": now_iso(),
        "phase0": {
            "runtime_executed": False,
            "task_created": False,
            "task_run_created": False,
            "operation_created": False,
            "operational_artifacts_created": False,
            "predicted_frontier": "PERCEPTION_PAYLOAD_COMPILE_BOUNDARY",
            "predicted_component": "ContractDrivenPerceptionService",
            "predicted_reason_code": "PERCEPTION_PAYLOAD_COMPILE_BOUNDARY",
        },
        "precheck": {
            "health": request("GET", "/api/v1/health", timeout=8),
            "queue_hygiene": request("GET", "/api/v1/runtime/hygiene/queue-health", timeout=8),
            "queue_runtime": request("GET", "/api/v1/task-runtime/queue", timeout=8),
        },
    }

    chat_payload = {
        "message": PHASE1_MESSAGE,
        "context": {
            "surface": "api",
            "active_workspace": "C:\\Users\\rafae\\Documents\\PinhoabacaxiMusicasDesktop",
        },
    }
    chat = request("POST", "/api/v1/chat", payload=chat_payload, timeout=20)
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
    reason = summary.get("result_reason_code")
    if summary.get("result_status") == "completed":
        observation["verdict"] = "phase1_completed_public_observed"
    elif summary.get("result_json_exists") and summary.get("terminal_event_count") == 1:
        observation["verdict"] = "phase1_terminal_blocked_or_failed_public_observed"
    else:
        observation["verdict"] = "phase1_public_observation_incomplete"

    skip_reason = reason or "PHASE1_NO_TERMINAL_RESULT"
    phase2_status = "not_called"
    if summary.get("result_status") not in {"completed", "completed_with_limitations"}:
        phase2_status = "skipped_due_to_prior_block"
    observation["phase2_to_6"] = {
        f"phase{i}": {
            "status": phase2_status,
            "api_called": False,
            "skip_reason": skip_reason,
        }
        for i in range(2, 7)
    }

    stage_trace = {
        "task_run_id": run_id,
        "operation_id": operation_id,
        "music_inventory_reached": summary.get("music_inventory_reached"),
        "before_perception_payload_compile_reached": summary.get("before_perception_payload_compile_reached"),
        "after_perception_payload_compile_reached": summary.get("after_perception_payload_compile_reached"),
        "perception_compile_completed_reached": summary.get("perception_compile_completed_reached"),
        "last_completed_internal_compile_stage": summary.get("last_completed_internal_compile_stage"),
        "checkpoints": summary.get("music_inventory_checkpoints"),
    }
    payload_metrics = {
        "task_run_id": run_id,
        "operation_id": operation_id,
        "metrics_from_checkpoints": [
            {
                "stage": cp.get("stage"),
                "payload_metrics": cp.get("payload_metrics"),
                "internal_reason_code": cp.get("internal_reason_code"),
            }
            for cp in summary.get("music_inventory_checkpoints", [])
        ],
    }
    observation_path.write_text(json.dumps(observation, indent=2, ensure_ascii=False), encoding="utf-8")
    stage_trace_path.write_text(json.dumps(stage_trace, indent=2, ensure_ascii=False), encoding="utf-8")
    metrics_path.write_text(json.dumps(payload_metrics, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({"observation": str(observation_path), "task_run_id": run_id, "verdict": observation["verdict"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
