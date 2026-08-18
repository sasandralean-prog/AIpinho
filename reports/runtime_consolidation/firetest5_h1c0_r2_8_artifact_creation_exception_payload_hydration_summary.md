# H1C0.R2.8 - Public Artifact Creation Exception & Payload Ref Hydration Hardening

## Verdict

`FIRETEST5_H1C0_R2_8_ARTIFACT_EXCEPTION_PAYLOAD_HYDRATION_BLOCKED_WITH_CORE_FIX_VALIDATED`

FireTest 5 remains `NOT_READY`.

This is a nuanced blocked result: the R2.8 core exception frontier was repaired and exercised, but the latest clean public rerun after backend restart stopped earlier at `PROJECT_ANALYSIS_DEGRADED`, before artifact runtime could re-prove metadata/inventory sufficiency publicly.

## Objective

Harden the public artifact runtime exception boundary around accepted workers, payload/ref hydration, artifact registry projection, artifact creation state, and endpoint/result coherence. The wave did not attempt to pass Phase 1 by relaxing semantic policy.

## Non-Goals Preserved

- No metadata sufficiency policy changes.
- No metadata reader implementation.
- No root binding or entity selection rewrite.
- No renderer observation or filesystem scan by renderer.
- No relationship truth promotion.
- No Phase 2 execution after Phase 1 blocked.
- No FireTest READY claim.
- No global timeout increase.
- No project/path/artifact/task-id hardcode in production logic.

## Root Cause

The R2.7 public blocker `ARTIFACT_CREATION_EXCEPTION_AFTER_ACCEPTED_RUNNING` was traced to artifact registry persistence, not metadata:

- `data/artifacts/manifests/artifact_registry.json` is `2,147,483,647` bytes.
- The legacy registry is invalid JSON, failing around char `2111892207`.
- `UniversalArtifactRegistryService.create()` called `ArtifactRegistryRepository.save()`.
- `save()` called `list()` and attempted to parse the monolithic legacy registry before writing a new artifact.
- That raised a JSON parsing exception after `artifact_creation_started`, preventing the first artifact from completing.

## Changed Files

- `src/aipinho/services/artifacts/artifact_interaction_core.py`
- `src/aipinho/services/governance/runtime/readonly_analysis_artifact_runtime_service.py`
- `src/aipinho/services/runtime/task_run_store.py`
- `src/aipinho/services/runtime/task_queue_service.py`
- `src/aipinho/services/cvl/cognitive_validation_laboratory_service.py`
- `src/aipinho/services/cvl/cognitive_readiness_service.py`
- `tests/unit/test_artifact_registry_payload_hydration_boundary.py`
- `tests/unit/test_accepted_running_artifact_worker_terminalization_guard.py`
- `tests/unit/test_cvl_artifact_worker_terminalization_frontier.py`

## What Changed

### Artifact Registry Projection

`ArtifactRegistryRepository` now writes sharded per-artifact manifests under `data/artifacts/manifests/by_artifact/` and a lightweight `artifact_registry_index.json`. Oversized or invalid legacy `artifact_registry.json` is preserved as evidence but skipped for new writes, with a diagnostic file instead of a parse attempt.

### Exception Boundary

Artifact creation exceptions now get sanitized envelopes with component/function/stage, artifact event context, and stack trace payload refs. Endpoint/result payloads stay bounded.

### Payload/Hydration Coherence

The immediate hydration failure was the legacy registry JSON boundary. The fix prevents each new artifact save from hydrating/parsing that giant legacy projection. Large payloads remain referenced rather than inline-expanded.

### Artifact Terminality

The R2.7 guard was strengthened:

- guard-created results now set `finished_at`;
- `TaskRunStore.terminalize_if_artifact_creation_stalled()` can terminalize active runs with `artifact_creation_started` and no terminal artifact/result;
- `TaskQueueService.reconcile()` invokes that store guard for active runs;
- generic `TASKRUN_LIFECYCLE_TIMEOUT` no longer steals authority when an artifact-specific in-progress state exists.

### CVL / Phase 0

CVL now recognizes unreadable/oversized legacy artifact registry projection and payload hydration boundary frontiers. The latest Phase 0 still predicted `TRUTH_READINESS`, so calibration remains imperfect and is a P1 follow-up.

