---
rag_pack_id: realtime_reconnect_and_sync_cursor
title: Realtime Reconnect and Sync Cursor
namespace: current_aipinho_curated
source_of_truth: true
current_source_of_truth: true
legacy: false
trust_level: high
status: approved
version: 1
owner: realtime_sync
created_from:
  - sprint_00_to_40_curated
allowed_purposes:
  - policy_audit
  - maintenance_diagnosis
  - context_admission
  - skill_execution
  - regression_case_generation
  - validation
  - debugger_analysis
blocked_purposes:
  - bypass_approval
  - direct_tool_execution
  - direct_patch_without_validation
  - shell_execution
  - git_write
  - memory_auto_write
requires_current_validation: true
sensitive: false
chunk_types:
  - config_policy
  - event_summary
tags:
  - realtime
  - sync
  - sse
  - cursor
  - dedupe
---

# Realtime Reconnect and Sync Cursor

## Canonical Summary

Realtime UX needs reconnect logic, monotonic cursor, dedupe and polling fallback. A reconnect should not duplicate events, resurrect terminal tasks or hide stale state. This pack is written as curated operational knowledge, not as raw sprint notes or copied legacy code.

## Why This Matters

It reduces the risk of event storms, duplicate chat messages, stale task state and inconsistent mobile/desktop views. The value of this pack is to give AIpinho reusable decision guidance with explicit limits, examples and regression seeds.

## Rules

1. Every streamed event has cursor or revision.
2. Reconnect resumes from last cursor when possible.
3. Polling fallback uses same canonical state.
4. Deduplication uses event id, task id and revision.
5. Terminal tombstones prevent task resurrection.
6. Stale indicator appears when sync lags.
7. Manual refresh reconciles state.

## Allowed Use

- Use for `policy_audit` when the pack purpose and scope match the active contract.
- Use for `maintenance_diagnosis` when the pack purpose and scope match the active contract.
- Use for `context_admission` when the pack purpose and scope match the active contract.
- Use for `skill_execution` when the pack purpose and scope match the active contract.
- Use for `regression_case_generation` when the pack purpose and scope match the active contract.
- Use for `validation` when the pack purpose and scope match the active contract.
- Use for `debugger_analysis` when the pack purpose and scope match the active contract.

## Blocked Use

- Do not use for `bypass_approval`.
- Do not use for `direct_tool_execution`.
- Do not use for `direct_patch_without_validation`.
- Do not use for `shell_execution`.
- Do not use for `git_write`.
- Do not use for `memory_auto_write`.

## Good Examples

- Prompt: `SSE drops.`
  Expected handling: UI reconnects and fetches missing state with stale indicator.
- Prompt: `Duplicate event arrives.`
  Expected handling: Deduped without duplicate Speaker bubble.

## Bad Examples

- Prompt: `Reconnect.`
  Expected handling: Start task again.
- Prompt: `Polling delay.`
  Expected handling: Show old task as active forever.

## Anti-patterns

- duplicate_event_render
- reconnect_runs_task
- cursor_ignored
- terminal_task_resurrected

## Regression Seeds

- sse_reconnect_no_duplicate
- polling_fallback_same_state
- cursor_monotonic
- tombstone_blocks_resurrection

## Context Admission Notes

Admit this pack when the requested purpose matches its tags and allowed purposes. It can support policy, UX, validation and debugging decisions but never bypasses live gates. Context admission must keep namespace, source trust, citation and current validation flags visible to Debugger.

## Validation Checklist

- The active purpose is allowed by frontmatter.
- The pack is cited by file and `rag_pack_id`.
- Blocked purposes were checked before use.
- Permission, capability, approval and validation gates remain authoritative.
- Any legacy or implementation-dependent claim is checked against current AIpinho state.
- Regression seeds are converted to reviewed tests before enforcement.

## Current Validation Notes

This pack represents current curated guidance. Operational use still follows live policy, endpoint state and validation where applicable. The pack must not create deterministic routing by exact phrase, project name, path, sprint number or user identity.
