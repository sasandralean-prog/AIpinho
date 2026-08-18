# H1C0.R2.1 - Semantic Evidence Coherence, Evidence Package, Cognition Projection & Runtime Truth Cleanup

## Verdict

`FIRETEST5_H1C0_R2_1_SEMANTIC_EVIDENCE_COHERENCE_BLOCKED`

The wave improved structural coherence and public observability, but the final public proof still blocks in Phase 1 because the music inventory did not receive governed corpus/library rows.

## Objective

Close residual H1C0.R2 inconsistencies: evidence refs projected in endpoints, coherent row-level validation, valid evidence package profiling, explainable cognition projection, lightweight endpoints, and conservative Speaker Truth.

## Scope And Non-goals

Executed scope:

- row-level validation for already-materialized CSV content;
- projection of evidence refs, row evidence coverage, and row validation summary;
- base64 ZIP decoding before semantic profile validation;
- lightweight summary/truth/session/artifacts for terminal blocked runs;
- general bare Windows path extraction fix for the standalone Portuguese connector `e`;
- clean public Phase 0->6 run with stop on first blocked phase.

Not done:

- no bypass;
- no hardcode for project/path/artifact/extension;
- no renderer filesystem observation;
- no RelationshipCandidate promotion to Truth;
- no Validation/Completion/Speaker Truth relaxation;
- no Phase 2 execution after Phase 1 blocked.

## Changed Files

- `src/aipinho/schemas/artifacts/row_semantic_validation.py`
- `src/aipinho/services/artifacts/row_level_semantic_validation_service.py`
- `src/aipinho/services/governance/runtime/readonly_analysis_artifact_runtime_service.py`
- `src/aipinho/services/artifacts/artifact_semantic_contract_service.py`
- `src/aipinho/services/artifacts/universal_artifact_registry_service.py`
- `src/aipinho/services/artifacts/artifact_runtime_service.py`
- `src/aipinho/services/runtime/universal_task_session_service.py`
- `src/aipinho/services/runtime/task_runtime_service.py`
- `src/aipinho/services/runtime/task_run_store.py`
- `src/aipinho/services/cvl/cognitive_validation_laboratory_service.py`
- `config/workspaces/workspace_resolution_policy.yaml`
- `tests/unit/test_path_extraction_service.py`
- `tests/unit/test_row_level_semantic_validation.py`
- `tests/unit/test_artifact_evidence_ref_projection.py`
- `tests/unit/test_universal_task_session_service.py`
- `tests/unit/test_observational_cognition_projection_coherence.py`
- `tests/unit/test_capability_status_projection_coherence.py`
- `tests/unit/test_runtime_truth_lightweight_projection.py`
- `tests/unit/test_terminal_finished_at_projection.py`
- `tests/unit/test_phase_progression_after_block.py`
- `tests/unit/test_evidence_phase1_semantic_package.py`
- `tests/unit/test_cvl_observational_binding_frontiers.py`

## Implemented Fixes

- Added canonical row semantic validation schemas and service.
- Separated rendered columns from missing row values and evidence coverage.
- Treated `name` and `filename` as semantic aliases for file identity, removing the false missing-column finding.
- Projected `row_validation_summary`, `row_evidence_coverage`, and bounded `evidence_refs` into artifact endpoint rows.
- Validated `evidence_phase1.zip` as a real ZIP when runtime content is base64 encoded.
- Prevented `UniversalArtifactRegistryService.by_task()` from scanning the legacy global registry for `task_run_*` lookups with no artifact index.
- Prevented `UniversalTaskSessionService.get_session()` from building heavy timelines for terminal blocked runs.
- Kept Runtime Truth lightweight and conservative for terminal blocked runs.
- Cohered terminal run/result state before result persistence.
- Fixed general path extraction policy so `C:\Project e ... D:\Library` does not become one invalid workspace path.

## Public Final Run

- Session: `firetest5_h1c0_r2_1_clean_phase0_to_6_20260813_155212`
- TaskRun: `task_run_6aab93c7b31f486b882b7d2aa34591d8`
- Client response: `accepted_running` in `5905` ms
- Run/result: `BLOCKED` / `blocked`
- `finished_at`: `2026-08-13T18:56:11.539816+00:00`
- Speaker Truth `safe_to_report_success`: `False`
- Terminal events: `1` `['run_blocked']`
- Artifacts: `4`
- Endpoint timings: `{'summary': 62, 'truth': 16, 'events': 14, 'artifacts': 360, 'session': 31}`

### music_inventory.csv

- status: `blocked`
- semantic_contract_status: `partial`
- reason_code: `MUSIC_INVENTORY_PARTIAL_EVIDENCE`
- selected_rows: `0`
- bound_rows: `0`
- evidence_ref_count: `0`
- row evidence status: `missing`
- row validation status: `blocked`
- missing_columns: `[]`
- safe_to_use: `False`

### evidence_phase1.zip

- status: `ready`
- semantic_contract_status: `satisfied`
- safe_to_use: `True`
- size_bytes: `1684771`

## Interpretation

H1C0.R2.1 removed important incoherences: the artifact no longer stays ambiguous, terminality is single, endpoints are lightweight, and the CSV is not confused with a findings report. The rendered `filename` column now satisfies the `filename/name` semantic intent without a false schema failure.

The remaining blocker is real: `MEDIA_CORPUS_ENTITY_SELECTION_EMPTY` / `ARTIFACT_EVIDENCE_BINDING_MISSING`. The public runtime still lacks structured corpus/library root binding that can produce `ObservedEntity` rows with `source_root_role=library/corpus`. Producing rows without that would require renderer observation or a parallel scanner, so the run correctly blocks.

## Tests

- Integrated final suite: `103 passed in 111.76s`.
- `py_compile`: PASS for changed production files.
- Anti-hardcode audit: PASS. Only existing CVL structural names appeared: `FireTestProfile`, `FireTestSuite`, `FireTestLaboratoryService`.

## Queue And Storage

- Queue after run remained clean according to the public observation file.
- `run.json` stayed lightweight enough for the current public run.
- No large endpoint payload was required for summary/truth/artifacts/session projections.

## Remaining Gaps

- Public structured corpus/library root binding is still missing.
- `ObservationGoal` for `media_corpus_inventory` does not yet produce corpus entities on the public path.
- `media_metadata_capability.status = not_configured` remains honest and limits rich metadata.
- Relationship cognition remains not available with causal reason; it is not Truth.

## Next Recommendation

`H1C0.R2.2 - Public Corpus Root Binding & ObservedEntity Role Projection`

Goal: let the public request carry distinct project and corpus roots as governed references, producing `ObservedEntity` rows with correct `source_root_role` before renderer materialization. This should stay general: no path-specific rule, no artifact-specific shortcut, no extension-as-truth.

## Why There Was No Bypass

The renderer continued to consume only governed payload/profile/evidence. When row binding was missing, it blocked `music_inventory.csv` with `MUSIC_INVENTORY_PARTIAL_EVIDENCE` instead of scanning the filesystem or inventing metadata.

## Why There Was No False Success

Validation and Completion stayed blocked; Speaker Truth stayed `safe_to_report_success=false`; Phases 2-6 were `skipped_due_to_prior_block`.
