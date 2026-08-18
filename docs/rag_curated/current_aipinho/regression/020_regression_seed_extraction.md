---
rag_pack_id: regression_seed_extraction
title: Regression Seed Extraction
namespace: current_aipinho_curated
source_of_truth: true
current_source_of_truth: true
legacy: false
trust_level: high
status: approved
version: 1
owner: regression_harness
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
  - regression_seed
  - decision_record
tags:
  - regression
  - testing
  - feedback
  - evidence
---

# Regression Seed Extraction

## Canonical Summary

Failures, disliked responses, blocked actions and historical bugs can become regression seed candidates. A seed is not a test until it has expected behavior, evidence and scope. This pack is written as curated operational knowledge, not as raw sprint notes or copied legacy code.

## Why This Matters

It reduces the risk of turning anecdotes into brittle tests or ignoring recurring failures. The value of this pack is to give AIpinho reusable decision guidance with explicit limits, examples and regression seeds.

## Rules

1. Extract seed only with source and evidence.
2. Separate candidate from active regression test.
3. Expected behavior must be explicit.
4. Scope must name surface or subsystem.
5. Avoid exact prompt-only fixtures.
6. Use class of failure, not a one-off case.
7. Promotion requires review and validation.

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

- Prompt: `User says simple prompt became task.`
  Expected handling: Create candidate class simple_chat_not_task.
- Prompt: `Legacy bug repeated.`
  Expected handling: Create seed with historical evidence and current expected behavior.

## Bad Examples

- Prompt: `One phrase failed.`
  Expected handling: Hardcode exact phrase into router.
- Prompt: `Feedback negative.`
  Expected handling: Automatically alter model memory.

## Anti-patterns

- exact_prompt_test_only
- feedback_as_training
- seed_without_expected
- seed_without_scope

## Regression Seeds

- simple_chat_not_task
- readonly_no_patch
- legacy_endpoint_not_current
- feedback_creates_candidate_only

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
