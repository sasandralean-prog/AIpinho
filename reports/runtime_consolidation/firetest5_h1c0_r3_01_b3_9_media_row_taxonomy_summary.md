# H1C0.R3.01.B3.9 Media Row Taxonomy + Container Anatomy

## Verdict

`R3_01_B3_9_MEDIA_ROW_TAXONOMY_CONTAINER_ANATOMY_READY_WITH_REMAINING_FRONTIER`

This is not an official FireTest 5 PASS. C gate remains `CORRECTIVE_REQUIRED_BEFORE_C`.

## Implementation

- Added row applicability taxonomy for media inventory rows.
- Added candidate identity fields as `candidate_only_not_truth`.
- Added bounded file/container anatomy from magic bytes as routing/anatomy evidence, not song identity.
- Updated sufficiency to use primary-media identity denominator when row taxonomy is present.
- Updated metadata projection to recover backend/key/identity counts from bounded observations and, in final code, prefer physical backend telemetry.

## Controlled Phase-1 Diagnostic

- task_run_id: `task_run_5732815a2d3c4ed99034ac48b69b9169`
- operation_id: `op_21efc8b6e30445ed850947ce3d0d8160`
- terminal status: `blocked`
- terminal reason: `ARTIFACT_EVIDENCE_BINDING_MISSING`
- SpeakerTruth safe_to_report_success: false
- events_count: 347

## CSV Artifact

- artifact_id: `artifact_52ed4f5843e249deb16ed7a545dcd916`
- path: `C:\Dev\AIpinho\data\artifacts\universal\artifact_52ed4f5843e249deb16ed7a545dcd916_reports__firetest5__music_inventory.csv`
- rows: 2230
- columns: 46
- bytes: 1501438
- old 8 MB inline frontier observed: false

The CSV is larger than B3.8 because B3.9 adds row taxonomy, candidate identity, and file anatomy columns, and this diagnostic selected 2230 rows instead of the B3.8 1051-row music-only CSV. It is still below 8 MB. The 8,813,500-byte figure is durable checkpoint evidence, not inline CSV materialization.

## Row Taxonomy

```json
{
  "non_primary_corpus_member": 1176,
  "primary_media_without_identity_tags": 704,
  "primary_media_with_governed_identity": 214,
  "lyrics_sidecar_candidate": 121,
  "primary_media_backend_no_valid_evidence": 10,
  "artwork_candidate": 5
}
```

Primary media identity denominator:

- primary_media_row_count: 928
- governed identity rows: 214
- without identity tags: 704
- backend/no-valid evidence: 10
- primary identity ratio: 0.2306

## Container Anatomy

```json
{
  "unknown": 1176,
  "iso_bmff": 916,
  "text_lrc_candidate": 121,
  "ebml_candidate": 10,
  "png": 3,
  "jpeg": 2,
  "mp3_candidate": 2
}
```

Mismatch count: 13

## Remaining Frontiers

- `R3_01_B3_9_P1_MEDIA_PRIMARY_IDENTITY_EVIDENCE_INSUFFICIENT`
- `R3_01_B3_9_P1_ARTIFACT_EVIDENCE_BINDING_DENOMINATOR_MISMATCH`
- `R3_01_B3_9_P1_MUSIC_INVENTORY_SCOPE_INCLUDES_NON_PRIMARY_MEMBERS_IN_DIAGNOSTIC_RUN`
- `R3_01_B3_9_P2_ACCEPTED_RUNNING_PUBLIC_PROGRESS_VISIBILITY_DELAY`

## Tests

- B3.9 focused: 12 passed
- B3.5-B3.7 post-compile/public boundary: 74 passed
- Static: compileall PASS, diff-check PASS
- One broader contract group failure recorded as outside B3.9 scope: stale `.track` fixture now blocks under B3.7 target-selection semantics.

## Full Unit Attempt

`python -m pytest tests/unit -q -x` stopped at first failure outside B3.9 scope: `tests/unit/test_agent_delegation_service.py::test_delegation_request_result_parent_child_and_timeline` with `PermissionError: agent_profile_disabled` after `1 failed, 16 passed`.
