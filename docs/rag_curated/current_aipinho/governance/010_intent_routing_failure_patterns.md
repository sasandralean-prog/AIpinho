---
rag_pack_id: intent_routing_failure_patterns
title: Intent Routing Failure Patterns
namespace: current_aipinho_curated
source_of_truth: true
current_source_of_truth: true
legacy: false
trust_level: high
status: approved
version: 1
owner: prompt_intelligence
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
  - anti_pattern
  - regression_seed
  - architecture_note
tags:
  - intent
  - routing
  - failure_patterns
  - confirmation
---

# Intent Routing Failure Patterns

## Canonical Summary

Common routing failures include simple chat becoming task, read-only becoming patch, image mention becoming OCR, log mention becoming raw ingestion, and ambiguous prompt skipping confirmation. This pack is written as curated operational knowledge, not as raw sprint notes or copied legacy code.

## Why This Matters

It reduces the risk of unwanted execution, noisy plans, unsafe context admission and user confusion. The value of this pack is to give AIpinho reusable decision guidance with explicit limits, examples and regression seeds.

## Rules

1. Greetings and capability questions stay chat unless user asks for task.
2. Self-analysis does not require workspace.
3. Read-only analysis cannot imply patch.
4. Image mention does not imply OCR unless attached or requested.
5. Log mention does not admit raw logs automatically.
6. Ambiguity should produce confirmation choices.
7. Multi-intent prompts must expose segments before execution when risk exists.

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

- Prompt: `What can you do?`
  Expected handling: Answer capability in chat; no task.
- Prompt: `Analyze this report and generate prompts.`
  Expected handling: Segment into analysis and prompt generation with read-only contract.

## Bad Examples

- Prompt: `OlÃ¡.`
  Expected handling: Create a task.
- Prompt: `Veja se estÃ¡ ok.`
  Expected handling: Start operational patch without confirmation.

## Anti-patterns

- greeting_task
- capability_plan_execution
- image_magic_context
- log_raw_ingestion
- ambiguous_autorun

## Regression Seeds

- hello_not_task
- capability_not_execution_plan
- ambiguous_prompt_confirmation
- multi_intent_segments_visible

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
