---
rag_pack_id: rag_as_evidence_not_truth
title: RAG as Evidence, Not Truth
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
  - anti_pattern
  - regression_seed
tags:
  - rag
  - evidence
  - truth
  - policy
---

# RAG as Evidence, Not Truth

## Canonical Summary

RAG provides contextual evidence. It does not replace Policy Kernel, Context Kernel, Event Contract Registry, current configs or validation results. This pack is written as curated operational knowledge, not as raw sprint notes or copied legacy code.

## Why This Matters

It reduces the risk of retrieved text overriding live policy, stale configuration or current runtime state. The value of this pack is to give AIpinho reusable decision guidance with explicit limits, examples and regression seeds.

## Rules

1. RAG without source_ref does not enter.
2. RAG without citation does not support factual claim.
3. Legacy RAG never wins over current AIpinho source.
4. Stale RAG is degraded or rejected.
5. RAG does not execute tools.
6. RAG does not write memory.
7. RAG does not define current endpoint when namespace is legacy.

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

- Prompt: `Old bug similar to speaker false progress.`
  Expected handling: Use as anti-pattern and regression seed.
- Prompt: `Current policy says apply requires approval.`
  Expected handling: Use cited current source as supporting evidence.

## Bad Examples

- Prompt: `Old report mentions port 8088.`
  Expected handling: Answer that 8088 is current port.
- Prompt: `RAG says a patch helped.`
  Expected handling: Apply patch without preview.

## Anti-patterns

- retrieval_as_authority
- stale_rag_primary
- legacy_endpoint_current
- rag_triggers_tool

## Regression Seeds

- uncited_rag_blocked
- stale_rag_not_primary
- legacy_endpoint_not_current
- rag_auto_ingest_blocked

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
