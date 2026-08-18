---
rag_pack_id: event_contract_registry
title: Event Contract Registry
namespace: current_aipinho_curated
source_of_truth: true
current_source_of_truth: true
legacy: false
trust_level: high
status: approved
version: 1
owner: event_contract_registry
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
  - event_summary
  - architecture_note
tags:
  - events
  - contracts
  - telemetry
  - debugger
---

# Event Contract Registry

## Canonical Summary

Task, policy, tool, speaker, debugger, RAG and memory events must follow registered contracts. Unregistered events are diagnostic noise until normalized or rejected. This pack is written as curated operational knowledge, not as raw sprint notes or copied legacy code.

## Why This Matters

It reduces the risk of inconsistent UI state, unreadable debugger logs and impossible regression reconstruction. The value of this pack is to give AIpinho reusable decision guidance with explicit limits, examples and regression seeds.

## Rules

1. Every operational event has type, timestamp, source, task correlation and payload contract.
2. Event payloads are validated before UI display.
3. Raw payloads are hidden behind sanitized references.
4. Unknown events are marked degraded, not treated as success.
5. State reconciliation uses event revision and terminal tombstones.
6. Debugger cards map to event categories, not arbitrary strings.
7. Regression seeds must keep evidence event ids when available.

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

- Prompt: `approval_requested event.`
  Expected handling: UI shows approval card with task id, risk and action.
- Prompt: `validation_failed event.`
  Expected handling: Debugger displays validator card and Speaker explains failure.

## Bad Examples

- Prompt: `Random log line.`
  Expected handling: UI treats it as active error without contract.
- Prompt: `Tool output text.`
  Expected handling: Pipeline marks success from a substring.

## Anti-patterns

- stringly_typed_events
- log_line_as_state
- missing_revision
- raw_event_in_chat

## Regression Seeds

- unknown_event_degraded
- event_revision_monotonic
- terminal_tombstone_not_active
- debugger_category_contract

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
