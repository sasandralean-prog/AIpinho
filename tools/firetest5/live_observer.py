from __future__ import annotations

import argparse
import concurrent.futures
import json
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4


DEFAULT_BASE_URL = "http://127.0.0.1:9088"
DEFAULT_TIMEOUT_SECONDS = 1800
DEFAULT_POLL_SECONDS = 10
CHAT_REQUEST_TIMEOUT_SECONDS = 1790

PHASE1_MESSAGE = (
    "FireTest 5 Phase 1 — Discovery Governado.\n"
    "Trabalhe em modo read-only. Nao modifique o workspace nem a biblioteca.\n"
    "Workspace do app: C:\\Users\\rafae\\Documents\\PinhoabacaxiMusicasDesktop.\n"
    "Corpus/biblioteca de musicas: D:\\rafa\\novapinhomusic.\n"
    "Gere artifacts governados:\n"
    "- reports/firetest5/phase1_discovery.md\n"
    "- reports/firetest5/project_inventory.md\n"
    "- reports/firetest5/music_inventory.csv\n"
    "- reports/firetest5/evidence_phase1.zip\n"
    "O inventario musical deve respeitar o contrato semantico de media corpus inventory; "
    "se a evidencia for insuficiente, bloqueie ou marque partial com reason_code explicito. "
    "Nao transforme findings CSV em inventario musical."
)


