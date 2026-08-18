---
rag_pack_id: patch_vs_readonly_invariant
title: Patch vs Read-Only Invariant
namespace: current_aipinho_curated
source_of_truth: true
current_source_of_truth: true
legacy: false
trust_level: high
status: approved
version: 1
owner: policy_kernel
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
requires_current_validation: false
sensitive: false
chunk_types:
  - config_policy
  - regression_seed
  - decision_record
tags:
  - patch
  - readonly
  - approval
  - quality_gate
---

# Patch vs Read-Only Invariant

## Canonical Summary

Patch, artifact write, apply and workspace mutation cannot coexist with read_only, write_forbidden or denied capability. Negative user constraints override action words such as fix, patch or correct. This pack is written as curated operational knowledge, not as raw sprint notes or copied legacy code.

## Why This Matters

It reduces the risk of accidental file mutation when the user requested explanation, review or diagnosis only. The value of this pack is to give AIpinho reusable decision guidance with explicit limits, examples and regression seeds.

## Rules

1. If read_only=true, patch_apply=false.
2. If write_forbidden=true, artifact_write and patch_apply are blocked.
3. User denial of mutation has precedence over inferred intent.
4. Patch preview is not patch apply.
5. Patch apply requires preview, quality gate, approval, capability and snapshot match.
6. No-op patches cannot become approval requests.
7. Validation after apply is required before success.
8. A task can recommend a patch later without producing one immediately.

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

- Prompt: `Do not apply patch, only explain the error.`
  Expected handling: Return explanation and optional next safe action; do not create apply path.
- Prompt: `Create a patch preview but wait.`
  Expected handling: Create preview, quality gate and approval request; do not write files.

## Bad Examples

- Prompt: `Only review this.`
  Expected handling: Generating a diff because review found an obvious fix.
- Prompt: `Patch later maybe.`
  Expected handling: Creating apply-ready approval without explicit patch request.

## Anti-patterns

- negated_patch_trigger
- readonly_patch_plan
- preview_equals_apply
- success_without_post_validation

## Regression Seeds

- negated_patch_not_patch_request
- patch_read_only_blocked
- write_forbidden_blocks_apply
- patch_requires_quality_gate
- no_op_patch_no_approval

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
