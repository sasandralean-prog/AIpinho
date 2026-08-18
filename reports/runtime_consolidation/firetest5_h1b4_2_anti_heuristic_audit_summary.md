# FireTest 5 - H1B4.2 Anti-Heuristic Audit & Public Path Evidence Propagation

## Verdict

`FIRETEST5_H1B4_2_PUBLIC_PROPAGATION_BLOCKED`

The anti-heuristic audit found and corrected the main conceptual risks introduced around H1B4/H1B4.1. The service-equivalent path now shows generic media metadata evidence through the governed capability chain, but the public `/api/v1/chat` path is still not fit as a reliable validation surface because the run timed out at the client, produced very large runtime payloads, and left lifecycle/summary state inconsistent.

This is not `FIRETEST5_READY`.

## Scope

This wave did not implement H1B5, did not add sidecar relationships, did not add a new parser, did not write directly to CSV, and did not relax Validation, Completion, or Speaker Truth.

The goal was to ensure the Runtime remains generic:

```text
contract
-> entity
-> capability
-> observation boundary
-> evidence
-> coverage
-> validation
-> completion
-> speaker truth
```

## Files Changed

- `src/aipinho/schemas/artifacts/contract_perception.py`
- `src/aipinho/services/artifacts/contract_driven_perception_service.py`
- `src/aipinho/capabilities/media_metadata/descriptor.py`
- `src/aipinho/capabilities/media_metadata/adapter.py`
- `src/aipinho/capabilities/media_metadata/normalizer.py`
- `tests/unit/test_media_metadata_capability_pack.py`
- `tests/unit/test_contract_driven_perception_service.py`
- `tests/unit/test_cognitive_validation_laboratory_service.py`

## Anti-Heuristic Findings

Full finding table:

`reports/runtime_consolidation/firetest5_h1b4_2_anti_heuristic_findings.json`

Summary:

```text
total_findings: 173
GENERIC_RUNTIME_OK: 32
CAPABILITY_PACK_OK: 32
ARTIFACT_CONTRACT_OK: 28
TEST_FIXTURE_OK: 81
```

The active high-risk leaks were corrected before final classification:

- `library_root/corpus_root` no longer promotes a file to `audio_track_candidate`.
- `media_metadata_reader` no longer declares `observations` as a produced media metadata attribute.
- degraded attribute label normalization now creates an explicit trace.
- `native_minimal` is covered by tests that prevent extension-only metadata inference.

## Corrections Made

### 1. Media Asset Hypothesis Instead Of Audio Truth

Before:

```text
corpus_file from library_root
-> audio_track_candidate
```

After:

```text
corpus_file
-> media_asset_candidate hypothesis
-> capability precondition
-> backend observation
-> EvidenceRecord or typed failure
```

The original entity remains `corpus_file`. The observation execution reference may use `media_asset_candidate`, but this is an operational hypothesis, not a truth claim.

### 2. `observations` Removed From Technical Metadata Capability

`media_metadata_reader` now produces technical/descriptive media fields only:

```text
codec
container
bitrate
sample_rate
channels
duration
artwork
metadata
```

`observations` remains unresolved unless a semantic review, diagnostic note, artifact contract, or other explicit authority produces it. A human CSV column no longer forces a technical backend to invent a note.

### 3. Attribute Identity Trace

Added `AttributeIdentityNormalizationTrace`.

Each normalized attribute can now explain:

```text
raw_label
display_label
normalized_label
canonical_key
match_method
known_alias_source
confidence
loss_tolerance_used
mojibake_detected
accepted
reason_code
```

Example observed in the H1B4.2 diagnostic:

```json
{
  "raw_label": "extens?o",
  "display_label": "extensão",
  "normalized_label": "extens_o",
  "canonical_key": "extension",
  "match_method": "loss_tolerant_alias",
  "confidence": 0.82,
  "loss_tolerance_used": true,
  "mojibake_detected": true,
  "reason_code": "LOSS_TOLERANT_ALIAS_MATCH"
}
```

### 4. Native Minimal Guardrails

Added tests proving fake files do not produce technical media evidence by extension:

```text
fake.m4a containing text -> no metadata evidence
fake.mp3 containing text -> no metadata evidence
fake.lrc containing lyrics -> no metadata evidence
fake.jpg containing arbitrary bytes -> no metadata evidence
```

## Service-Equivalent Diagnostic

Artifact:

`reports/runtime_consolidation/firetest5_h1b4_2_service_equivalent_diagnostic.json`

Key result:

```text
candidate_entity_count: 2272
selected_entity_count: 1051
selected_root_roles: [library_root]
selected_entity_roles: [corpus_file]
media_metadata_capability.status: available
selected_backend: mutagen
evidence_records_created: 8068
attributes_observed:
  artwork
  bitrate
  channels
  codec
  container
  duration
  metadata
  sample_rate
attributes_missing: []
```

Coverage:

```text
structural_coverage: 1.0
entity_coverage: 1.0
attribute_coverage: 0.9167
capability_coverage: 0.9167
evidence_coverage: 0.9167
semantic_confidence: 0.7
is_semantically_complete: false
```

Remaining service-equivalent blocker:

