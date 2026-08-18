---
rag_pack_id: raw_sanitized_copy_policy
title: Raw Sanitized Copy Policy
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
  - anti_pattern
tags:
  - raw
  - sanitization
  - copy
  - debugger
---

# Raw Sanitized Copy Policy

## Canonical Summary

Raw technical data is hidden by default, accessed only through explicit copy/view controls, and must be redacted or policy-checked. Sanitized logs are the default technical view. This pack is written as curated operational knowledge, not as raw sprint notes or copied legacy code.

## Why This Matters

It reduces the risk of secret exposure, chat pollution and accidental copying of unsafe technical data. The value of this pack is to give AIpinho reusable decision guidance with explicit limits, examples and regression seeds.

## Rules

1. Chat never shows raw.
2. Debugger shows sanitized log by default.
3. Raw requires explicit user action.
4. Raw copy uses redaction and policy checks.
5. Copy full sanitized log must include full text, not visible excerpt only.
6. Blocked raw access reports why.
7. Secret scan applies before raw export.

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

- Prompt: `User copies log.`
  Expected handling: Receives full sanitized log with source metadata.
- Prompt: `Raw blocked by secret scan.`
  Expected handling: UI shows raw unavailable and reason.

## Bad Examples

- Prompt: `Error response.`
  Expected handling: Paste full stack trace into chat.
- Prompt: `Copy button.`
  Expected handling: Copies truncated visible lines only.

## Anti-patterns

- raw_in_chat
- copy_truncated_text
- raw_without_redaction
- secret_in_export

## Regression Seeds

- chat_no_raw
- copy_full_sanitized
- raw_requires_explicit_action
- secret_scan_blocks_raw

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
