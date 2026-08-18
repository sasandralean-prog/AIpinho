# Runtime Vertical Slice Root Cause

Date: 2026-07-05

## Root Cause

Read-only analysis was treated as non-executing by default. That was correct for pure chat planning, but incorrect for read-only tasks that explicitly request governed artifacts.

The main failure chain was:

1. `workspace_analysis_readonly` returned `requires_task=False`.
2. The public chat service produced a final answer directly.
3. Expected artifact outputs were never promoted into lifecycle completion.
4. Speaker Truth could not distinguish "read-only no side effects" from "read-only execution with artifact side effects in governed storage".

## Secondary Causes

- The TaskRun event policy did not permit analysis/artifact/validation events used by the new vertical slice.
- The finalizer did not map logical artifact outputs like `artifact:reports/foo.md` into completion evidence.
- Phase references selected the last mentioned phase as current, which inverted prompts such as "Fase 2 usando Fase 1".

## Non-Causes

- Source workspace write policy was not the blocker.
- Artifact generation does not require source workspace mutation.
- No provider-specific Gemini/Codex path was needed.

## Checkpoint

ROOT_CAUSE_CONFIRMED
