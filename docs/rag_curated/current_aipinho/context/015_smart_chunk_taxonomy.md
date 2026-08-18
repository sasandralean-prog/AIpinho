---
rag_pack_id: smart_chunk_taxonomy
title: Smart Chunk Taxonomy
namespace: current_aipinho_curated
source_of_truth: true
current_source_of_truth: true
legacy: false
trust_level: high
status: approved
version: 1
owner: rag_service
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
  - doc_section
tags:
  - chunks
  - taxonomy
  - rag
  - context
---

# Smart Chunk Taxonomy

## Canonical Summary

Chunks must declare their type so the Context Kernel can use them correctly. A config_policy chunk is not the same as an anti_pattern, event_summary, memory_summary or regression_seed. This pack is written as curated operational knowledge, not as raw sprint notes or copied legacy code.

## Why This Matters

It reduces the risk of all retrieved text being treated as equally actionable. The value of this pack is to give AIpinho reusable decision guidance with explicit limits, examples and regression seeds.

## Rules

1. config_policy can inform policy audit when current and cited.
2. architecture_note informs design but needs validation for implementation.
3. decision_record explains why a rule exists.
4. anti_pattern blocks unsafe behavior.
5. regression_seed proposes tests, not truth.
6. memory_summary is curated user/project knowledge only after approval.
7. doc_section supports explanation with citation.
8. event_summary supports current task state if recent and correlated.

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

- Prompt: `anti_pattern chunk.`
  Expected handling: Use to block repeating a failure.
- Prompt: `regression_seed chunk.`
  Expected handling: Generate a test case candidate.

## Bad Examples

- Prompt: `regression_seed.`
  Expected handling: Treat as current policy.
- Prompt: `architecture_note.`
  Expected handling: Apply code change without validation.

## Anti-patterns

- chunk_type_ignored
- seed_as_policy
- note_as_contract
- memory_summary_without_approval

## Regression Seeds

- chunk_type_controls_admission
- anti_pattern_blocks_behavior
- regression_seed_not_policy
- event_summary_requires_correlation

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