class ApiClient:
    def __init__(self, base_url: str, request_timeout: float = 12.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.request_timeout = request_timeout

    def request(self, method: str, path: str, payload: dict[str, Any] | None = None, *, timeout: float | None = None) -> dict[str, Any]:
        url = f"{self.base_url}{path}"
        data = None
        headers = {"Accept": "application/json"}
        if payload is not None:
            data = json.dumps(payload).encode("utf-8")
            headers["Content-Type"] = "application/json"
        started = time.perf_counter()
        request = urllib.request.Request(url, data=data, headers=headers, method=method)
        effective_timeout = self.request_timeout if timeout is None else timeout
        try:
            with urllib.request.urlopen(request, timeout=effective_timeout) as response:
                raw = response.read()
                body = _decode_body(raw)
                return {
                    "ok": True,
                    "status_code": response.status,
                    "elapsed_ms": round((time.perf_counter() - started) * 1000),
                    "body": body,
                }
        except urllib.error.HTTPError as exc:
            raw = exc.read()
            return {
                "ok": False,
                "status_code": exc.code,
                "elapsed_ms": round((time.perf_counter() - started) * 1000),
                "body": _decode_body(raw),
            }
        except Exception as exc:  # network failure is evidence, not a crash of the observer
            return {
                "ok": False,
                "status_code": None,
                "elapsed_ms": round((time.perf_counter() - started) * 1000),
                "error": type(exc).__name__,
                "message": str(exc)[:500],
            }


def _decode_body(raw: bytes) -> Any:
    if not raw:
        return None
    try:
        return json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return {"_non_json_preview": raw[:1000].decode("utf-8", errors="replace")}


def _find_key(value: Any, key: str) -> Any:
    if isinstance(value, dict):
        if key in value and value[key] not in (None, ""):
            return value[key]
        for child in value.values():
            found = _find_key(child, key)
            if found not in (None, ""):
                return found
    elif isinstance(value, list):
        for child in value:
            found = _find_key(child, key)
            if found not in (None, ""):
                return found
    return None


def _events(body: Any) -> list[dict[str, Any]]:
    if isinstance(body, dict):
        events = body.get("events") or body.get("timeline") or []
        if isinstance(events, dict):
            events = events.get("events") or events.get("items") or []
        if isinstance(events, list):
            return [event for event in events if isinstance(event, dict)]
    return []


def _compact_event(event: dict[str, Any]) -> dict[str, Any]:
    data = event.get("metadata") if isinstance(event.get("metadata"), dict) else {}
    if not data:
        data = event.get("data") if isinstance(event.get("data"), dict) else {}
    return {
        "sequence": event.get("sequence"),
        "type": event.get("type"),
        "status": event.get("status"),
        "reason_code": data.get("reason_code") or event.get("reason_code"),
        "stage": data.get("stage") or data.get("checkpoint_stage"),
        "logical_path": data.get("logical_path") or data.get("artifact_logical_path"),
        "artifact_attempt_id": data.get("artifact_attempt_id"),
        "internal_reason_code": data.get("internal_reason_code"),
        "payload_metrics": data.get("payload_metrics"),
    }


def _collect_run(client: ApiClient, run_id: str) -> dict[str, Any]:
    endpoints = {
        "summary": client.request("GET", f"/api/v1/task-runs/{run_id}/summary"),
        "events": client.request("GET", f"/api/v1/task_runs/{run_id}/events?limit=300"),
        "result": client.request("GET", f"/api/v1/task-runs/{run_id}/result"),
        "truth": client.request("GET", f"/api/v1/task-runs/{run_id}/truth"),
        "artifacts": client.request("GET", f"/api/v1/task-runs/{run_id}/artifacts"),
        "session": client.request("GET", f"/api/v1/task-runs/{run_id}/session"),
        "timeline": client.request("GET", f"/api/v1/task_runs/{run_id}/timeline"),
        "queue_hygiene": client.request("GET", "/api/v1/runtime/hygiene/queue-health"),
        "queue_runtime": client.request("GET", "/api/v1/task-runtime/queue"),
    }
    events = _events(endpoints["events"].get("body"))
    compact = [_compact_event(event) for event in events]
    result = endpoints["result"].get("body")
    result = result if isinstance(result, dict) else {}
    truth = endpoints["truth"].get("body")
    truth = truth if isinstance(truth, dict) else {}
    summary = endpoints["summary"].get("body")
    summary = summary if isinstance(summary, dict) else {}
    terminal_types = {"run_completed", "run_blocked", "run_failed", "run_cancelled"}
    terminal = [event for event in compact if event.get("type") in terminal_types]
    return {
        "task_run_id": run_id,
        "result": result,
        "summary": summary,
        "truth": truth,
        "terminal_events": terminal,
        "events": compact,
        "endpoint_timings": {
            name: {
                "status_code": value.get("status_code"),
                "elapsed_ms": value.get("elapsed_ms"),
                "ok": value.get("ok"),
            }
            for name, value in endpoints.items()
        },
        "queue_hygiene": endpoints["queue_hygiene"].get("body"),
        "queue_runtime": endpoints["queue_runtime"].get("body"),
        "result_status": result.get("status"),
        "result_reason_code": result.get("reason_code") or _find_key(summary, "block_reason_code"),
        "finished_at": result.get("finished_at") or summary.get("finished_at"),
        "safe_to_report_success": _find_key(truth, "safe_to_report_success"),
        "event_count": len(compact),
        "last_event": compact[-1] if compact else None,
    }


def _collect_runtime_observability(client: ApiClient, run_id: str | None = None) -> dict[str, Any]:
    snapshot_path = "/api/v1/runtime/operator/snapshot"
    if run_id:
        snapshot_path += f"?task_run_id={run_id}"
    return {
        "operator_status": client.request("GET", "/api/v1/runtime/operator/status"),
        "operator_snapshot": client.request("GET", snapshot_path),
        "doctor_status": client.request("GET", "/api/v1/runtime/doctor"),
        "runtime_doctor_status": client.request("GET", "/api/v1/runtime-doctor/status"),
        "runtime_queue": client.request("GET", "/api/v1/task-runtime/queue"),
        "task_sessions": client.request("GET", "/api/v1/task_runs?limit=100"),
    }


def _find_run_for_session(body: Any, session_id: str) -> str | None:
    if not isinstance(body, dict):
        return None
    sessions = body.get("sessions")
    if not isinstance(sessions, list):
        return None
    for session in sessions:
        if not isinstance(session, dict):
            continue
        metadata = session.get("metadata") if isinstance(session.get("metadata"), dict) else {}
        if session.get("session_id") == session_id or metadata.get("session_id") == session_id:
            candidate = session.get("task_run_id") or session.get("public_id")
            if candidate:
                return str(candidate)
    return None


def _post_chat(client: ApiClient, session_id: str) -> dict[str, Any]:
    return client.request(
        "POST",
        "/api/v1/chat",
        {
            "message": PHASE1_MESSAGE,
            "session_id": session_id,
            "context": {
                "surface": "api",
                "active_workspace": "C:\\Users\\rafae\\Documents\\PinhoabacaxiMusicasDesktop",
            },
        },
        timeout=CHAT_REQUEST_TIMEOUT_SECONDS,
    )


def _write_output(observation: dict[str, Any], output: Path | None) -> None:
    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(observation, indent=2, ensure_ascii=False), encoding="utf-8")


