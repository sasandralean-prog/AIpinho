---
rag_pack_id: pipeline_permission_visibility
title: Pipeline Permission Visibility
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
  - pipeline
  - permissions
  - approval
  - ux
---

# Pipeline Permission Visibility

## Canonical Summary

Pipeline UX must show permission requests, capability decisions, approvals, blocked actions and next safe action. Users should understand why a step can or cannot proceed. This pack is written as curated operational knowledge, not as raw sprint notes or copied legacy code.

## Why This Matters

It reduces the risk of hidden gates that look like failures or unsafe buttons that look available. The value of this pack is to give AIpinho reusable decision guidance with explicit limits, examples and regression seeds.

## Rules

1. Permission request is a visible pipeline event.
2. Denied capability shows reason.
3. Approval pending shows action owner and risk.
4. Blocked action shows next safe step.
5. Apply buttons are disabled until backend reports readiness.
6. Read-only mode is visibly distinct.
7. Validation status is not inferred from execution alone.

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

- Prompt: `Patch blocked by quality gate.`
  Expected handling: Show quality gate card and do not show apply as ready.
- Prompt: `Read-only task.`
  Expected handling: Show no write capability and report expected output.

## Bad Examples

- Prompt: `Capability denied.`
  Expected handling: Button still enabled and fails silently.
- Prompt: `Approval pending.`
  Expected handling: Only visible in raw log.

## Anti-patterns

- button_without_backend_state
- hidden_permission_request
- apply_enabled_without_gate
- silent_denial

## Regression Seeds

- pipeline_shows_capability_denied
- approval_visible
- apply_button_requires_ready
- readonly_pipeline_no_write

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
