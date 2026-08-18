---
rag_pack_id: manual_only_14b_model_routing
title: 14B Manual-Only Model Routing
namespace: current_aipinho_curated
source_of_truth: true
current_source_of_truth: true
legacy: false
trust_level: high
status: approved
version: 1
owner: model_registry
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
  - decision_record
tags:
  - models
  - routing
  - manual_review
  - cpu
---

# 14B Manual-Only Model Routing

## Canonical Summary

Large 14B local models are reserved for explicit manual or deep review profiles when hardware and policy allow. Routine chat and operational routing should prefer configured effective policy, not hardcoded model size. This pack is written as curated operational knowledge, not as raw sprint notes or copied legacy code.

## Why This Matters

It reduces the risk of slow CPU-only execution, queue lock, memory pressure and accidental model escalation. The value of this pack is to give AIpinho reusable decision guidance with explicit limits, examples and regression seeds.

## Rules

1. Model size is not a permission grant.
2. 14B routing requires explicit model policy profile.
3. Manual deep review must expose expected latency and resource risk.
4. Fallback to smaller model is allowed when policy prefers responsiveness.
5. No prompt phrase should hard-route to 14B.
6. Capability and role requirements remain separate from model selection.
7. Unavailable models create degraded status, not false success.

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

- Prompt: `User asks deep architecture review.`
  Expected handling: UI offers manual deep-review mode with latency warning.
- Prompt: `Small chat question.`
  Expected handling: Use normal chat routing and do not escalate.

## Bad Examples

- Prompt: `Prompt says complex.`
  Expected handling: Hardcoding 14B execution.
- Prompt: `14B unavailable.`
  Expected handling: Pretending response came from 14B.

## Anti-patterns

- model_size_as_quality_gate
- prompt_word_model_hardroute
- silent_model_fallback
- cpu_queue_starvation

## Regression Seeds

- simple_prompt_no_14b
- manual_deep_review_requires_choice
- unavailable_model_degraded
- role_model_gate_explains_selection

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
