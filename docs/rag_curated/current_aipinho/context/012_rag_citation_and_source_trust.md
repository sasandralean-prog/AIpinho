---
rag_pack_id: rag_citation_and_source_trust
title: RAG Citation and Source Trust
namespace: current_aipinho_curated
source_of_truth: true
current_source_of_truth: true
legacy: false
trust_level: high
status: approved
version: 1
owner: rag_service
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
  - doc_section
tags:
  - rag
  - citation
  - trust
  - source
---

# RAG Citation and Source Trust

## Canonical Summary

RAG results need source reference, citation, namespace trust and scope before they support any factual claim. Trust level affects admission, ranking and conflict handling. This pack is written as curated operational knowledge, not as raw sprint notes or copied legacy code.

## Why This Matters

It reduces the risk of hallucinated facts backed by anonymous retrieval or stale source. The value of this pack is to give AIpinho reusable decision guidance with explicit limits, examples and regression seeds.

## Rules

1. Every RAG hit carries namespace, source_ref and citation.
2. High-trust current sources rank above legacy references.
3. Missing citation blocks factual use.
4. Conflicting sources require explicit resolution.
5. Legacy citations must state historical scope.
6. RAG cannot grant permission or create approval.
7. Source trust must be visible in Debugger when used.

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

- Prompt: `Current policy config cited.`
  Expected handling: Use as policy evidence.
- Prompt: `Legacy report cited.`
  Expected handling: Use as anti-pattern with scope warning.

## Bad Examples

- Prompt: `Vector hit no source.`
  Expected handling: Use it to answer current API.
- Prompt: `Legacy route citation.`
  Expected handling: Generate current route docs.

## Anti-patterns

- anonymous_rag
- citation_free_claim
- legacy_route_current_api
- trust_level_ignored

## Regression Seeds

- uncited_rag_blocked
- source_trust_affects_ranking
- legacy_citation_scoped
- conflict_requires_resolution

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
