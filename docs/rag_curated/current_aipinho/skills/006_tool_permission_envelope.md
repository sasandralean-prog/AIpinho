---
rag_pack_id: tool_permission_envelope
title: Tool Permission Envelope
namespace: current_aipinho_curated
source_of_truth: true
current_source_of_truth: true
legacy: false
trust_level: high
status: approved
version: 1
owner: tool_registry
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
  - skill_contract
  - config_policy
tags:
  - tools
  - capability
  - workspace_guard
  - approval
---

# Tool Permission Envelope

## Canonical Summary

Tools only execute inside a permission envelope built by policy, capability, workspace guard and approval checks. A tool never decides whether it is allowed. This pack is written as curated operational knowledge, not as raw sprint notes or copied legacy code.

## Why This Matters

It reduces the risk of direct shell, filesystem, git, browser or connector execution outside contract. The value of this pack is to give AIpinho reusable decision guidance with explicit limits, examples and regression seeds.

## Rules

1. Tool input must include action, capability, workspace scope, risk and audit id.
2. Filesystem writes require safe path and approval where policy requires it.
3. Shell execution requires explicit shell capability.
4. Git writes require explicit git capability and approval.
5. Network or connector access follows connector policy.
6. Dry-run and preview do not imply execute.
7. Tool result is evidence, not final answer.

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

- Prompt: `Read a file for diagnosis.`
  Expected handling: Filesystem read tool receives read_workspace capability and path guard success.
- Prompt: `Preview a shell command.`
  Expected handling: Tool preview returns risk and expected effect without running it.

## Bad Examples

- Prompt: `Skill wants to help.`
  Expected handling: Skill calls shell because the prompt mentioned tests.
- Prompt: `Path looks safe.`
  Expected handling: Tool writes without path guard decision.

## Anti-patterns

- tool_executes_on_prompt
- dry_run_as_execute
- missing_audit_id
- skill_bypasses_policy

## Regression Seeds

- tool_requires_valid_envelope
- shell_requires_capability
- git_write_requires_approval
- path_guard_blocks_escape

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
