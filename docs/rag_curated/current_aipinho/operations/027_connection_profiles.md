---
rag_pack_id: connection_profiles
title: Connection Profiles
namespace: current_aipinho_curated
source_of_truth: true
current_source_of_truth: true
legacy: false
trust_level: high
status: approved
version: 1
owner: connection_service
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
  - connection
  - mobile
  - adb
  - wifi
  - tailscale
---

# Connection Profiles

## Canonical Summary

Connection profiles describe Localhost/ADB, Wi-Fi/LAN, Tailscale and Manual access without hardcoding operational truth. Profiles are presets that users can edit and validate. This pack is written as curated operational knowledge, not as raw sprint notes or copied legacy code.

## Why This Matters

It reduces the risk of mobile offline state caused by wrong bind host, stale IP or hidden base URL behavior. The value of this pack is to give AIpinho reusable decision guidance with explicit limits, examples and regression seeds.

## Rules

1. Profiles are config-driven presets.
2. Users can edit host and port.
3. UI may omit protocol visually but stores normalized URL.
4. Test connection checks health and source-root status.
5. Wi-Fi requires LAN bind and firewall rule.
6. Tailscale requires detected Tailscale IP or manual override.
7. Connection errors are specific and actionable.

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

- Prompt: `Wi-Fi profile.`
  Expected handling: Shows editable host, normalized http URL and Test connection.
- Prompt: `ADB profile.`
  Expected handling: Uses localhost reverse when available.

## Bad Examples

- Prompt: `Hardcoded IP.`
  Expected handling: Cannot edit when network changes.
- Prompt: `Offline.`
  Expected handling: Shows generic unknown without diagnostics.

## Anti-patterns

- hardcoded_mobile_ip
- protocol_double_insert
- silent_connection_fail
- profile_without_test

## Regression Seeds

- wifi_profile_editable
- tailscale_profile_editable
- health_connection_test
- offline_error_actionable

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
