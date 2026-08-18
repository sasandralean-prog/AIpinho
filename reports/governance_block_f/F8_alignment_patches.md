# F8 Alignment Patches

Checkpoint: F8_ALIGNMENT_PATCHES_READY
Generated: 2026-06-28T15:44:57.208267+00:00

Patches applied:
1. Added LiveAlignmentConflictDetector.
2. ProjectGenerationPlanExecutor blocks omitted placeholders explicitly.
3. ProjectGenerationPlanExecutor prefers the approved TaskDraft plan when draft_id exists.
4. TaskRuntimeService injects the matching TaskDraftStore into GovernedTaskStepRunner/ProjectGenerationPlanExecutor.
5. Added focused tests for sanitization boundary and live alignment detector.

Risk:
- The TaskRuntimeService injection changes construction only; existing default behavior still uses default TaskDraftStore.
