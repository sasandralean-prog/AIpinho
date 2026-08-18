---
rag_pack_id: context_purpose_mapping
title: Context Purpose Mapping
namespace: current_aipinho_curated
source_of_truth: true
current_source_of_truth: true
legacy: false
trust_level: high
status: approved
version: 1
owner: context_kernel
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
  - architecture_note
tags:
  - context
  - purpose
  - admission
  - routing
---

# Context Purpose Mapping

## Canonical Summary

Context must be admitted for a named purpose such as user_response, diagnosis, patch_planning, validation, debugger_analysis or regression_case_generation. The same source may be allowed for one purpose and blocked for another. This pack is written as curated operational knowledge, not as raw sprint notes or copied legacy code.

## Why This Matters

It reduces the risk of using diagnostic context as executable plan or UX note as backend contract. The value of this pack is to give AIpinho reusable decision guidance with explicit limits, examples and regression seeds.

## Rules

1. Purpose is selected before context admission.
2. User response prefers concise grounded context.
3. Diagnosis may use legacy lessons with warnings.
4. Patch planning requires current source and workspace evidence.
5. Validation requires executable test/profile evidence.
6. Regression generation may use failure patterns and anti-patterns.
7. Purpose mismatch rejects context.

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

- Prompt: `Legacy failure report.`
  Expected handling: Allowed for failure_analysis and regression seed.
- Prompt: `Current route config.`
  Expected handling: Allowed for current_api_contract.

## Bad Examples

- Prompt: `UX design pack.`
  Expected handling: Use it to grant shell capability.
- Prompt: `Historical report.`
  Expected handling: Use it to define current route.

## Anti-patterns

- purpose_free_context
- diagnosis_as_execution
- ux_as_policy
- legacy_as_current_contract

## Regression Seeds

- purpose_mismatch_rejected
- diagnosis_context_not_patch
- validation_requires_current_evidence
- regression_context_scoped

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
