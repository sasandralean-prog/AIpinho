---
rag_pack_id: feedback_to_regression_candidate
title: Feedback to Regression Candidate
namespace: current_aipinho_curated
source_of_truth: true
current_source_of_truth: true
legacy: false
trust_level: high
status: approved
version: 1
owner: feedback_service
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
  - memory_summary
  - config_policy
tags:
  - feedback
  - regression
  - memory
  - quality
---

# Feedback to Regression Candidate

## Canonical Summary

Human feedback, dislikes and correction notes become regression or memory candidates, not automatic training, not automatic curated memory and not silent behavior changes. This pack is written as curated operational knowledge, not as raw sprint notes or copied legacy code.

## Why This Matters

It reduces the risk of feedback loops that overfit one user comment, alter memory without approval or create hidden deterministic rules. The value of this pack is to give AIpinho reusable decision guidance with explicit limits, examples and regression seeds.

## Rules

1. Feedback creates candidate records.
2. Candidate includes source, evidence, expected improvement and scope.
3. Negative feedback does not directly change model or memory.
4. Regression candidate promotion requires review.
5. Memory candidate promotion requires memory approval.
6. UI should show that feedback was captured as candidate.
7. Exact phrase hardcoding from feedback is blocked.

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

- Prompt: `User says answer was truncated.`
  Expected handling: Create anti-truncation regression candidate with evidence.
- Prompt: `User says mobile state stale.`
  Expected handling: Create UX sync candidate and link to surface/state evidence.

## Bad Examples

- Prompt: `User dislikes response.`
  Expected handling: Automatically save a permanent memory saying never answer that way.
- Prompt: `One prompt failed.`
  Expected handling: Hardcode exact prompt handling.

## Anti-patterns

- feedback_auto_training
- feedback_auto_memory
- single_prompt_hardcode
- candidate_without_evidence

## Regression Seeds

- feedback_creates_candidate_only
- dislike_not_training
- candidate_requires_scope
- feedback_not_hardcode

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
