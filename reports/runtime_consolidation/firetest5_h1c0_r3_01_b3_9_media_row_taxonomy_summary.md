# H1C0.R3.01.B3.9 Media Row Taxonomy + Container Anatomy

## Verdict

`R3_01_B3_9_MEDIA_ROW_TAXONOMY_AND_CONTAINER_ANATOMY_READY`

This is not an official FireTest 5 PASS. C gate remains `CORRECTIVE_REQUIRED_BEFORE_C`.

## Completion Update

- Partial prompt work was preserved.
- Completion update applied after the full prompt sections I-P.
- File/container signature ownership is now `FileContainerSignatureService`.
- Filename candidate identity ownership is now `MediaCandidateIdentityPolicy`.
- Row taxonomy consumes those services and remains row applicability classification.
- No partial implementation was reverted; ownership and reports were corrected.

## Public Phase-1 Diagnostic

- task_run_id: `task_run_8c5a622574d847a287cc60e28c3097df`
- operation_id: `op_aa54373588d54fdea7fca3a6900e714d`
- POST status: `200`
- response mode: `accepted_running`
- elapsed_ms: `6553`
- terminal status: `blocked`
- terminal reason: `MEDIA_PRIMARY_IDENTITY_EVIDENCE_INSUFFICIENT`
- terminal blocking event count: `1`
- SpeakerTruth safe_to_report_success: `false`
- events_count: `297`

## CSV Artifact

- artifact_id: `artifact_327f349bca50420083692816c982c52d`
- logical_path: `reports/firetest5/music_inventory.csv`
- storage_ref: `data\artifacts\universal\artifact_327f349bca50420083692816c982c52d_reports__firetest5__music_inventory.csv`
- path: `C:\Dev\AIpinho\data\artifacts\universal\artifact_327f349bca50420083692816c982c52d_reports__firetest5__music_inventory.csv`
- rows: `1051`
- columns: `46`
- bytes: `678101`
- sha256: `d8b2ef8c5c42261c495c144977d512ee98fff791aaba10449125c8f450f5023c`
- status: `blocked`
- validation_status: `blocked`
- safe_to_use: `false`
- reason_code: `MEDIA_PRIMARY_IDENTITY_EVIDENCE_INSUFFICIENT`
- old 8 MB inline frontier observed: `false`

The CSV is larger than the B3.8 artifact because B3.9 adds row taxonomy, candidate identity, and file/container anatomy columns. It remains below 8 MB and is stored as an artifact file/reference. The old inline materialization frontier did not reappear.

## Row Taxonomy

```json
{
  "primary_media_without_identity_tags": 704,
  "primary_media_with_governed_identity": 214,
  "artwork_candidate": 2,
  "primary_media_backend_no_valid_evidence": 10,
  "lyrics_sidecar_candidate": 121
}
```

Primary media identity denominator:

- primary_media_row_count: `928`
- governed identity rows: `214`
- without identity tags: `704`
- backend/no-valid evidence: `10`
- primary identity ratio: `0.2306`

Sidecars/artwork remain visible and are excluded from the primary media identity denominator.

## Candidate and Anatomy Truth Policy

- filename/path/extension/container/LRC promoted to Truth: `false`
- candidate identity represented as: `candidate_only_not_truth`
- candidate_identity_available_count: `1051`
- candidate_identity_not_truth_count: `1051`
- lrc_relationship_candidate_count: `53`
- extension_container_mismatch_count: `13`
- unsupported .m4a reclassification count: `10`

## Backend Telemetry

```json
{
  "files_planned": 928,
  "files_attempted": 928,
  "files_succeeded": 918,
  "files_failed": 10,
  "physical_probe_count": 928,
  "backend_attempt_counts": {
    "mutagen": 928
  },
  "backend_success_counts": {
    "mutagen": 918
  },
  "backend_failure_counts": {
    "MEDIA_BACKEND_UNSUPPORTED_FORMAT": 10,
    "FFPROBE_NOT_AVAILABLE": 10
  },
  "evidence_records_by_backend": {
    "mutagen": 5934
  },
  "evidence_records_by_canonical_key": {
    "duration": 918,
    "codec": 916,
    "bitrate": 918,
    "sample_rate": 918,
    "channels": 918,
    "artwork": 918,
    "track_title": 214,
    "artist": 214
  },
  "semantic_identity_evidence_counts": {
    "track_title": 214,
    "artist": 214
  },
  "technical_metadata_counts": {
    "duration": 918,
    "codec": 916,
    "bitrate": 918,
    "sample_rate": 918,
    "channels": 918,
    "artwork": 918
  },
  "telemetry_projection_source": {
    "attribute_observations_projected": true,
    "execution_telemetry_present": true,
    "row_applicability_summary_present": true
  },
  "reconciles_with_evidence_records": true
}
```

## Gates

- ffprobe installed: `false`
- FireTest 5 PASS claimed: `false`
- main touched: `false`
- public polling available: `true`
- backend telemetry reconciles with EvidenceRecords: `true`

## Issue Classification

Resolved/reframed:

- `R3_01_B3_8_1_P1_MEDIA_INVENTORY_DENOMINATOR_LACKS_ROW_APPLICABILITY_TAXONOMY`

Remaining P0: none observed.

Remaining P1:

- `R3_01_B3_9_P1_PRIMARY_MEDIA_IDENTITY_EVIDENCE_INSUFFICIENT`

Remaining P2:

- `R3_01_B3_9_P2_FILENAME_CANDIDATE_IDENTITY_REQUIRES_REVIEW_PROMOTION_POLICY`
- `R3_01_B3_9_P2_LYRICS_SIDECAR_RELATIONSHIP_CANDIDATES_REQUIRE_GOVERNED_CONFIRMATION`
- `R3_01_B3_9_P2_CONTAINER_AWARE_BACKEND_EXPANSION_MAY_BE_NEEDED`
- `R3_01_B3_7_P2_ACCEPTED_RUNNING_WORKER_PROGRESS_VISIBILITY_DELAY`
- `R3_01_B3_9_P2_ARTIFACT_VALIDATION_LIMITATION_LABELS_REQUIRE_RECONCILIATION`

Remaining frontier: primary media identity evidence is still insufficient under governed evidence.
