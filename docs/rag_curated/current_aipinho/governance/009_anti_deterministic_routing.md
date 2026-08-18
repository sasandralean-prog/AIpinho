---
rag_pack_id: anti_deterministic_routing
title: Anti-Deterministic Routing
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
  - config_policy
  - anti_pattern
  - regression_seed
tags:
  - intent
  - routing
  - anti_hardcode
  - policy
---

# Anti-Deterministic Routing

## Canonical Summary

Routing must be based on intent evidence, policy and context, not exact prompt phrases, project names, sprint numbers, paths or user identity. Determinism is reserved for safety gates and contracts. This pack is written as curated operational knowledge, not as raw sprint notes or copied legacy code.

## Why This Matters

It reduces the risk of case-specific behavior that passes one test and fails general prompts. The value of this pack is to give AIpinho reusable decision guidance with explicit limits, examples and regression seeds.

## Rules

1. Do not route on exact sprint labels.
2. Do not route on a specific project name.
3. Do not route on a specific path or IP.
4. Do not create user-specific behavior.
5. Use taxonomy, confidence, evidence spans and policy.
6. Allowed determinism includes secret block, dangerous route block and approval requirement.
7. Routing decisions must be explainable in Debugger.

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

- Prompt: `Prompt asks to analyze a project path.`
  Expected handling: Detect file analysis intent from structure and permissions, not project name.
- Prompt: `Prompt mentions PinhoForge.`
  Expected handling: Treat as a concept unless explicit task/workspace contract exists.

## Bad Examples

- Prompt: `if 'Sprint 43' then legacy_rag mode.`
  Expected handling: Case-specific routing.
- Prompt: `if user is Rafa then allow write.`
  Expected handling: User-specific bypass.

## Anti-patterns

- prompt_phrase_router
- workspace_name_router
- sprint_specific_logic
- ip_specific_behavior
- test_fixture_shortcut

## Regression Seeds

- project_name_not_route
- sprint_name_not_route
- path_string_not_permission
- safety_determinism_allowed

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
