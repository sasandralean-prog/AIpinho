---
rag_pack_id: neon_cyberpunk_design_system
title: Neon Cyberpunk Design System
namespace: current_aipinho_curated
source_of_truth: true
current_source_of_truth: true
legacy: false
trust_level: high
status: approved
version: 1
owner: ux_design_system
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
  - doc_section
  - architecture_note
tags:
  - ux
  - design_system
  - neon
  - cyberpunk
---

# Neon Cyberpunk Design System

## Canonical Summary

AIpinho visual identity uses a cyberpunk/matrix/neon style: ciano for metainfo, green neon for normal chat/log, pink neon for error/attention/approval/danger, dark terminals and thin ciano borders. This pack is written as curated operational knowledge, not as raw sprint notes or copied legacy code.

## Why This Matters

It reduces the risk of visual inconsistency that hides severity, state or action priority. The value of this pack is to give AIpinho reusable decision guidance with explicit limits, examples and regression seeds.

## Rules

1. Metainfo uses ciano neon.
2. Normal chat and logs use green neon.
3. Danger, error, approval and attention use pink neon.
4. Cards use dark gray or blue-gray surfaces.
5. Terminals use black or very dark gray.
6. Borders are thin and ciano when interactive.
7. Long content is scrollable.
8. Copy actions are visible for logs and responses.
9. Raw stays hidden by default.

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

- Prompt: `Debugger filter card.`
  Expected handling: Dark card, ciano metadata, green sanitized text and pink error badge.
- Prompt: `Mobile chat.`
  Expected handling: Speaker bubble readable with copy button and no raw.

## Bad Examples

- Prompt: `Error in green.`
  Expected handling: Severity visually disappears.
- Prompt: `Raw panel open.`
  Expected handling: Technical data dominates chat.

## Anti-patterns

- raw_default_visual
- severity_color_confusion
- truncated_card_no_scroll
- surface_visual_drift

## Regression Seeds

- neon_tokens_present
- error_pink_attention
- metadata_ciano
- long_log_scroll_copy
- raw_hidden_default

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
