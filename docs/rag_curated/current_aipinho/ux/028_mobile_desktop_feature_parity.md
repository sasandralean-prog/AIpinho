---
rag_pack_id: mobile_desktop_feature_parity
title: Mobile/Desktop Feature Parity
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
  - doc_section
  - regression_seed
tags:
  - mobile
  - launcher
  - workbench
  - parity
---

# Mobile/Desktop Feature Parity

## Canonical Summary

Mobile, Launcher and Workbench should expose equivalent operational meaning even when layout differs. The same task, approval, debugger and speaker state should reconcile across surfaces. This pack is written as curated operational knowledge, not as raw sprint notes or copied legacy code.

## Why This Matters

It reduces the risk of one surface showing stale or incomplete state, causing unsafe user decisions. The value of this pack is to give AIpinho reusable decision guidance with explicit limits, examples and regression seeds.

## Rules

1. All surfaces use canonical task/session state.
2. Feature differences are explicit, not accidental.
3. Mobile may use compact layout but not hide critical approval.
4. Launcher may show cockpit detail without raw in chat.
5. Workbench may show advanced diagnostics with same backend truth.
6. Refresh/reconnect should converge state.
7. Cross-surface QA compares task_id, status, phase, approval and final answer.

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

- Prompt: `Approval pending.`
  Expected handling: Visible on mobile and desktop with same action.
- Prompt: `Debugger logs.`
  Expected handling: Mobile compact cards and Launcher detailed cards show same sanitized source.

## Bad Examples

- Prompt: `Mobile lacks cancel.`
  Expected handling: Task can only be supervised on desktop.
- Prompt: `Workbench says done.`
  Expected handling: Mobile still shows active task.

## Anti-patterns

- surface_state_divergence
- mobile_missing_approval
- desktop_raw_chat
- workbench_parallel_flow

## Regression Seeds

- cross_surface_same_task
- mobile_approval_visible
- launcher_final_matches_mobile
- workbench_not_parallel_runtime

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
