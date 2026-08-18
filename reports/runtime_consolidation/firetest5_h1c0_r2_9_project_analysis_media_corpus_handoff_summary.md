# H1C0.R2.9 — ProjectAnalysis Media Corpus Handoff & Public Artifact Runtime Continuation

## Verdict

`FIRETEST5_H1C0_R2_9_PROJECT_ANALYSIS_MEDIA_CORPUS_HANDOFF_BLOCKED_WITH_CORE_FIX_VALIDATED`

FireTest 5 remains `NOT_READY`.

## Objective

Separate source-readable ProjectAnalysis from inventory-eligible media corpus handoff. A media file is not source-readable, but a governed library/corpus entity can be eligible for inventory artifact runtime.

## What Changed

- `ProjectAnalysisRequest` now carries `workspace_context`.
- Public runtime passes the extracted `workspace_context` into ProjectAnalysis.
- `FileSelectionService` now records root role and distinguishes:
  - source-readable selection;
  - inventory-eligible entity selection.
- Media files blocked by text-read extension policy under a governed library/corpus root are recorded as `EXTENSION_NOT_ALLOWED_FOR_SOURCE_READING`, not as invalid inventory entities.
- `ProjectAnalysisService` can return a safe partial `MEDIA_CORPUS_ROOT_HANDOFF_READY` result when no source-readable files exist but inventory-eligible corpus entities do.
- `ProjectAnalysisResult` now exposes `corpus_handoff`.
- CVL recognizes media corpus handoff and root-role/file-selection mismatch frontiers.

## Public Rerun Result

The clean Phase 0→6 rerun after backend restart proved the core fix:

- Phase 1 returned `accepted_running`.
- ProjectAnalysis no longer blocked with generic `PROJECT_ANALYSIS_DEGRADED`.
- ProjectAnalysis returned `partial`, `MEDIA_CORPUS_ROOT_HANDOFF_READY`.
- `inventory_eligible_entities_count=200`.
- `media_entity_candidates_count=200`.
- `source_rejected_inventory_eligible_count=200`.
- Artifact runtime was reached.
- `phase1_discovery.md` was created.
- `project_inventory.md` was created.
- `music_inventory.csv` was reached.

The wave remains blocked because the run stalled after:

`artifact_creation_started` for `reports/firetest5/music_inventory.csv`

with:

- `result.json` absent;
- `/result` initially `404`;
- endpoints later timing out;
- `finished_at=null`;
- `terminal_event_count=0`.

Phase 2–6 were not called and are treated as `skipped_due_to_prior_block`.

## Tests

- Focused ProjectAnalysis/FileSelection/CVL tests: `30 passed`.
- Expanded regressions across runtime, artifact registry, metadata service-equivalent, phase progression, and store: `92 passed`.
- `py_compile`: PASS for changed Python files.

Some prompt-listed regression filenames were not present in this checkout; the existing matching regression set was run instead.

## Anti-Hardcode

No production decision branch was added for a task id, operation id, local project path, FireTest-only success path, artifact filename success, or media extension as metadata truth. Media extensions are used only as configurable routing hints for inventory eligibility and capability routing.

## Why No False Success

The handoff result is `partial`, not success. It allows artifact runtime to evaluate the governed corpus inventory, but Validation, Completion, and Speaker Truth still decide the terminal truth. Since the run did not produce a terminal result, FireTest 5 remains not ready.

## Next Recommendation

Repair slice:

`H1C0.R2.10 — Music Inventory Artifact Worker Stall Terminal Result After Corpus Handoff`

Scope should be narrow: after `MEDIA_CORPUS_ROOT_HANDOFF_READY`, `music_inventory.csv` entering `artifact_creation_started` must produce `artifact_created`, `artifact_partial`, `artifact_blocked`, `artifact_failed`, or a terminal `TaskRunResult`. Endpoints must stay lightweight and `/result` must not remain 404 or timeout as final state.
