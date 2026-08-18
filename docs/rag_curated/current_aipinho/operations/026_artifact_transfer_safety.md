---
rag_pack_id: artifact_transfer_safety
title: Artifact Transfer Safety
namespace: current_aipinho_curated
source_of_truth: true
current_source_of_truth: true
legacy: false
trust_level: high
status: approved
version: 1
owner: artifact_service
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
  - decision_record
tags:
  - artifacts
  - transfer
  - sha256
  - security
---

# Artifact Transfer Safety

## Canonical Summary

Artifact transfer uses artifact ids, manifest metadata, sha256, allowed path scopes and validation. It must not expose arbitrary filesystem paths or trust uploaded zip content blindly. This pack is written as curated operational knowledge, not as raw sprint notes or copied legacy code.

## Why This Matters

It reduces the risk of path traversal, wrong artifact delivery, corrupted previews and unsafe export/import. The value of this pack is to give AIpinho reusable decision guidance with explicit limits, examples and regression seeds.

## Rules

1. Artifacts are addressed by artifact_id, not arbitrary path.
2. Every transfer includes sha256 and size.
3. Zip contents require path normalization and traversal checks.
4. Preview and final artifact hashes must match when required.
5. Downloads use configured artifact store.
6. Sensitive artifacts require policy check.
7. Post-write validation is required before success.

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

- Prompt: `Create review zip.`
  Expected handling: Generate manifest, hashes and safe relative entries.
- Prompt: `Install artifact.`
  Expected handling: Verify hash against approved preview.

## Bad Examples

- Prompt: `User gives path.`
  Expected handling: Serve arbitrary file from disk.
- Prompt: `Zip upload.`
  Expected handling: Extract without checking paths.

## Anti-patterns

- path_based_download
- zip_slip
- hash_mismatch_ignored
- artifact_write_no_validation

## Regression Seeds

- artifact_id_required
- zip_path_traversal_blocked
- sha256_mismatch_blocks_write
- post_write_validation_required

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
