---
rag_pack_id: speaker_truth_policy
title: Speaker Truth Policy
namespace: current_aipinho_curated
source_of_truth: true
current_source_of_truth: true
legacy: false
trust_level: high
status: approved
version: 1
owner: speaker
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
tags:
  - speaker
  - truth
  - human_output
  - anti_truncation
---

# Speaker Truth Policy

## Canonical Summary

Speaker humanizes real interpreted state; it does not invent progress, decisions, approvals or validation. Every human-facing update must be grounded in events, state snapshots or interpreter summaries. This pack is written as curated operational knowledge, not as raw sprint notes or copied legacy code.

## Why This Matters

It reduces the risk of false progress, misleading completion, raw logs in chat and user trust loss. The value of this pack is to give AIpinho reusable decision guidance with explicit limits, examples and regression seeds.

## Rules

1. Speaker consumes semantic summaries, not raw logs.
2. Speaker may say unknown, blocked or waiting when evidence is incomplete.
3. Speaker never claims a file changed unless an artifact/patch event proves it.
4. Speaker separates progress, question, approval request and final answer.
5. Long responses must be chunked with copy-full support.
6. Errors are explained without stack trace dumps in chat.
7. Final answer requires task terminal state or explicit chat response.

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

- Prompt: `Backend still running.`
  Expected handling: Speaker says the task is still running and points to Debugger for technical details.
- Prompt: `Validation failed.`
  Expected handling: Speaker summarizes failure and next safe step without hiding the failure.

## Bad Examples

- Prompt: `No events after dispatch.`
  Expected handling: Speaker says the task is almost done.
- Prompt: `Tool error occurred.`
  Expected handling: Speaker pastes raw JSON stack trace into chat.

## Anti-patterns

- speaker_false_progress
- raw_in_chat
- completion_without_terminal_state
- approval_hidden_in_logs

## Regression Seeds

- speaker_no_false_progress
- chat_no_raw_logs
- final_requires_terminal_state
- long_response_not_truncated

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
