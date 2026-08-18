---
rag_pack_id: pinhoforge_generalized_reference
title: PinhoForge Generalized Reference
namespace: legacy_pinhoabacaxi_curated
source_of_truth: false
current_source_of_truth: false
legacy: true
trust_level: medium
status: approved_with_scope_limit
version: 1
owner: context_kernel
created_from:
  - sprint_00_to_40_curated
allowed_purposes:
  - diagnosis
  - maintenance_diagnosis
  - regression_case_generation
  - policy_audit
  - anti_pattern_detection
  - architecture_lessons
  - historical_debugging
  - failure_analysis
  - migration_context
blocked_purposes:
  - current_endpoint_answer
  - current_config_generation
  - current_api_contract
  - current_port_reference
  - current_policy_source_of_truth
  - direct_patch_generation
  - direct_execution_plan
  - automatic_memory_update
requires_current_validation: true
sensitive: false
chunk_types:
  - architecture_note
  - anti_pattern
  - regression_seed
tags:
  - legacy
  - pinhoforge
  - generalization
  - anti_determinism
pinhoforge_policy:
  generalized_only: true
  deterministic_behavior_allowed: false
  direct_routing_target_allowed: false
  hardcoded_project_logic_allowed: false
---

# PinhoForge Generalized Reference

## Canonical Summary

PinhoForge is a conceptual legacy reference. It may inspire tooling, workbench and product architecture ideas, but must never become route, endpoint, skill, project behavior or implementation contract by name. This pack is written as curated operational knowledge, not as raw sprint notes or copied legacy code.

## Why This Matters

It reduces the risk of project-name determinism and accidental hardcoded behavior. The value of this pack is to give AIpinho reusable decision guidance with explicit limits, examples and regression seeds.

## Rules

1. Use PinhoForge only as generalized conceptual reference.
2. Do not route prompts because they mention PinhoForge.
3. Do not create hardcoded skills for the project name.
4. Do not infer current workspace from the name.
5. Do not define current endpoints from legacy PinhoForge notes.
6. Extract transferable patterns and state uncertainty.
7. Block deterministic project behavior.

## Allowed Use

- Use for `diagnosis` when the pack purpose and scope match the active contract.
- Use for `maintenance_diagnosis` when the pack purpose and scope match the active contract.
- Use for `regression_case_generation` when the pack purpose and scope match the active contract.
- Use for `policy_audit` when the pack purpose and scope match the active contract.
- Use for `anti_pattern_detection` when the pack purpose and scope match the active contract.
- Use for `architecture_lessons` when the pack purpose and scope match the active contract.
- Use for `historical_debugging` when the pack purpose and scope match the active contract.
- Use for `failure_analysis` when the pack purpose and scope match the active contract.
- Use for `migration_context` when the pack purpose and scope match the active contract.

## Blocked Use

- Do not use for `current_endpoint_answer`.
- Do not use for `current_config_generation`.
- Do not use for `current_api_contract`.
- Do not use for `current_port_reference`.
- Do not use for `current_policy_source_of_truth`.
- Do not use for `direct_patch_generation`.
- Do not use for `direct_execution_plan`.
- Do not use for `automatic_memory_update`.

## Good Examples

- Prompt: `Can PinhoForge inspire Skill Runtime?`
  Expected handling: Extract generic workflow lessons and compare with current contracts.
- Prompt: `Discuss PinhoForge UI idea.`
  Expected handling: Frame as product idea reference, not current UX requirement.

## Bad Examples

- Prompt: `PinhoForge.`
  Expected handling: Auto-select project route or create patch.
- Prompt: `Use PinhoForge behavior.`
  Expected handling: Hardcode skill or endpoint around that name.

## Anti-patterns

- project_name_default_route
- pinhoforge_skill_hardcode
- legacy_project_current_contract
- deterministic_project_behavior

## Regression Seeds

- pinhoforge_not_default_route
- pinhoforge_not_current_contract
- pinhoforge_generalized_only
- legacy_concept_not_hardcode

## Context Admission Notes

Admit this pack only with purpose `historical_diagnostic`, `failure_analysis`, `anti_pattern_detection` or `regression_case_generation`. Never admit it as current source of truth. Context admission must keep namespace, source trust, citation and current validation flags visible to Debugger.

## Validation Checklist

- The active purpose is allowed by frontmatter.
- The pack is cited by file and `rag_pack_id`.
- Blocked purposes were checked before use.
- Permission, capability, approval and validation gates remain authoritative.
- Any legacy or implementation-dependent claim is checked against current AIpinho state.
- Regression seeds are converted to reviewed tests before enforcement.

## Current Validation Notes

This is a legacy lesson only. It requires current validation and loses any conflict against current AIpinho policy, route, config or event state. The pack must not create deterministic routing by exact phrase, project name, path, sprint number or user identity.
