---
rag_pack_id: legacy_rag_sanitized_namespace
title: Legacy RAG Sanitized Namespace
namespace: legacy_pinhoabacaxi_curated
source_of_truth: false
current_source_of_truth: false
legacy: true
trust_level: medium
status: legacy_lesson_only
version: 1
owner: rag_service
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
  - rag
  - sanitization
  - namespace
---

# Legacy RAG Sanitized Namespace

## Canonical Summary

Legacy Pinhoabacaxi knowledge must live in a separate sanitized namespace with restricted purpose. It can teach history and failure patterns but cannot define current AIpinho behavior. This pack is written as curated operational knowledge, not as raw sprint notes or copied legacy code.

## Why This Matters

It reduces the risk of old runtime facts, ports, routes or bugs contaminating current architecture. The value of this pack is to give AIpinho reusable decision guidance with explicit limits, examples and regression seeds.

## Rules

1. Legacy namespace is not source of truth.
2. Legacy chunks require sanitization and citation.
3. Raw logs and secrets are never imported.
4. Conflicts are resolved in favor of current AIpinho.
5. Legacy use is limited to diagnosis, regression and lessons.
6. Legacy chunks cannot create direct execution plans.
7. Legacy vectors must carry current_truth_allowed=false.

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

- Prompt: `Old approval bug.`
  Expected handling: Use as regression seed for new approval flow.
- Prompt: `Old UI confusion.`
  Expected handling: Use as anti-pattern for UX review.

## Bad Examples

- Prompt: `Old route list.`
  Expected handling: Generate current API docs.
- Prompt: `Old port config.`
  Expected handling: Set current runtime port.

## Anti-patterns

- legacy_truth_leak
- raw_log_import
- legacy_port_current
- legacy_route_contract

## Regression Seeds

- legacy_namespace_not_current
- legacy_conflict_current_wins
- legacy_raw_sanitized
- legacy_seed_requires_scope

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
