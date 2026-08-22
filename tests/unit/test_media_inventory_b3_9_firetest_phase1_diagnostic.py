from __future__ import annotations

import json
from pathlib import Path


REPORT = Path("reports/runtime_consolidation/firetest5_h1c0_r3_01_b3_9_public_phase1_observation.json")


def test_b3_9_phase1_diagnostic_preserves_speakertruth_and_avoids_old_inline_8mb_frontier() -> None:
    payload = json.loads(REPORT.read_text(encoding="utf-8"))

    assert payload["terminal"]["speaker_truth_safe_to_report_success"] is False
    assert payload["music_inventory_csv"]["old_8mb_inline_frontier_observed"] is False
    assert payload["music_inventory_csv"]["bytes"] < 8_000_000
    assert payload["music_inventory_csv"]["storage_mode"] == "artifact_file_reference_payload_ref_manifest"


def test_b3_9_phase1_diagnostic_projects_row_taxonomy_and_candidate_not_truth() -> None:
    payload = json.loads(REPORT.read_text(encoding="utf-8"))
    row_taxonomy = payload["row_taxonomy"]

    assert row_taxonomy["row_class_counts"]["primary_media_with_governed_identity"] == 214
    assert row_taxonomy["row_class_counts"]["primary_media_without_identity_tags"] == 704
    assert row_taxonomy["row_class_counts"]["lyrics_sidecar_candidate"] == 121
    assert row_taxonomy["row_class_counts"]["primary_media_backend_no_valid_evidence"] == 10
    assert row_taxonomy["primary_media_denominator"] == 928
    assert row_taxonomy["candidate_identity_available_count"] == 2230


def test_b3_9_artifact_metadata_projection_explains_safety_and_digest_availability() -> None:
    payload = json.loads(REPORT.read_text(encoding="utf-8"))
    projection = payload.get("artifact_metadata_projection")

    assert projection, "B3.9 report must project artifact metadata safety and digest evidence"
    by_path = {item["logical_path"]: item for item in projection["artifacts"]}
    music = by_path["reports/firetest5/music_inventory.csv"]
    assert music["status"] == "blocked"
    assert music["safe_to_use"] is False
    assert music["reason_code"] == "ARTIFACT_EVIDENCE_BINDING_MISSING"
    assert music["sha256"]
    assert music["storage_ref_status"] in {"local_artifact_file", "not_projected_by_runtime_payload"}
