from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from h1c0_r2_14_collect_public_rerun import OUT, run_public


PERSIST_STAGES = {
    "before_artifact_persist",
    "before_persist_payload_classification",
    "after_persist_payload_classification",
    "before_payload_materialization",
    "after_payload_materialization",
    "before_payload_serialization",
    "payload_serialization_checkpoint",
    "after_payload_serialization",
    "before_payload_ref_decision",
    "after_payload_ref_decision",
    "before_payload_ref_persist",
    "after_payload_ref_persist",
    "before_artifact_content_write",
    "artifact_content_write_checkpoint",
    "after_artifact_content_write",
    "before_manifest_build",
    "after_manifest_build",
    "before_manifest_persist",
    "before_sharded_manifest_persist",
    "after_sharded_manifest_persist",
    "after_manifest_persist",
    "before_registry_index_update",
    "before_light_index_persist",
    "after_light_index_persist",
    "before_legacy_registry_projection",
    "after_legacy_registry_projection",
    "legacy_registry_projection_skipped",
    "after_registry_index_update",
    "before_artifact_commit",
    "after_artifact_commit",
    "artifact_persist_completed",
    "after_artifact_persist",
}

PERSIST_METRIC_KEYS = {
    "artifact_content_bytes",
    "artifact_id",
    "bytes_written",
    "checksum",
    "copy_count_estimate",
    "manifest_bytes",
    "manifest_inline_bytes",
    "payload_bytes",
    "payload_ref_bytes",
    "payload_ref_count",
    "payload_ref_decision",
    "serialized_bytes",
    "storage_ref_present",
    "write_elapsed_ms",
}


def _metrics_from_checkpoints(checkpoints: list[dict[str, Any]]) -> dict[str, Any]:
    merged: dict[str, Any] = {}
    for checkpoint in checkpoints:
        metrics = checkpoint.get("metrics") if isinstance(checkpoint.get("metrics"), dict) else {}
        for key, value in metrics.items():
            if value is not None:
                merged[key] = value
    return merged


def _metrics_from_raw_music_checkpoints(observation: dict[str, Any]) -> dict[str, Any]:
    merged: dict[str, Any] = {}
    for event in _raw_events(observation):
        if event.get("type") != "artifact_render_checkpoint":
            continue
        metadata = event.get("metadata") if isinstance(event.get("metadata"), dict) else {}
        if metadata.get("logical_path") != "reports/firetest5/music_inventory.csv":
            continue
        payload_metrics = metadata.get("payload_metrics") if isinstance(metadata.get("payload_metrics"), dict) else {}
        for source in (metadata, payload_metrics):
            for key, value in source.items():
                if key.startswith("_") or isinstance(value, (dict, list)):
                    continue
                if value is not None:
                    merged[key] = value
    return merged


def _raw_events(observation: dict[str, Any]) -> list[dict[str, Any]]:
    endpoints = observation.get("endpoints") if isinstance(observation.get("endpoints"), dict) else {}
    events_body = endpoints.get("events", {}).get("body") if isinstance(endpoints.get("events"), dict) else {}
    events = events_body.get("events") if isinstance(events_body, dict) else []
    return events if isinstance(events, list) else []


def _raw_persist_checkpoints(observation: dict[str, Any], *, logical_path: str | None = None) -> list[dict[str, Any]]:
    checkpoints: list[dict[str, Any]] = []
    for event in _raw_events(observation):
        if event.get("type") != "artifact_render_checkpoint":
            continue
        metadata = event.get("metadata") if isinstance(event.get("metadata"), dict) else {}
        stage = metadata.get("stage")
        if stage not in PERSIST_STAGES:
            continue
        event_logical_path = metadata.get("logical_path")
        if logical_path is not None and event_logical_path != logical_path:
            continue
        metrics = {key: metadata.get(key) for key in PERSIST_METRIC_KEYS if metadata.get(key) is not None}
        checkpoints.append(
            {
                "sequence": event.get("sequence"),
                "type": event.get("type"),
                "status": event.get("status"),
                "stage": stage,
                "logical_path": metadata.get("logical_path"),
                "artifact_attempt_id": metadata.get("artifact_attempt_id"),
                "bounded": metadata.get("bounded"),
                "metrics": metrics,
            }
        )
    return checkpoints


def _endpoint_timings(phase1: dict[str, Any]) -> dict[str, Any]:
    timings = phase1.get("endpoint_timings") if isinstance(phase1.get("endpoint_timings"), dict) else {}
    return {
        key: {
            "status_code": value.get("status_code"),
            "elapsed_ms": value.get("elapsed_ms"),
            "ok": value.get("ok"),
        }
        for key, value in timings.items()
        if isinstance(value, dict)
    }


