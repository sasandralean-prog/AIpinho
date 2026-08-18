---
rag_pack_id: policy_ownership_matrix
title: Policy Ownership Matrix
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
  - decision_record
tags:
  - policy
  - ownership
  - capability
  - approval
---

# Policy Ownership Matrix

## Canonical Summary

Every permission decision has a single owner. Policy Kernel owns permission, Capability Gate owns grants, Approval Policy owns user consent, and tools only execute a validated envelope. This pack is written as curated operational knowledge, not as raw sprint notes or copied legacy code.

## Why This Matters

It reduces the risk of split-brain authorization where UI, skill, role or tool makes an inconsistent decision. The value of this pack is to give AIpinho reusable decision guidance with explicit limits, examples and regression seeds.

## Rules

1. Policy Kernel is authoritative for permission decisions.
2. Capability Gate determines whether a requested action can be attempted.
3. Approval Policy determines when a human decision is required.
4. Workspace Guard determines path access and protected roots.
5. Tool services execute only a received contract.
6. Roles can request work but cannot grant themselves new actions.
7. UI can surface approval but cannot mark approval as satisfied without backend state.
8. Config-critical absence creates degraded or blocked status, never silent allow.

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

- Prompt: `Executor wants shell.`
  Expected handling: Executor receives shell only if contract grants shell and approval policy is satisfied.
- Prompt: `UI shows Apply.`
  Expected handling: Button is enabled only when backend reports preview, quality gate and approval ready.

## Bad Examples

- Prompt: `Reviewer sees low risk.`
  Expected handling: Reviewer directly enabling patch apply.
- Prompt: `Tool receives path.`
  Expected handling: Tool writes because the path string looks local, without Workspace Guard result.

## Anti-patterns

- permission_by_label
- ui_authorization
- tool_self_authorization
- role_policy_bypass
- silent_policy_fallback

## Regression Seeds

- role_cannot_grant_shell
- missing_policy_blocks_write
- ui_button_not_authority
- tool_requires_envelope

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
