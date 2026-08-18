# H1B6.R1 - Phase 3 Public Pre-Acceptance Determinism + Harness Stop Condition

- verdict: `FIRETEST5_H1B6_R1_PHASE3_PRE_ACCEPTANCE_READY`
- objective: make governed phase prompts create a traceable runtime state before heavy work, and stop canonical phase progression after the first block.
- scope: public pre-acceptance ordering, phase dependency boundary, progression state model, CVL awareness, tests, and controlled progression observation.
- non-goals preserved: no H1C0 repair, no H1B5 truth-policy changes, no Phase 4-6 implementation, no target-app patch/build, no fake artifact, no timeout-global workaround.

## Initial Finding

Previous public progression observed Phase 3 as `timeout_blocked` before TaskRun creation:

- `task_run_id = None`
- `result_ref_id = None`
- `TaskRun created = false`
- `reason_code = PUBLIC_RUNTIME_BLOCKED_BEFORE_ACCEPTED_RUNNING`

The audit found the risky boundary: `ReadonlyAnalysisArtifactRuntimeService.execute()` validated phase dependencies before creating the TaskRun. For dependency-heavy phases, this could revalidate prior artifacts and semantic contracts before the public response had a persisted runtime state.

## Changes

- Added `PublicPreAcceptancePolicy` in `src/aipinho/services/governance/runtime/readonly_analysis_artifact_runtime_service.py`.
- Split phase dependency checks into:
  - light preflight before TaskRun: phase record/artifact-id presence only;
  - semantic validation inside TaskRun: artifact revalidation and semantic contract validation.
- Replaced the normal pre-TaskRun fallback reason with `PUBLIC_RUNTIME_CREATE_RUN_NOT_REACHED`.
- Added `FireTestPhaseProgressionState` and `PhaseProgressionGate`.
- Added `PhaseProgressionGateService` to stop progression after the first canonical block.
- Added CVL/Fase 0 awareness for:
  - `PUBLIC_RUNTIME_PREACCEPTANCE_HEAVY_WORK_DETECTED`
  - `PUBLIC_RUNTIME_CREATE_RUN_NOT_REACHED`
  - `PHASE_PROGRESSION_STOP_CONDITION_REQUIRED`
  - `PHASE_SKIPPED_DUE_TO_PRIOR_BLOCK`

## Behavior

- Phase 3 normal path now creates/accepts a TaskRun before heavy dependency semantic validation.
- If dependency semantic validation fails, it blocks inside the TaskRun with result/status/events.
- Pre-TaskRun timeout remains possible only as a specific diagnostic boundary, not the generic old fallback.
- Harness/progression stops at the first block; later phases become `skipped_due_to_prior_block`.
- `invalid_post_block_attempt` remains diagnostic only, not canonical progression.

## Public Observation

Public API health and queue health were checked on `http://127.0.0.1:9088`:

- health: `ok`
- active_runs: `0`
- queued_runs: `0`
- stale_runs: `0`
- pending_approvals: `0`

Because Wave A/H1C0 is currently `FIRETEST5_H1C0_PHASE1_PHASE2_SEMANTIC_CONTRACT_BLOCKED`, canonical progression does not allow a Phase 3 public call. The controlled progression observation therefore recorded:

- Phase 1: `blocked`
- Phase 2: `skipped_due_to_prior_block`
- Phase 3: `skipped_due_to_prior_block`
- invalid post-block attempts: `0`

This is intentional: the wave must not advance artificially past a prior semantic block.

## Verification

- `python -m pytest tests/unit/test_phase3_public_preacceptance_boundary.py tests/unit/test_firetest_phase_progression_harness.py tests/unit/test_phase_progression_state_model.py tests/unit/test_public_runtime_response_boundary.py tests/unit/test_public_runtime_result_finalization.py tests/unit/test_public_chat_phase_dependency_boundary.py tests/unit/test_project_analysis_single_file_read_budget_cooperation.py tests/unit/test_cognitive_validation_laboratory_service.py -q`
  - result: `36 passed`
- `python -m pytest tests/unit/test_relationship_stack_integration_audit.py -q`
  - result: `9 passed`
- `python -m py_compile ...`
  - result: `PASS`

## Gaps

- Phase 3 was not called publicly because H1C0 is still the canonical prior block.
- The next public evidence should come after H1C0 is repaired or intentionally rerun to a Phase 1/2 state that allows Phase 3.
- The public endpoint now has a more specific pre-TaskRun diagnostic, but a true public Phase 3 acceptance run still depends on valid prior phase progression.

## Why This Is Not a Bypass

- No phase was forced after a prior block.
- No fake artifact/result was created.
- No timeout was increased to hide work.
- Heavy artifact dependency validation still exists, but now runs under a real TaskRun.
- Validation, Completion, and Speaker Truth remain conservative.
- The patch does not hardcode FireTest, Pinhoabacaxi, local paths, Kotlin, artifact names, or extensions as decision logic.

## Recommendation

Return to the H1C0 semantic artifact contract blocker first. Once Phase 1/2 progression is semantically allowed, rerun a public Phase 1 -> Phase 2 -> Phase 3 diagnostic to collect a real Phase 3 `accepted_running` or in-run `blocked` result.