```text
missing_attributes: [observations]
missing_capabilities: [observations]
blocking_reasons: [CAPABILITY_REJECTED]
```

Interpretation:

The media metadata capability works through the canonical path. The remaining semantic gap is not media parsing; it is the authority for artifact/diagnostic observations.

## Public Path Diagnostic

Artifacts:

`reports/runtime_consolidation/firetest5_h1b4_2_public_path_diagnostic.json`
`reports/runtime_consolidation/firetest5_h1b4_2_public_result_extract.json`

Observed:

```text
POST /api/v1/chat timeout: 1200 seconds
task_run_id: task_run_269f80dba2c94c0cb6774e47b3ea85f9
run.json: 333 MB
events.json: 254 MB
result.json: 564 MB
run.status: running
result.status: blocked
```

The public result does contain the H1B4.2 capability state:

```text
media_metadata_capability.status: partial
selected_backend: mutagen
successful_backends: [mutagen, native_minimal]
missing_dependency: [ffprobe]
evidence_records_created: 8068
attributes_observed:
  artwork
  bitrate
  channels
  codec
  container
  duration
  metadata
  sample_rate
attributes_missing:
  observations
```

However, Validation still blocked with artifact-level findings:

```text
artifact_material_kind_mismatch
artifact_collection_items_missing
ATTRIBUTE_NOT_OBSERVED:observations
ATTRIBUTE_NOT_OBSERVED:codec
ATTRIBUTE_NOT_OBSERVED:bitrate
ATTRIBUTE_NOT_OBSERVED:sample_rate
ATTRIBUTE_NOT_OBSERVED:channels
ATTRIBUTE_NOT_OBSERVED:duration
ATTRIBUTE_NOT_OBSERVED:artwork
ATTRIBUTE_NOT_OBSERVED:metadata
ATTRIBUTE_NOT_OBSERVED:container
artifact_schema_field_missing:name
artifact_schema_field_missing:extension
artifact_schema_field_missing:size bytes
...
```

Interpretation:

Evidence exists in public Runtime output, but artifact semantic validation/rendering/profile binding still does not consume it coherently. The public path also has an observability/lifecycle performance gap: heavy payloads make chat response, summary, and cancellation unreliable.

## Tests Executed

```text
python -m pytest tests/unit/test_media_metadata_capability_pack.py tests/unit/test_contract_driven_perception_service.py tests/unit/test_cognitive_validation_laboratory_service.py -q
42 passed, 1 skipped

python -m pytest tests/unit/test_runtime_doctor_service.py tests/unit/test_validation_gate_service.py tests/unit/test_speaker_service.py tests/unit/test_h1c1_conversation_runtime_truth.py -q
30 passed

python -m pytest tests/governance/test_no_legacy_operational_bypass.py -q
2 passed
```

## Remaining Gaps

### H1B4.2 Public Propagation Gap

The canonical evidence exists, but the public artifact validation path still reports missing artifact/schema/attribute semantics. Next wave should focus on:

```text
EvidenceRecord
-> AttributeObservation
-> ArtifactSemanticProfile
-> renderer/materialized artifact
-> ArtifactSemanticValidation
```

without letting renderer call backend or fabricate values.

### Observability Performance Gap

The public task run persisted hundreds of MB:

```text
run.json: 333 MB
events.json: 254 MB
result.json: 564 MB
```

This causes:

```text
PUBLIC_CHAT_TIMEOUT
PUBLIC_SUMMARY_PAYLOAD_TOO_LARGE
OBSERVABILITY_PERFORMANCE_GAP
```

The Runtime needs lightweight indexes/summaries for public endpoints, not full embedded perception/evidence payloads in every surface.

### Lifecycle Coherence Gap

The public run had:

```text
run.status: running
result.status: blocked
finished_at: null
```

An official cancel request also timed out. This should be handled as a lifecycle/summary coherence issue, not masked.

### H1B5 Still Needed

The corpus contains heterogeneous assets:

```text
m4a
mp3
mp4
lrc
jpg
```

H1B4.2 deliberately did not classify sidecars. H1B5 should introduce relationship-aware media roles without extension magic:

```text
media_asset_candidate
audio_track_observed
lyric_sidecar_candidate
artwork_sidecar_candidate
video_related_asset
relationship evidence
```

## Why This Was Not A Bypass

- No FireTest-specific branch was added.
- No local path was hardcoded.
- No CSV renderer was taught to parse media.
- No backend writes artifact values directly.
- No Validation/Completion/Speaker Truth rule was relaxed.
- `mutagen` and `native_minimal` remain observational mechanisms only.
- Evidence remains the bridge between observation and truth.

## Recommendation

Do not move to FireTest green yet.

Recommended next step:

```text
H1B4.3 - Public Evidence Propagation & Lightweight Runtime Summaries
```

Goal:

```text
EvidenceRecord exists in public Runtime
-> ArtifactSemanticProfile binds it by artifact/entity/attribute
-> renderer consumes AttributeObservation only
-> validation sees the same semantic state
-> summary endpoint returns lightweight status without loading 500 MB
```

Only after that should H1B5 sidecar/relationship modeling proceed.
