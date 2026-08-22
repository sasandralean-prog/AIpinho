# H1C0.R3.01.B3.8.1 — CSV Generation & Semantic Row Autopsy

## Verdict

`R3_01_B3_8_1_CSV_SEMANTIC_ROW_AUTOPSY_COMPLETE`

This was report-only. No production code, tests, config, ffprobe installation, main merge, C gate, or official FireTest 5 PASS run was performed.

## Baseline

- Branch: `agent/codex/r3-01-b3-8-1-csv-semantic-row-autopsy`
- Source B3.8 report commit: `1c52769dbfddbd529c634be1acc4a44f9a8f3216`
- Canonical main baseline: `d76a1a21ceeef00f953d87a6aca07dcb6635c834`
- Source task_run_id: `task_run_02e3ebb7d7ec4afdae76117876639ba3`
- Source operation_id: `op_e6bed7d851254cccb7093cdc3bb5774b`
- Source terminal reason: `MEDIA_IDENTITY_EVIDENCE_INSUFFICIENT`
- SpeakerTruth safe_to_report_success: `False`

## CSV Artifact

- artifact_id: `artifact_e5512dcd48c54e8f8018c6f38c4a24e4`
- logical path: `reports/firetest5/music_inventory.csv`
- runtime CSV path: `C:\Dev\AIpinho\data\artifacts\universal\artifact_e5512dcd48c54e8f8018c6f38c4a24e4_reports__firetest5__music_inventory.csv`
- rows: `1051`
- bytes: `403647`
- status: `blocked`
- safe_to_use: `False`
- old 8 MB inline frontier: `not observed`

## Row Autopsy

Extension distribution:

```json
{
  "m4a": 921,
  "jpg": 2,
  "mp3": 5,
  "mp4": 2,
  "lrc": 121
}
```

Row classification:

```json
{
  "observed_media_without_governed_identity_tags": 704,
  "observed_media_with_governed_identity": 214,
  "sidecar_or_artwork_without_media_identity_contract": 123,
  "media_candidate_no_valid_mutagen_evidence": 10
}
```

Denominator models:

```json
{
  "all_rows": {
    "denominator": 1051,
    "identity": 214,
    "without_identity": 837,
    "identity_ratio": 0.2036
  },
  "media_extension_rows_m4a_mp3_mp4": {
    "denominator": 928,
    "identity": 214,
    "without_identity": 714,
    "identity_ratio": 0.2306
  },
  "observed_media_rows": {
    "denominator": 918,
    "identity": 214,
    "without_identity": 704,
    "identity_ratio": 0.2331
  },
  "sidecar_artwork_rows": {
    "denominator": 123,
    "identity": 0,
    "without_identity": 123,
    "identity_ratio": 0.0
  }
}
```

Interpretation: the current `MEDIA_IDENTITY_EVIDENCE_INSUFFICIENT` block is evidence-backed, not a mere report artifact. Only 214/1051 rendered rows have governed semantic identity evidence. Excluding `.lrc`/`.jpg` sidecar/artwork rows from the identity denominator would improve the ratio from 20.36% to 23.06% over media extensions, but it would not clear Phase 1 because 704 observed media rows still lack governed title/artist/album/album_artist evidence.

## Evidence Autopsy

- checkpoint_count: `918`
- checkpoint_bytes_total: `8813500`
- EvidenceRecords: `5934`
- backend_counts: `{'mutagen': 5934}`
- canonical_key_counts: `{'codec': 916, 'duration': 918, 'bitrate': 918, 'sample_rate': 918, 'channels': 918, 'artwork': 918, 'track_title': 214, 'artist': 214}`
- identity EvidenceRecords: `428`
- entities with identity EvidenceRecords: `214`
- CSV rows with identity values: `214`

Checkpoint evidence and CSV identity rows agree for identity-bearing entities: `214 == 214`. The identity path is therefore not lost at checkpoint/CSV binding for the rows that have governed Mutagen identity claims.

## Storage Size Autopsy

The produced CSV itself is not larger than 8 MB:

- CSV bytes: `403647`
- CSV exceeds old 8 MB inline budget: `false`
- checkpoint bytes total: `8813500`
- payload_refs total bytes: `14920628`
- payload_ref count: `919`
- largest payload_ref: `7f1b8b1557f7d3b16d3c524b8877114fc67463403031688f4c6b63247d7217fa.json`
- largest payload_ref bytes: `6107128`
- largest payload_ref role: selected entity/corpus observation payload, not the CSV artifact
- events.json bytes: `1169181`
- result.json bytes: `118399`
- run.json bytes: `97414`
- task-run directory total bytes: `16306462`

The number above 8 MB belongs to durable checkpoint/evidence storage, not inline CSV materialization. After Slice 4, `max_materialized_observation_bytes` governs the inline retained materialization envelope; checkpointed evidence is governed separately by `max_checkpointed_observation_bytes = 64000000`. B3.8 stayed within the checkpoint budget and did not reintroduce the old inline 8 MB frontier.

## Row Categories

- `observed_media_with_governed_identity`: valid claim-level identity evidence exists.
- `observed_media_without_governed_identity_tags`: Mutagen produced technical metadata, but no governed title/artist/album/album_artist tags.
- `media_candidate_no_valid_mutagen_evidence`: 10 `.m4a` files returned no Mutagen object in bounded inspection; they were not converted to success.
- `sidecar_or_artwork_without_media_identity_contract`: `.lrc`/`.jpg` rows are corpus-visible but currently counted in the same media identity denominator.

## Sufficiency Policy Finding

Current code requires full identity coverage over rendered rows. This preserves Truth: filename/path/extension do not satisfy semantic identity, and generic `file:` row evidence does not satisfy claim identity.

The policy is stricter than the current artifact taxonomy. The CSV contains mixed row applicability classes, but the denominator treats every rendered row as requiring semantic media identity evidence.

## Issues

Remaining P0: none observed.

Remaining P1:

- `R3_01_B3_8_1_P1_MEDIA_IDENTITY_EVIDENCE_SPARSITY_PHASE1_FRONTIER`
- `R3_01_B3_8_1_P1_MEDIA_INVENTORY_DENOMINATOR_LACKS_ROW_APPLICABILITY_TAXONOMY`

Remaining P2:

- `R3_01_B3_8_1_P2_MEDIA_METADATA_SUMMARY_BACKEND_IDENTITY_PROJECTION_INCONSISTENT`
- `R3_01_B3_8_1_P2_UNSUPPORTED_M4A_CLASSIFICATION_NEEDS_CONTENT_SIGNATURE_DETAIL`

## C Gate

`CORRECTIVE_REQUIRED_BEFORE_C`.

The current evidence does not prove that installing ffprobe is the next correct step. The dominant blocker is semantic identity sufficiency and row applicability taxonomy. ffprobe may help the 10 unsupported `.m4a` cases, but it is not proven to solve the 704 observed media rows without title/artist tags.

## Recommended Next Mission

`H1C0.R3.01.B3.9 — Media Inventory Row Applicability Taxonomy & Semantic Identity Sufficiency Policy Correction`
