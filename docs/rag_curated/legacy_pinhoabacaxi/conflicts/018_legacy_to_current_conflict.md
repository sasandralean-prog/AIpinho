---
rag_pack_id: legacy_to_current_conflict
title: Legacy-to-Current Conflict
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
  - anti_pattern
  - regression_seed
  - decision_record
tags:
  - legacy
  - conflict
  - current_truth
  - deprecation
---

# Legacy-to-Current Conflict

## Canonical Summary

Legacy references to old ports, roots, endpoints, adapters or runtime files are conflict signals. They help diagnose migration risks but cannot override current configs, routes or contracts. This pack is written as curated operational knowledge, not as raw sprint notes or copied legacy code.

## Why This Matters

It reduces the risk of answering with stale endpoint contracts or resurrecting deprecated flows. The value of this pack is to give AIpinho reusable decision guidance with explicit limits, examples and regression seeds.

## Rules

1. Detect old local ports as legacy evidence, not current port truth.
2. Detect old roots as historical source paths.
3. Detect deprecated endpoints as anti-patterns.
4. Detect legacy runtime files as migration context only.
5. Resolve conflicts by current AIpinho source priority.
6. Expose conflict reasoning in Debugger.
7. Require current validation before any operational use.

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

- Prompt: `Legacy says /chat was operational.`
  Expected handling: Flag as deprecated pattern and prefer current chat contract.
- Prompt: `Old root appears.`
  Expected handling: Treat as legacy citation path only.

## Bad Examples

- Prompt: `Legacy report mentions /v2 route.`
  Expected handling: Assume current behavior without checking current router.
- Prompt: `Old backend path.`
  Expected handling: Patch old project or runtime.

## Anti-patterns

- deprecated_route_resurrection
- old_root_as_workspace
- legacy_adapter_dependency
- current_docs_from_legacy

## Regression Seeds

- legacy_endpoint_not_current
- old_port_not_current
- legacy_root_not_workspace
- conflict_debugger_trace

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
