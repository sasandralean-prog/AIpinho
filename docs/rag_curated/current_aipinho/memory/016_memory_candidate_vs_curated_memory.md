---
rag_pack_id: memory_candidate_vs_curated_memory
title: Memory Candidate vs Curated Memory
namespace: current_aipinho_curated
source_of_truth: true
current_source_of_truth: true
legacy: false
trust_level: high
status: approved
version: 1
owner: memory_curator
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
  - memory_summary
  - config_policy
  - regression_seed
tags:
  - memory
  - curation
  - approval
  - evidence
---

# Memory Candidate vs Curated Memory

## Canonical Summary

A memory candidate is only a proposal. Curated memory requires source, evidence, scope, dedupe, conflict handling and explicit approval before it can influence future context. This pack is written as curated operational knowledge, not as raw sprint notes or copied legacy code.

## Why This Matters

It reduces the risk of semantic memory becoming noisy, stale, sensitive or self-reinforcing without review. The value of this pack is to give AIpinho reusable decision guidance with explicit limits, examples and regression seeds.

## Rules

1. Nothing enters definitive memory automatically.
2. Every extracted memory starts as candidate.
3. Candidate requires source reference and evidence.
4. Scope defines where it may be used.
5. Dedupe prevents duplicate memories.
6. Conflicts require resolution.
7. Approval promotes candidate to curated memory.
8. Approved memory still needs context admission policy before prompt use.

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

- Prompt: `User says a durable preference.`
  Expected handling: Create candidate with scope and ask for approval.
- Prompt: `Sprint lesson detected.`
  Expected handling: Propose memory candidate with evidence and tags.

## Bad Examples

- Prompt: `Tool log contains path.`
  Expected handling: Save it as memory automatically.
- Prompt: `User dislikes answer.`
  Expected handling: Train or alter memory without review.

## Anti-patterns

- auto_memory_write
- candidate_as_memory
- memory_without_scope
- memory_without_evidence
- approved_memory_auto_prompt

## Regression Seeds

- candidate_not_curated
- memory_requires_approval
- approved_memory_needs_context_policy
- feedback_not_training

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
