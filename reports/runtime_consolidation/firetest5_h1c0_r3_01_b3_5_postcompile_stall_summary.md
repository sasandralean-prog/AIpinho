# FireTest 5 H1C0 R3.01 B3.5 Post-Compile Stall Forensics

## Baseline

- Mission class: hybrid_operational_correction
- Branch: `agent/codex/r3-01-b3-5-postcompile-stall-route-boundary`
- Base SHA: `50af6491b78e662bbd3390a59400aec6f0eb0bb1`
- Main merge: not performed
- FireTest 5: not executed
- ffprobe/dependency/budget changes: none

## Code Changes

Changed files before report generation:

- `docs/external/public_runtime_api.md`
- `src/aipinho/api/routers/public_runtime_api_router.py`
- `src/aipinho/services/artifacts/governed_observation_execution_stage_service.py`
- `src/aipinho/services/governance/runtime/readonly_analysis_artifact_runtime_service.py`
- `src/aipinho/services/runtime/task_run_store.py`
- `tests/unit/test_public_runtime_api_ex3.py`

The governed execution stage now emits bounded micro-checkpoints through group planning, applicability resolution, backend snapshot, and physical probe dispatch. Total observation budget is checked inside group planning/applicability iteration, so the public bridge can terminalize with a stage-specific reason instead of a generic post-compile execution stall.

The public runtime chat route was relocated to `/api/v1/runtime/chat`. `/api/v1/chat` remains the canonical ChatRequest route.

## Stall Diagnosis

B3.4 stopped at `before_post_compile_observation_execution` and terminalized as `POST_COMPILE_OBSERVATION_EXECUTION_STALLED` without group/probe proof.

The B3.5 canary reached the post-compile dark zone and blocked with:

- reason: `POST_COMPILE_CAPABILITY_APPLICABILITY_RESOLUTION_STALLED`
- task_run_id: `task_run_10a7ad7dabca4687bcebbe5cba30ce25`
- operation_id: `op_42cafcfaa0654bf299011345171199dc`
- terminal blocking event count: `1`
- SpeakerTruth safe_to_report_success: `False`

Observed group-planning telemetry:

- task_count: `None`
- tasks_seen: `None`
- deferred_task_count: `None`
- execute_observer_task_count: `None`
- target_entity_ref_count: `None`
- applicability_started_count: `None`
- applicability_completed_count: `None`
- applicability_failed_count: `None`
- groups_created_count: `None`
- elapsed_ms: `None`

No physical probe was claimed: physical_probe_count remained `None`.

## Route Boundary

- `/api/v1/chat` with PublicRuntimeRequest: 422 ChatRequest validation, proving canonical ownership.
- `/api/v1/runtime/chat` with PublicRuntimeRequest: 200 accepted, operation `chat`.
- Duplicate route ambiguity is covered by tests.

## Issue Register

- Current P0: none observed.
- Corrected P1: `R3_01_B3_4_P1_PUBLIC_CANARY_POST_COMPILE_OBSERVATION_STALL_BEFORE_FIRETEST` now reports a specific applicability-resolution frontier.
- New remaining P1: `R3_01_B3_5_P1_CAPABILITY_APPLICABILITY_RESOLUTION_CAPACITY_FRONTIER`.
- Route issue: resolved/isolated with explicit route boundary tests.

## Tests Run

- `python -m pytest tests/unit/test_post_compile_observation_group_planning_checkpoints.py tests/unit/test_post_compile_observation_stall_reason_refinement.py tests/unit/test_post_compile_applicability_resolution_boundedness.py tests/unit/test_public_runtime_chat_route_boundary.py -q` -> 8 passed
- `python -m pytest tests/unit/test_governed_post_compile_observation_execution_stage.py -q` -> 50 passed
- `python -m pytest tests/unit/test_public_runtime_api_ex3.py tests/unit/test_public_runtime_chat_route_boundary.py -q` -> 12 passed
- `python -m pytest tests/unit/test_contract_driven_perception_service.py tests/unit/test_media_metadata_capability_pack.py tests/unit/test_media_metadata_capability_policy.py -q` -> 53 passed, 1 skipped
- `python -m pytest tests/unit/test_media_corpus_entity_selection.py tests/unit/test_file_selection_role_semantics.py tests/unit/test_music_inventory_observational_binding_public.py tests/unit/test_music_inventory_metadata_coverage.py -q` -> 9 passed
- `python -m pytest tests/unit/test_music_inventory_artifact_worker_stall_terminality.py tests/unit/test_universal_task_session_service.py -q` -> 21 passed
- `python -m pytest tests/unit/test_observation_execution_boundary_service.py tests/unit/test_bounded_runtime_metrics_projection.py -q` -> 8 passed
- `python -m pytest tests/unit/test_public_runtime_response_boundary.py -q` -> 3 passed after isolated retry of a timing-sensitive grouped run
- `python -m compileall -q src tests` -> pass
- `git diff --check` -> pass

Final static checks and full-unit attempt are recorded in the final response after report generation.

## B3.3 Effect Status

PARTIALLY_PROVEN. The corrected runtime is publicly exercisable past the previous generic post-compile checkpoint and now exposes applicability telemetry. It did not reach physical probes because applicability resolution itself consumed the total observation envelope.

## C Gate

CORRECTIVE_REQUIRED_BEFORE_C. The next blocker is applicability-resolution capacity before physical execution, not ffprobe coverage.

## Why No False Success

The canary blocked with one governed terminal blocked outcome, no physical/evidence claims were invented, and SpeakerTruth remained false on block.


## Final Validation Update

Complete changed-file set at report close:

- `docs/external/public_runtime_api.md`
- `src/aipinho/api/routers/public_runtime_api_router.py`
- `src/aipinho/services/artifacts/governed_observation_execution_stage_service.py`
- `src/aipinho/services/governance/runtime/readonly_analysis_artifact_runtime_service.py`
- `src/aipinho/services/runtime/task_run_store.py`
- `tests/unit/test_public_runtime_api_ex3.py`
- `reports/runtime_consolidation/firetest5_h1c0_r3_01_b3_5_issue_register.json`
- `reports/runtime_consolidation/firetest5_h1c0_r3_01_b3_5_postcompile_stall_diagnostic.json`
- `reports/runtime_consolidation/firetest5_h1c0_r3_01_b3_5_postcompile_stall_summary.md`
- `reports/runtime_consolidation/firetest5_h1c0_r3_01_b3_5_public_canary_observation.json`
- `reports/runtime_consolidation/firetest5_h1c0_r3_01_b3_5_route_boundary_observation.json`
- `tests/unit/test_post_compile_applicability_resolution_boundedness.py`
- `tests/unit/test_post_compile_observation_group_planning_checkpoints.py`
- `tests/unit/test_post_compile_observation_stall_reason_refinement.py`
- `tests/unit/test_public_runtime_chat_route_boundary.py`

Static validation:

- `python -m compileall -q src tests` -> PASS
- `git diff --check` -> PASS
- anti-hardcode scan -> PASS with existing fixture/path-report matches only; no new corpus-count, extension-truth, or ffprobe-install hardcode found in B3.5 code/tests.

Full unit attempt:

- `python -m pytest tests/unit -q -x` -> FAIL_EXTERNAL_SCOPE_FIRST_FAILURE
- first failure: `tests/unit/test_agent_delegation_service.py::test_delegation_request_result_parent_child_and_timeline`
- reason: `PermissionError: agent_profile_disabled` while creating the `lucio` agent session
- counts before stop: 1 failed, 16 passed
- attribution: not attributed to B3.5 post-compile or route-boundary changes.