def observe(
    base_url: str = DEFAULT_BASE_URL,
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
    poll_seconds: int = DEFAULT_POLL_SECONDS,
    output: Path | None = None,
) -> dict[str, Any]:
    client = ApiClient(base_url)
    started = time.time()
    session_id = f"firetest5_observer_{uuid4().hex}"
    observation: dict[str, Any] = {
        "observer": "firetest5_live_observer_v2",
        "started_at": datetime.now(timezone.utc).isoformat(),
        "base_url": base_url,
        "timeout_seconds": timeout_seconds,
        "poll_seconds": poll_seconds,
        "correlation_session_id": session_id,
        "protocol": {
            "architecture": "dispatch -> acquire_task_run_id -> observe",
            "chat_route": "/api/v1/chat",
            "chat_dispatch_mode": "asynchronous_observer_thread",
            "run_acquisition": "GET /api/v1/task_runs filtered by unique session_id",
            "run_endpoints": [
                "summary",
                "events",
                "result",
                "truth",
                "artifacts",
                "session",
                "timeline",
                "queue_hygiene",
                "queue_runtime",
            ],
            "runtime_observability": [
                "/api/v1/runtime/operator/status",
                "/api/v1/runtime/operator/snapshot?task_run_id=...",
                "/api/v1/runtime/doctor",
                "/api/v1/runtime-doctor/status",
                "/api/v1/task_runs?limit=100",
            ],
        },
        "preflight": {
            "health": client.request("GET", "/api/v1/health"),
            "queue_hygiene": client.request("GET", "/api/v1/runtime/hygiene/queue-health"),
            "queue_runtime": client.request("GET", "/api/v1/task-runtime/queue"),
        },
        "samples": [],
        "pre_task_run_samples": [],
    }

    executor = concurrent.futures.ThreadPoolExecutor(max_workers=1, thread_name_prefix="firetest5-chat")
    future = executor.submit(_post_chat, client, session_id)
    run_id: str | None = None
    last_signature: str | None = None
    deadline = started + timeout_seconds

    try:
        while time.time() < deadline:
            # Acquire the TaskRun independently of the HTTP response. This is the
            # critical separation from the previous synchronous observer design.
            if run_id is None:
                task_sessions = client.request("GET", f"/api/v1/task_runs?session_id={session_id}&limit=10")
                runtime_state = _collect_runtime_observability(client)
                pre_sample = {
                    "captured_at": datetime.now(timezone.utc).isoformat(),
                    "runtime": runtime_state,
                    "task_session_lookup": task_sessions,
                }
                observation["pre_task_run_samples"].append(pre_sample)
                run_id = _find_run_for_session(task_sessions.get("body"), session_id)
                if run_id:
                    observation["acquisition"] = {
                        "status": "task_run_acquired",
                        "task_run_id": run_id,
                        "acquired_at": pre_sample["captured_at"],
                    }

            if run_id:
                run_state = _collect_run(client, run_id)
                runtime_state = _collect_runtime_observability(client, run_id)
                sample = {
                    "captured_at": datetime.now(timezone.utc).isoformat(),
                    "run": run_state,
                    "runtime": runtime_state,
                }
                observation["samples"].append(sample)
                signature = json.dumps(
                    {
                        "result_status": run_state.get("result_status"),
                        "reason": run_state.get("result_reason_code"),
                        "event_count": run_state.get("event_count"),
                        "last_event": run_state.get("last_event"),
                    },
                    sort_keys=True,
                    ensure_ascii=False,
                )
                if signature != last_signature:
                    print(
                        f"[{sample['captured_at']}] run={run_id} "
                        f"status={run_state.get('result_status')!r} "
                        f"events={run_state.get('event_count')} "
                        f"last={run_state.get('last_event')}"
                    )
                    last_signature = signature
                if run_state.get("finished_at") or run_state.get("terminal_events"):
                    observation["verdict"] = "TERMINAL_RUNTIME_OBSERVED"
                    break

            if future.done() and run_id is None:
                chat = future.result()
                chat_body = chat.get("body")
                response_run_id = _find_key(chat_body, "task_run_id")
                if response_run_id:
                    run_id = str(response_run_id)
                    observation["acquisition"] = {
                        "status": "task_run_acquired_from_chat_response",
                        "task_run_id": run_id,
                        "acquired_at": datetime.now(timezone.utc).isoformat(),
                    }

            if run_id is None and future.done():
                # The request has terminalized without exposing a TaskRun. Preserve
                # that fact; do not invent a runtime verdict.
                observation["verdict"] = "CHAT_COMPLETED_WITHOUT_TASK_RUN_ID"
                break

            time.sleep(max(1, poll_seconds))
        else:
            observation["verdict"] = "OBSERVER_DEADLINE_REACHED_WITHOUT_TERMINAL_RUNTIME"

        chat = future.result(timeout=0 if future.done() else max(0, deadline - time.time()))
        chat_body = chat.get("body")
        observation["chat"] = {
            "status_code": chat.get("status_code"),
            "elapsed_ms": chat.get("elapsed_ms"),
            "task_run_id": _find_key(chat_body, "task_run_id"),
            "operation_id": _find_key(chat_body, "operation_id"),
            "status": _find_key(chat_body, "status"),
            "body": chat_body,
        }
        if run_id and not observation.get("acquisition"):
            observation["acquisition"] = {
                "status": "task_run_acquired_from_chat_response",
                "task_run_id": run_id,
            }
    except concurrent.futures.TimeoutError:
        observation["chat"] = {
            "status": "chat_request_still_in_flight_at_observer_deadline",
            "task_run_id": run_id,
        }
        if run_id:
            observation["verdict"] = "OBSERVER_DEADLINE_REACHED_WITHOUT_TERMINAL_RUNTIME"
        else:
            observation["verdict"] = "OBSERVER_DEADLINE_REACHED_WITHOUT_TASK_RUN_ID"
    finally:
        # Do not wait for a long-running HTTP request after the observation
        # deadline. The server owns the runtime; the observer only observes it.
        executor.shutdown(wait=False, cancel_futures=False)

    observation["finished_at"] = datetime.now(timezone.utc).isoformat()
    observation["elapsed_seconds"] = round(time.time() - started, 3)
    observation["task_run_id"] = run_id
    observation["last_run_state"] = observation["samples"][-1]["run"] if observation["samples"] else None
    _write_output(observation, output)
    return observation


def main() -> int:
    parser = argparse.ArgumentParser(description="FireTest 5 Phase 1 live multi-endpoint observer")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--timeout-seconds", type=int, default=DEFAULT_TIMEOUT_SECONDS)
    parser.add_argument("--poll-seconds", type=int, default=DEFAULT_POLL_SECONDS)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = observe(
        base_url=args.base_url,
        timeout_seconds=args.timeout_seconds,
        poll_seconds=args.poll_seconds,
        output=args.output,
    )
    print(json.dumps({
        "verdict": result.get("verdict"),
        "task_run_id": result.get("task_run_id"),
        "chat_task_run_id": result.get("chat", {}).get("task_run_id"),
        "elapsed_seconds": result.get("elapsed_seconds"),
        "pre_task_run_samples": len(result.get("pre_task_run_samples", [])),
        "samples": len(result.get("samples", [])),
    }, ensure_ascii=False))
    return 0 if result.get("verdict") == "TERMINAL_RUNTIME_OBSERVED" else 2


if __name__ == "__main__":
    sys.exit(main())