def _group_persist_by_logical_path(checkpoints: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    grouped: dict[str, dict[str, Any]] = {}
    for checkpoint in checkpoints:
        logical_path = str(checkpoint.get("logical_path") or "unknown")
        entry = grouped.setdefault(
            logical_path,
            {
                "checkpoint_count": 0,
                "stages": [],
                "last_stage": None,
                "metrics": {},
            },
        )
        entry["checkpoint_count"] += 1
        stage = checkpoint.get("stage")
        if stage:
            entry["stages"].append(stage)
            entry["last_stage"] = stage
        for key, value in (checkpoint.get("metrics") or {}).items():
            if value is not None:
                entry["metrics"][key] = value
    return grouped


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    output_name = sys.argv[1] if len(sys.argv) > 1 else "firetest5_h1c0_r2_15_clean_phase0_to_6_validation_rerun.json"
    observation = run_public(output_name)
    observation["phase0"] = {
        "runtime_executed": False,
        "task_created": False,
        "task_run_created": False,
        "operation_created": False,
        "operational_artifacts_created": False,
        "predicted_frontier": "ARTIFACT_PERSIST_PAYLOAD_REF_BOUNDARY",
        "predicted_component": "ArtifactRuntimeService",
        "predicted_reason_code": "ARTIFACT_PERSIST_PAYLOAD_BOUNDARY_FRONTIER",
    }
    (OUT / output_name).write_text(json.dumps(observation, indent=2, ensure_ascii=False), encoding="utf-8")

    phase1 = observation.get("phase1") if isinstance(observation.get("phase1"), dict) else {}
    client = observation.get("phase1_client") if isinstance(observation.get("phase1_client"), dict) else {}
    checkpoints = phase1.get("music_inventory_checkpoints") if isinstance(phase1.get("music_inventory_checkpoints"), list) else []
    compact_persist_checkpoints = [item for item in checkpoints if item.get("stage") in PERSIST_STAGES]
    raw_persist_checkpoints_all = _raw_persist_checkpoints(observation)
    raw_persist_checkpoints = _raw_persist_checkpoints(observation, logical_path="reports/firetest5/music_inventory.csv")
    persist_checkpoints = raw_persist_checkpoints or [
        item for item in compact_persist_checkpoints if item.get("logical_path") == "reports/firetest5/music_inventory.csv"
    ]
    persist_metrics = _metrics_from_checkpoints(persist_checkpoints)
    trace = {
        "task_run_id": client.get("task_run_id"),
        "operation_id": client.get("operation_id"),
        "music_inventory_reached": phase1.get("music_inventory_reached"),
        "persist_stages_reached": {stage: any(item.get("stage") == stage for item in persist_checkpoints) for stage in sorted(PERSIST_STAGES)},
        "last_completed_stage": phase1.get("last_completed_stage"),
        "after_artifact_persist_reached": any(item.get("stage") == "after_artifact_persist" for item in persist_checkpoints),
        "persist_checkpoints": persist_checkpoints,
        "persist_by_logical_path": _group_persist_by_logical_path(raw_persist_checkpoints_all),
    }
    metrics = {
        "task_run_id": client.get("task_run_id"),
        "operation_id": client.get("operation_id"),
        "persist_metrics": persist_metrics,
        "bounded_metrics_projection": phase1.get("source_binding_metrics"),
        "bounded_metrics_merged_from_music_checkpoints": _metrics_from_raw_music_checkpoints(observation),
        "endpoint_timings": _endpoint_timings(phase1),
    }
    terminal = {
        "task_run_id": client.get("task_run_id"),
        "operation_id": client.get("operation_id"),
        "result_status": phase1.get("result_status"),
        "result_reason_code": phase1.get("result_reason_code"),
        "result_top_level_reason_code": phase1.get("result_top_level_reason_code"),
        "completion_reason_code": phase1.get("completion_reason_code"),
        "finished_at": phase1.get("finished_at"),
        "terminal_event_count": phase1.get("terminal_event_count"),
        "terminal_event_types": phase1.get("terminal_event_types"),
        "truth_safe_to_report_success": phase1.get("truth_safe_to_report_success"),
        "reason_projection_consistent": bool(
            phase1.get("result_top_level_reason_code")
            and phase1.get("result_top_level_reason_code") == phase1.get("result_reason_code")
        ),
    }
    (OUT / "firetest5_h1c0_r2_15_artifact_persist_stage_trace.json").write_text(
        json.dumps(trace, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    (OUT / "firetest5_h1c0_r2_15_artifact_persist_metrics.json").write_text(
        json.dumps(metrics, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    (OUT / "firetest5_h1c0_r2_15_terminal_reason_consistency.json").write_text(
        json.dumps(terminal, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(json.dumps({"task_run_id": client.get("task_run_id"), "verdict": observation.get("verdict"), "reason": phase1.get("result_reason_code")}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
