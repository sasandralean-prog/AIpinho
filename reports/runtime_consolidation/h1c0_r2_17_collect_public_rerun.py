from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from h1c0_r2_16_collect_public_rerun import (
    CARDINALITY_KEYS,
    COST_KEYS,
    DIGEST_KEYS,
    PAYLOAD_REF_KEYS,
    _endpoint_timings,
    _events,
    _payload_ref_physical_summary,
    run_public,
)


OUT = Path(__file__).resolve().parents[2] / "reports" / "runtime_consolidation"
MUSIC_LOGICAL_PATH = "reports/firetest5/music_inventory.csv"
SCALAR = (str, int, float, bool)
CELL_LOOKUP_KEYS = {
    "cell_value_lookup_count",
    "cell_value_lookup_elapsed_ms",
    "cell_direct_lookup_count",
    "cell_index_lookup_count",
    "cell_index_hit_count",
    "cell_index_miss_count",
    "cell_fallback_scan_count",
    "cell_fallback_scan_items_examined",
    "cell_provenance_lookup_count",
    "cell_provenance_lookup_elapsed_ms",
    "cell_evidence_lookup_count",
    "cell_evidence_lookup_elapsed_ms",
    "cell_fact_lookup_count",
    "cell_fact_lookup_elapsed_ms",
    "cell_normalization_count",
    "cell_normalization_elapsed_ms",
    "index_build_elapsed_ms",
    "index_entry_count",
    "index_bytes_estimate",
    "max_lookup_depth",
    "average_lookup_us",
}
BOUNDED_KEYS = CARDINALITY_KEYS | DIGEST_KEYS | COST_KEYS | PAYLOAD_REF_KEYS | CELL_LOOKUP_KEYS | {
    "cardinality_domain",
    "progress_semantics",
}


def _metric_sources(metadata: dict[str, Any]) -> list[dict[str, Any]]:
    sources = [metadata]
    payload_metrics = metadata.get("payload_metrics")
    if isinstance(payload_metrics, dict):
        sources.append(payload_metrics)
    return sources


def _scalar_metrics(metadata: dict[str, Any]) -> dict[str, Any]:
    output: dict[str, Any] = {}
    for source in _metric_sources(metadata):
        for key in BOUNDED_KEYS:
            value = source.get(key)
            if isinstance(value, SCALAR) or value is None:
                output[key] = value
    return {key: value for key, value in output.items() if value is not None}


def _bounded_column_cost(metadata: dict[str, Any]) -> dict[str, Any]:
    value = metadata.get("column_cost_summary")
    if not isinstance(value, dict):
        return {}
    output: dict[str, Any] = {}
    for column, metrics in value.items():
        if not isinstance(metrics, dict):
            continue
        output[str(column)] = {
            key: metrics.get(key)
            for key in ("lookup_count", "total_elapsed_ms", "avg_us", "index_hit_count", "index_miss_count", "fallback_scan_count")
            if isinstance(metrics.get(key), SCALAR)
        }
    return output


def _music_checkpoints(observation: dict[str, Any]) -> list[dict[str, Any]]:
    checkpoints: list[dict[str, Any]] = []
    for event in _events(observation):
        metadata = event.get("metadata") if isinstance(event.get("metadata"), dict) else {}
        if event.get("type") != "artifact_render_checkpoint" or metadata.get("logical_path") != MUSIC_LOGICAL_PATH:
            continue
        checkpoints.append(
            {
                "sequence": event.get("sequence"),
                "stage": metadata.get("stage"),
                "rows_rendered": metadata.get("rows_rendered"),
                "rows_expected": metadata.get("rows_expected"),
                "cells_rendered": metadata.get("cells_rendered"),
                "metrics": _scalar_metrics(metadata),
                "column_cost_summary": _bounded_column_cost(metadata),
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


def _latest_column_cost(checkpoints: list[dict[str, Any]]) -> dict[str, Any]:
    for checkpoint in reversed(checkpoints):
        value = checkpoint.get("column_cost_summary")
        if isinstance(value, dict) and value:
            return value
    return {}


def _summaries(observation: dict[str, Any]) -> dict[str, Any]:
    phase1 = observation.get("phase1") if isinstance(observation.get("phase1"), dict) else {}
    client = observation.get("phase1_client") if isinstance(observation.get("phase1_client"), dict) else {}
    checkpoints = _music_checkpoints(observation)
    merged = _merge_metrics(checkpoints)
    return {
        "task_run_id": client.get("task_run_id") or phase1.get("task_run_id"),
        "operation_id": client.get("operation_id"),
        "result_status": phase1.get("result_status"),
        "result_reason_code": phase1.get("result_reason_code"),
        "finished_at": phase1.get("finished_at"),
        "terminal_event_count": phase1.get("terminal_event_count"),
        "truth_safe_to_report_success": phase1.get("truth_safe_to_report_success"),
        "music_inventory_reached": phase1.get("music_inventory_reached"),
        "metadata_coverage_reached": phase1.get("metadata_coverage_reached"),
        "inventory_sufficiency_reached": phase1.get("inventory_sufficiency_reached"),
        "evidence_phase1_reached": phase1.get("evidence_phase1_reached"),
        "last_completed_stage": phase1.get("last_completed_stage"),
        "music_checkpoint_count": len(checkpoints),
        "music_stages": [item.get("stage") for item in checkpoints if item.get("stage")],
        "cardinality": {key: merged.get(key) for key in sorted(CARDINALITY_KEYS) if key in merged},
        "digests": {key: merged.get(key) for key in sorted(DIGEST_KEYS) if key in merged},
        "cost_model": {key: merged.get(key) for key in sorted(COST_KEYS) if key in merged},
        "lookup_cost_model": {key: merged.get(key) for key in sorted(CELL_LOOKUP_KEYS) if key in merged},
        "column_cost_summary": _latest_column_cost(checkpoints),
        "bounded_metrics": merged,
        "payload_ref_physical": _payload_ref_physical_summary(observation),
        "endpoint_timings": _endpoint_timings(observation),
    }


def write_secondary(observation: dict[str, Any], *, prefix: str) -> dict[str, Any]:
    summaries = _summaries(observation)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f"{prefix}_lookup_cost_model.json").write_text(
        json.dumps(
            {
                "task_run_id": summaries["task_run_id"],
                "operation_id": summaries["operation_id"],
                "lookup_cost_model": summaries["lookup_cost_model"],
                "cost_model": summaries["cost_model"],
                "cardinality": summaries["cardinality"],
                "digests": summaries["digests"],
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (OUT / f"{prefix}_column_cost_profile.json").write_text(
        json.dumps(
            {
                "task_run_id": summaries["task_run_id"],
                "operation_id": summaries["operation_id"],
                "column_cost_summary": summaries["column_cost_summary"],
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (OUT / f"{prefix}_payload_ref_public_validation.json").write_text(
        json.dumps(summaries["payload_ref_physical"], indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return summaries


def main() -> int:
    output_name = sys.argv[1] if len(sys.argv) > 1 else "firetest5_h1c0_r2_17_public_diagnostic_rerun.json"
    prefix = "firetest5_h1c0_r2_17"
    observation = run_public(output_name)
    observation["phase0"] = {
        "runtime_executed": False,
        "task_created": False,
        "task_run_created": False,
        "operation_created": False,
        "operational_artifacts_created": False,
        "predicted_frontier": "CSV_CELL_VALUE_EXTRACTION_INDEXED_LOOKUP",
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
                "lookup_cost_model": summaries["lookup_cost_model"],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
