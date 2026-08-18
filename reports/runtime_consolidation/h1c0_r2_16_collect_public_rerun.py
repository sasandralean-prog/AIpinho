from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any

from h1c0_r2_14_collect_public_rerun import OUT, run_public


MUSIC_LOGICAL_PATH = "reports/firetest5/music_inventory.csv"
SCALAR = (str, int, float, bool)
CARDINALITY_KEYS = {
    "source_input_entity_count",
    "selected_entity_count",
    "projected_entity_count",
    "row_model_candidate_count",
    "row_model_accepted_count",
    "row_model_rejected_count",
    "row_model_skipped_count",
    "csv_rows_expected_at_stream_start",
    "csv_rows_attempted",
    "csv_rows_rendered",
    "csv_rows_written",
    "csv_rows_failed",
    "csv_cells_expected",
    "csv_cells_attempted",
    "csv_cells_rendered",
    "csv_cells_written",
}
DIGEST_KEYS = {
    "input_entity_set_digest",
    "projected_entity_set_digest",
    "row_model_digest",
    "column_schema_digest",
    "render_order_digest",
}
COST_KEYS = {
    "row_model_build_elapsed_ms",
    "row_order_elapsed_ms",
    "csv_stream_elapsed_ms",
    "csv_row_render_elapsed_ms",
    "csv_cell_render_elapsed_ms",
    "csv_cell_serialization_elapsed_ms",
    "csv_serialization_elapsed_ms",
    "csv_finalize_elapsed_ms",
    "rows_per_second",
    "cells_per_second",
    "average_cell_us",
    "max_batch_elapsed_ms",
}
PAYLOAD_REF_KEYS = {
    "payload_kind",
    "payload_bytes",
    "payload_ref_count",
    "payload_ref_bytes",
    "payload_ref_dedup_hit_count",
    "payload_ref_decision",
    "artifact_id",
}
BOUNDED_METRIC_KEYS = CARDINALITY_KEYS | DIGEST_KEYS | COST_KEYS | PAYLOAD_REF_KEYS | {
    "input_entity_count",
    "entity_count",
    "payload_item_count",
    "estimated_payload_bytes",
    "materialized_payload_bytes",
    "observation_requirement_count",
    "attribute_observation_count",
    "missing_observation_count",
    "unsupported_observation_count",
    "failed_observation_count",
    "observed_null_count",
    "candidate_fact_count",
    "observed_fact_count",
    "derived_fact_count",
    "projected_fact_count",
    "facts_with_evidence_count",
    "facts_with_provenance_count",
    "evidence_ref_count",
    "unique_evidence_ref_count",
    "evidence_set_count",
    "source_index_entry_count",
    "provenance_ref_count",
    "bound_status",
    "reason_code",
    "cardinality_domain",
    "progress_semantics",
}


def _events(observation: dict[str, Any]) -> list[dict[str, Any]]:
    endpoints = observation.get("endpoints") if isinstance(observation.get("endpoints"), dict) else {}
    body = endpoints.get("events", {}).get("body") if isinstance(endpoints.get("events"), dict) else {}
    events = body.get("events") if isinstance(body, dict) else []
    return events if isinstance(events, list) else []


def _metric_sources(metadata: dict[str, Any]) -> list[dict[str, Any]]:
    sources = [metadata]
    payload_metrics = metadata.get("payload_metrics")
    if isinstance(payload_metrics, dict):
        sources.append(payload_metrics)
    return sources


def _scalar_metrics(metadata: dict[str, Any], keys: set[str]) -> dict[str, Any]:
    output: dict[str, Any] = {}
    for source in _metric_sources(metadata):
        for key in keys:
            value = source.get(key)
            if isinstance(value, SCALAR) or value is None:
                output[key] = value
    return {key: value for key, value in output.items() if value is not None}


def _music_checkpoints(observation: dict[str, Any]) -> list[dict[str, Any]]:
    checkpoints: list[dict[str, Any]] = []
    for event in _events(observation):
        metadata = event.get("metadata") if isinstance(event.get("metadata"), dict) else {}
        if event.get("type") != "artifact_render_checkpoint" or metadata.get("logical_path") != MUSIC_LOGICAL_PATH:
            continue
        metrics = _scalar_metrics(metadata, BOUNDED_METRIC_KEYS)
        checkpoints.append(
            {
                "sequence": event.get("sequence"),
                "stage": metadata.get("stage"),
                "rows_rendered": metadata.get("rows_rendered"),
                "rows_expected": metadata.get("rows_expected"),
                "cells_rendered": metadata.get("cells_rendered"),
                "metrics": metrics,
            }
        )
    return checkpoints


def _merge_metrics(checkpoints: list[dict[str, Any]]) -> dict[str, Any]:
    merged: dict[str, Any] = {}
    for checkpoint in checkpoints:
        for key, value in (checkpoint.get("metrics") or {}).items():
            if value is not None:
                merged[key] = value
    return merged


def _payload_ref_physical_summary(observation: dict[str, Any]) -> dict[str, Any]:
    artifact_ids = sorted(
        {
            str((event.get("metadata") or {}).get("artifact_id"))
            for event in _events(observation)
            if isinstance(event.get("metadata"), dict)
            and (event.get("metadata") or {}).get("logical_path") == MUSIC_LOGICAL_PATH
            and (event.get("metadata") or {}).get("artifact_id")
        }
    )
    refs: list[dict[str, Any]] = []
    for artifact_id in artifact_ids:
        root = Path("data/artifacts/payload_refs") / artifact_id
        if not root.exists():
            continue
        for path in root.glob("*.json"):
            raw = path.read_bytes()
            refs.append(
                {
                    "artifact_id": artifact_id,
                    "path": str(path),
                    "physical_bytes": len(raw),
                    "sha256": hashlib.sha256(raw).hexdigest(),
                    "name": path.name,
                }
            )
    by_hash: dict[str, list[dict[str, Any]]] = {}
    for ref in refs:
        by_hash.setdefault(str(ref["sha256"]), []).append(ref)
    return {
        "artifact_ids": artifact_ids,
        "physical_ref_count": len(refs),
        "physical_total_bytes": sum(int(item["physical_bytes"]) for item in refs),
        "unique_hash_count": len(by_hash),
        "duplicate_hash_groups": [[item["path"] for item in group] for group in by_hash.values() if len(group) > 1],
        "refs": refs,
    }


