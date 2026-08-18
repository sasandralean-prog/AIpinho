---
rag_pack_id: external_connector_safety
title: External Connector Safety
namespace: current_aipinho_curated
source_of_truth: true
current_source_of_truth: true
legacy: false
trust_level: high
status: approved
version: 1
owner: connector_policy
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
  - skill_contract
  - config_policy
tags:
  - connectors
  - network
  - browser
  - github
  - openai_docs
---

# External Connector Safety

## Canonical Summary

External connectors such as GitHub, Hugging Face, Notion, Canva, OpenAI docs, browser, computer-use and shell require explicit policy context and safe purpose. Connector availability is not permission. This pack is written as curated operational knowledge, not as raw sprint notes or copied legacy code.

## Why This Matters

It reduces the risk of data leakage, unintended external state mutation and hidden dependency on network/session state. The value of this pack is to give AIpinho reusable decision guidance with explicit limits, examples and regression seeds.

## Rules

1. Network connectors require allowed purpose and user-visible intent.
2. Write-capable connectors require approval or dedicated policy grant.
3. Browser and computer-use actions must not bypass safer APIs when available.
4. OpenAI docs lookups are documentation evidence, not runtime permission.
5. Secrets must never be pasted into external targets.
6. Connector failures are reported clearly.
7. External evidence requires citation/source when used in output.

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

- Prompt: `Check official docs.`
  Expected handling: Use docs connector for current API facts and cite source.
- Prompt: `Create GitHub PR.`
  Expected handling: Require explicit publishing intent and preserve review trail.

## Bad Examples

- Prompt: `Need context.`
  Expected handling: Opening logged-in Chrome and copying private data without consent.
- Prompt: `Connector installed.`
  Expected handling: Using it for write action without approval.

## Anti-patterns

- connector_as_permission
- hidden_browser_write
- uncited_external_fact
- secret_to_connector

## Regression Seeds

- connector_write_requires_approval
- docs_evidence_not_permission
- network_unavailable_clear_error
- browser_not_default_when_api_exists

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
