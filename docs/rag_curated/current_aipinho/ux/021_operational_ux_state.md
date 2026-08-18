---
rag_pack_id: operational_ux_state
title: Operational UX State
namespace: current_aipinho_curated
source_of_truth: true
current_source_of_truth: true
legacy: false
trust_level: high
status: approved
version: 1
owner: ux_runtime
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
  - doc_section
tags:
  - ux
  - state
  - mobile
  - launcher
  - workbench
---

# Operational UX State

## Canonical Summary

UX surfaces must distinguish healthy, degraded, offline, blocked, recovering and unknown states. The user should see what is actionable, what is waiting and what is historical. This pack is written as curated operational knowledge, not as raw sprint notes or copied legacy code.

## Why This Matters

It reduces the risk of stale tasks, false offline status, hidden approvals and confusing pipeline state. The value of this pack is to give AIpinho reusable decision guidance with explicit limits, examples and regression seeds.

## Rules

1. Active state comes from canonical endpoint state.
2. Terminal tasks must not appear active.
3. Unknown state is not healthy.
4. Blocked approval must be visible as pending action.
5. Historical errors are separated from active errors.
6. Recovering state indicates reconnect/retry.
7. Manual refresh should be available.

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

- Prompt: `Backend offline.`
  Expected handling: Show offline with connection test and last known state marked stale.
- Prompt: `Approval pending.`
  Expected handling: Show approval card, not generic error.

## Bad Examples

- Prompt: `Old task failed.`
  Expected handling: Show it as current active error.
- Prompt: `No connection.`
  Expected handling: Pretend task is complete.

## Anti-patterns

- stale_task_active
- unknown_as_healthy
- approval_hidden
- historical_error_active

## Regression Seeds

- terminal_task_not_active
- offline_state_clear
- approval_pending_visible
- manual_refresh_updates_state

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