def _endpoint_timings(observation: dict[str, Any]) -> dict[str, Any]:
    phase1 = observation.get("phase1") if isinstance(observation.get("phase1"), dict) else {}
    timings = phase1.get("endpoint_timings") if isinstance(phase1.get("endpoint_timings"), dict) else {}
    return {
        key: {"status_code": value.get("status_code"), "elapsed_ms": value.get("elapsed_ms"), "ok": value.get("ok")}
        for key, value in timings.items()
        if isinstance(value, dict)
    }


def _summaries(observation: dict[str, Any]) -> dict[str, Any]:
    phase1 = observation.get("phase1") if isinstance(observation.get("phase1"), dict) else {}
    client = observation.get("phase1_client") if isinstance(observation.get("phase1_client"), dict) else {}
    checkpoints = _music_checkpoints(observation)
    merged = _merge_metrics(checkpoints)
    cardinality = {key: merged.get(key) for key in sorted(CARDINALITY_KEYS) if key in merged}
    digests = {key: merged.get(key) for key in sorted(DIGEST_KEYS) if key in merged}
    costs = {key: merged.get(key) for key in sorted(COST_KEYS) if key in merged}
    return {
        "task_run_id": client.get("task_run_id") or phase1.get("task_run_id"),
        "operation_id": client.get("operation_id"),
        "result_status": phase1.get("result_status"),
        "result_reason_code": phase1.get("result_reason_code"),
        "finished_at": phase1.get("finished_at"),
        "terminal_event_count": phase1.get("terminal_event_count"),
        "truth_safe_to_report_success": phase1.get("truth_safe_to_report_success"),
        "artifact_creation_started_count": phase1.get("artifact_creation_started_count"),
        "artifact_created_count": phase1.get("artifact_created_count"),
        "music_inventory_reached": phase1.get("music_inventory_reached"),
        "metadata_coverage_reached": phase1.get("metadata_coverage_reached"),
        "inventory_sufficiency_reached": phase1.get("inventory_sufficiency_reached"),
        "evidence_phase1_reached": phase1.get("evidence_phase1_reached"),
        "last_completed_stage": phase1.get("last_completed_stage"),
        "music_checkpoint_count": len(checkpoints),
        "music_stages": [item.get("stage") for item in checkpoints if item.get("stage")],
        "cardinality": cardinality,
        "digests": digests,
        "cost_model": costs,
        "bounded_metrics": merged,
        "payload_ref_physical": _payload_ref_physical_summary(observation),
        "endpoint_timings": _endpoint_timings(observation),
    }


def write_secondary(observation: dict[str, Any], *, prefix: str) -> dict[str, Any]:
    summaries = _summaries(observation)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f"{prefix}_cardinality_trace.json").write_text(
        json.dumps(
            {
                "task_run_id": summaries["task_run_id"],
                "operation_id": summaries["operation_id"],
                "cardinality": summaries["cardinality"],
                "digests": summaries["digests"],
                "stages": summaries["music_stages"],
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (OUT / f"{prefix}_render_cost_model.json").write_text(
        json.dumps(
            {
                "task_run_id": summaries["task_run_id"],
                "operation_id": summaries["operation_id"],
                "cost_model": summaries["cost_model"],
                "endpoint_timings": summaries["endpoint_timings"],
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (OUT / f"{prefix}_payload_ref_amplification.json").write_text(
        json.dumps(summaries["payload_ref_physical"], indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    (OUT / f"{prefix}_bounded_metrics_projection.json").write_text(
        json.dumps(
            {
                "task_run_id": summaries["task_run_id"],
                "bounded_metric_count": len(summaries["bounded_metrics"]),
                "bounded_metrics": summaries["bounded_metrics"],
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    return summaries


def main() -> int:
    output_name = sys.argv[1] if len(sys.argv) > 1 else "firetest5_h1c0_r2_16_public_diagnostic_rerun.json"
    prefix = "firetest5_h1c0_r2_16"
    observation = run_public(output_name)
    observation["phase0"] = {
        "runtime_executed": False,
        "task_created": False,
        "task_run_created": False,
        "operation_created": False,
        "operational_artifacts_created": False,
        "predicted_frontier": "CSV_ROW_CARDINALITY_STREAMING_DETERMINISM",
        "predicted_component": "ReadonlyAnalysisArtifactRuntimeService",
        "predicted_reason_code": "MUSIC_INVENTORY_CSV_STREAMING_BUDGET_EXCEEDED",
    }
    (OUT / output_name).write_text(json.dumps(observation, indent=2, ensure_ascii=False), encoding="utf-8")
    summaries = write_secondary(observation, prefix=prefix)
    print(
        json.dumps(
            {
                "task_run_id": summaries["task_run_id"],
                "verdict": observation.get("verdict"),
                "reason": summaries["result_reason_code"],
                "last_stage": summaries["last_completed_stage"],
                "bounded_metric_count": len(summaries["bounded_metrics"]),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