## Tests

Passed:

- `python -m pytest tests/unit/test_artifact_registry_payload_hydration_boundary.py -q` -> 2 passed
- `python -m pytest tests/unit/test_accepted_running_artifact_worker_terminalization_guard.py -q` -> 8 passed
- Integrated R2.7/R2.8/result/CVL set -> 74 passed
- Metadata/sufficiency regression set -> 41 passed, 1 skipped
- `python -m compileall -q src tests/unit/test_artifact_registry_payload_hydration_boundary.py tests/unit/test_accepted_running_artifact_worker_terminalization_guard.py tests/unit/test_cvl_artifact_worker_terminalization_frontier.py` -> PASS

Prompt-listed tests absent in this checkout were represented by available equivalent suites where possible.

## Anti-Hardcode Audit

Production search found only existing structural `FireTestProfile` / `FireTestLaboratoryService` references in CVL. No production decision branch was added for FireTest, Pinhoabacaxi, local paths, exact artifact names, task ids, operation ids, or extensions as truth.

## Public Reruns

### Same-Wave Rerun Before Final Guard Hardening

Raw capture:

`reports/firetest5/firetest5_h1c0_r2_8_clean_phase0_to_6_20260816_093618`

Observed:

- `phase1_discovery.md` created.
- `project_inventory.md` created.
- legacy registry no longer blocked first artifact creation.
- `music_inventory.csv` was reached.
- remaining state: artifact worker stall at `music_inventory.csv`, then terminal blocked result.

This proved the original artifact registry exception frontier moved.

### Latest Clean Rerun After Backend Restart

Raw capture:

`C:\Dev\AIpinho\reports\firetest5\firetest5_h1c0_r2_8_clean_phase0_to_6_20260816_095958`

Observed:

- `client_response_status = accepted_running`
- `task_run_id = task_run_24636b2abe6f4b08bc6d7826b5cf136f`
- `result.status = blocked`
- `reason_code = PROJECT_ANALYSIS_DEGRADED`
- `finished_at = 2026-08-16T13:00:07.668971+00:00`
- `terminal_event_count = 1`
- `artifact_creation_started_count = 0`
- Phase 2-6: `skipped_due_to_prior_block`

The latest clean rerun blocked before artifact runtime because ProjectAnalysis selected zero files from the library root and returned `PROJECT_ANALYSIS_DEGRADED`. It produced a coherent terminal result and did not execute Phase 2.

## Endpoint / Storage Health

Latest rerun endpoint statuses were coherent:

- `/summary`: 200
- `/result`: 200
- `/truth`: 200
- `/events`: 200
- `/artifacts`: 200

Queue/storage after:

- active runs: `0`
- queued runs: `0`
- stale runs: `0`
- pending approvals: `0`
- large runs: `0`
- missing indexes: `0`

## Why No False Success

The wave did not treat artifact creation, result existence, registry write success, or service-equivalent metadata coverage as FireTest success. Speaker Truth remained unsafe to report success, Phase 1 stayed blocked, and Phase 2-6 were skipped.

## Why FireTest 5 Is Not READY

FireTest 5 is not ready because the latest clean public run did not reach artifact runtime. It blocked in ProjectAnalysis with `PROJECT_ANALYSIS_DEGRADED`, specifically zero selected/read files from the library root due file-selection rejection. Metadata/inventory sufficiency was not publicly re-proven after the backend restart.

## Remaining Gaps

- P0: ProjectAnalysis/library-root selection can block before artifact runtime when the selected root is a media corpus and the file selection policy rejects media files as unsupported for source reading.
- P1: Phase 0 predicted `TRUTH_READINESS` in the latest rerun instead of the observed `PROJECT_ANALYSIS_DEGRADED` frontier.
- P1: Legacy 2GB artifact registry remains preserved as evidence; new writes no longer depend on it, but long-term archival/compaction policy may move it out of the hot manifest directory.

## Next Recommendation

Run a narrow repair slice for ProjectAnalysis corpus-root handoff/file-selection semantics: ProjectAnalysis should not fail the public artifact flow solely because a governed media corpus root contains files that are not source-code-readable. It should either produce partial context sufficient for artifact runtime or block with a corpus-root-specific reason, without reopening metadata policy or renderer observation.
