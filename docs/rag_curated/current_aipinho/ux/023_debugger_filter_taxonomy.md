---
rag_pack_id: debugger_filter_taxonomy
title: Debugger Filter Taxonomy
namespace: current_aipinho_curated
source_of_truth: true
current_source_of_truth: true
legacy: false
trust_level: high
status: approved
version: 1
owner: debugger
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
  - doc_section
tags:
  - debugger
  - filters
  - telemetry
  - logs
---

# Debugger Filter Taxonomy

## Canonical Summary

Debugger filters organize technical evidence by planner, executor, reviewer, validator, interpreter, speaker, policy, tool, RAG, memory, approval, patch and route telemetry categories. This pack is written as curated operational knowledge, not as raw sprint notes or copied legacy code.

## Why This Matters

It reduces the risk of Debugger becoming a raw log dump rather than an audit surface. The value of this pack is to give AIpinho reusable decision guidance with explicit limits, examples and regression seeds.

## Rules

1. Every card has category and severity.
2. Raw is hidden by default and copied on demand.
3. Sanitized log is visible and copyable.
4. Filters are additive and do not delete evidence.
5. Policy and approval events are first-class categories.
6. Legacy and dangerous route telemetry are marked advanced.
7. Long details are scrollable, not silently truncated.

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

- Prompt: `Validation failure.`
  Expected handling: User filters validator/error and copies sanitized log.
- Prompt: `RAG decision.`
  Expected handling: Debugger shows source trust and context admission result.

## Bad Examples

- Prompt: `Raw JSON panel.`
  Expected handling: Default view dumps everything.
- Prompt: `Filter hides approval.`
  Expected handling: User cannot see pending decision.

## Anti-patterns

- raw_default_debugger
- uncategorized_logs
- truncated_without_copy
- approval_not_filterable

## Regression Seeds

- debugger_filters_categories
- raw_hidden_copyable
- long_log_scrollable
- policy_event_visible

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
