---
rag_pack_id: context_admission_rejection
title: Context Admission and Rejection
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
  - decision_record
tags:
  - context
  - admission
  - scope
  - policy
---

# Context Admission and Rejection

## Canonical Summary

Context enters a prompt bundle only when purpose, scope, source trust, citation, budget and policy permit. Context rejection is a normal safe outcome, not a failure. This pack is written as curated operational knowledge, not as raw sprint notes or copied legacy code.

## Why This Matters

It reduces the risk of stale, irrelevant, sensitive or over-budget context influencing decisions. The value of this pack is to give AIpinho reusable decision guidance with explicit limits, examples and regression seeds.

## Rules

1. Context must have a declared purpose.
2. Source namespace and trust level are evaluated.
3. Citation or source reference is required for factual support.
4. Sensitive context requires policy allowance.
5. Legacy context cannot define current truth.
6. Budget limits may reject otherwise valid context.
7. Rejected context should be traceable in Debugger.

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

- Prompt: `Use legacy issue as anti-pattern.`
  Expected handling: Admit as historical_diagnostic with current_truth_allowed=false.
- Prompt: `Use current config policy.`
  Expected handling: Admit high-trust current source with citation.

## Bad Examples

- Prompt: `All retrieved chunks.`
  Expected handling: Dump everything into prompt.
- Prompt: `Old report mentions endpoint.`
  Expected handling: Treat endpoint as current API.

## Anti-patterns

- context_by_availability
- uncited_context
- legacy_as_truth
- over_budget_context_dump

## Regression Seeds

- irrelevant_context_rejected
- legacy_context_scoped
- context_budget_enforced
- rejection_trace_visible

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
