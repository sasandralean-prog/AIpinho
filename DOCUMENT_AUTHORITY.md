# AIpinho Document Authority Index

Status: `CURRENT_AUTHORITY_INDEX`

Baseline inspected: `main` at `d993da01eb6022772969b6f7168bb3b9aa06c9e1`

Generated: 2026-08-19

## Purpose

This file routes readers to the right source. It does not create a new runtime authority and does not promote documents merely by listing them.

Core rule:

> Filename does not grant authority.

A document named `Final`, `Canonical`, `Current`, `MasterPlan`, or `Architecture` must still be interpreted through its internal status, date, implementation evidence, and agreement with current code/config/tests.

## Authority order

When sources disagree, use this order:

1. current production code and canonical contracts/config;
2. validated public runtime evidence;
3. current issue registers and wave reports;
4. architecture documents explicitly marked current/canonical and corroborated by implementation;
5. current repository/context orientation documents;
6. generated snapshots such as `genome/`;
7. historical architecture, audits, release notes, and `archaeology/`;
8. conversation-derived context and planning;
9. speculative ideas.

No lower layer may silently override a higher one.

## Class A — Runtime authority

These sources define or implement current behavior. They remain subject to tests and observed runtime evidence.

| Source | Role | Authority note |
|---|---|---|
| `src/aipinho/` | Production implementation | Highest repository authority for implemented behavior. |
| `config/` | Active policy, registry, capability, runtime, and provider configuration | Authoritative for configured state when loaded by current code. Configuration existence alone does not prove successful execution. |
| `src/aipinho/schemas/` | Runtime/public contracts | Authoritative for current accepted/emitted shapes when used by live paths. |
| `AIpinho_Canonical_Flow.md` | Canonical runtime flow and ownership boundaries | Status is `CANONICAL_FLOW_DEFINED`; use as the current architectural control document, but resolve implementation details against code/config/tests. |
| `config/agents/agent_registry.yaml` | Configured agent identities/capabilities | Current registry authority. Enabled/configured does not equal end-to-end public validation. |
| `config/agents/delegation_policy.yaml` | Governed delegation routes and bounds | Current configured route authority. |
| `config/agents/hybrid_execution_policy.yaml` | Codex modes and interpretation-island policy | Current configured hybrid-execution authority. |

## Class B — Validated current evidence

These sources prove bounded observations at their recorded scope. They do not automatically generalize beyond that scope.

| Source | Role | Authority note |
|---|---|---|
| `reports/runtime_consolidation/firetest5_h1c0_r2_18_*` | R2.18 public diagnostics, A+B comparison, evidence sufficiency, identity coverage, and issue state | Current validated R2.18 evidence. |
| `reports/runtime_consolidation/firetest5_h1c0_r2_exit_assessment.md` | R2 exit assessment | Supports `H1C0_R2_READY_FOR_R3`. |
| `reports/runtime_consolidation/firetest5_h1c0_r2_consolidated_issue_register.json` | Consolidated R2 issue state | Current for the R2 exit scope. |
| Tests tied to the implemented boundary | Unit/regression proof | Proof scope must be stated; unit proof is not public proof. |

Current validated conclusion:

```text
H1C0.R2 = H1C0_R2_READY_FOR_R3
FireTest 5 = NOT_READY
current blocked reason = MEDIA_IDENTITY_EVIDENCE_INSUFFICIENT
next runtime frontier = H1C0.R3.01
```

## Class C — Current orientation and continuity

These documents summarize current state. They are deliberately subordinate to Class A and Class B.

| Source | Role | Authority note |
|---|---|---|
| `README.md` | Public repository orientation and current frontier | Must remain aligned with validated reports and `main`. |
| `AIpinho_context_pack/README_CONTEXT_PACK.md` | Context Pack entrypoint | Current continuity entrypoint. |
| `AIpinho_context_pack/docs/context/00_START_HERE.md` | Read order and authority rules | Current handoff orientation. |
| `AIpinho_context_pack/docs/context/05_RUNTIME_ARCHITECTURE_MAP.md` | Two-layer architectural orientation and agent taxonomy | Orientation only; code/config and canonical flow win. |
| `AIpinho_context_pack/docs/context/09_CURRENT_FRONTIER.md` | Current project/runtime frontier | Must be updated when the validated frontier changes. |
| `AIpinho_context_pack/docs/context/current_state.json` | Machine-readable continuity state | Current state pointer, not runtime state storage. |

## Class C2 — Engineering-agent infrastructure

These documents guide external engineering assistants working ON AIpinho. They
do not define runtime behavior and do not modify AIpinho internal runtime-agent
semantics.

| Source | Role | Authority note |
|---|---|---|
| `AGENTS.md` | Canonical engineering instruction entrypoint | Shared constitution/map for repository engineering agents. Subordinate to runtime code/config/evidence for runtime truth. |
| `.agents/skills/` | Reusable engineering workflow procedures | Portable skill layer for engineering tasks; not runtime skills or runtime agents. |
| `docs/engineering_agents/` | Detailed engineering operating policy | Git, platform, validation-authority, local-overlay, and handoff policy for repository work. |
| `replit.md` | Thin Replit adapter | Points Replit Agent back to `AGENTS.md`; not a second constitution. |
| `.github/agents/` | VS Code/GitHub Copilot role profiles | Specialized repository engineering roles; not AIpinho runtime agents. |

## Class D — Active ledgers and partially current working documents

These may contain useful current entries, but their titles/statuses do not imply complete coverage of the current repository.

| Document | Internal status | Interpretation |
|---|---|---|
| `AIpinho_BreakingChanges.md` | `NO_BREAKING_CHANGES` plus dated wave entries | Active historical ledger; verify completeness for later waves. |
| `AIpinho_RemovedFiles.md` | `FILES_REMOVED_WITH_TESTED_REPLACEMENTS` | Removal ledger; authoritative only for recorded removals. |
| `AIpinho_TestCoverageMatrix.md` | `WAVE_9_CANONICAL_TEST_MATRIX_STARTED` | Partial test index, not a claim of complete present coverage. |
| `AIpinho_CompatibilityMatrix.md` | `COMPATIBILITY_MATRIX_STARTED` | Started migration/compatibility ledger; not a final present-state matrix. |
| `AIpinho_DuplicateClasses.md` | `DUPLICATE_CLASS_LEDGER_STARTED` | Working ledger; not proof that every duplicate remains current. |
| `AIpinho_Hardcode_Remediation.md` | `HARDCODE_REMEDIATION_PLAN_STARTED` | Working plan/ledger; verify each entry against current code. |

## Class E — Draft, target, or migration planning

These documents preserve design intent and migration history. They must not be used as evidence that a target is implemented.

| Document | Internal status | Classification |
|---|---|---|
| `AIpinho_CanonicalDirectories.md` | `CANONICAL_DIRECTORIES_DRAFTED` | Draft target ownership map. Unresolved `or` choices are not canonical runtime decisions. |
| `AIpinho_FinalArchitecture.md` | `TARGET_ARCHITECTURE_DRAFT` | Target/draft despite the filename `FinalArchitecture`. |
| `AIpinho_Consolidation_MasterPlan.md` | `CONSOLIDATION_MASTERPLAN_STARTED` | Migration master plan and historical consolidation guidance. |
| `AIpinho_MigrationPlan.md` | `MIGRATION_PLAN_STARTED` | Historical/ongoing migration plan; not current runtime truth by itself. |
| `AIpinho_RuntimeContractBundle.md` | `RUNTIME_CONTRACT_BUNDLE_DRAFTED` | Draft contract design; current schemas/code determine implemented shape. |

## Class F — Historical evidence, snapshots, and archaeology

These preserve why decisions were made. They are valuable but not current runtime authority.

| Source | Classification | Notes |
|---|---|---|
| `AIpinho_Architecture_Audit.md` | Historical large audit corpus | Use bounded sections; do not treat its size or filename as current truth. |
| `AIpinho_Architecture_Audit_Consolidated_Report.md` | Historical audit consolidation | Generated 2026-07-31 from the audit state at that time. |
| `genome/` | Generated architecture snapshot/design DNA | The summary was generated 2026-07-30 and explicitly contains `UNKNOWN` areas. |
| `archaeology/` | Historical project archaeology | Context and rationale only. |
| `RELEASE_NOTES_RC1.md`, `RELEASE_NOTES_RC2.md`, `RELEASE_NOTES_RC3.md` | Historical release snapshots | Do not interpret RC numbering as the current H1C0 wave state. |
| `docs/architecture/CURRENT_RUNTIME_INVENTORY_20260621.md` | Timestamped historical inventory | Date-bounded snapshot. |
| `docs/architecture/FINAL_MULTI_AGENT_ARCHITECTURE.md` | RC1-era architecture snapshot | The word `FINAL` does not override current code/config or later canonical flow. |
| `docs/architecture/MULTI_AGENT_KERNEL_ROADMAP*.md` | Roadmap/history | Directional material; verify completed items independently. |

## Class G — Operational guides and surface matrices

These are user/operator aids. Commands, ports, endpoints, and feature status must be checked against current scripts/config before use.

| Document | Classification |
|---|---|
| `README_FIRST_RUN.md` | RC3-era first-run guide; operationally useful but potentially stale. |
| `README_OPERATIONAL.md` | RC3-era operational guide; verify scripts, ports, and current startup behavior. |
| `DESKTOP_MOBILE_PARITY_MATRIX.md` | Surface-status snapshot; not a runtime authority. |
| `docs/architecture/CURRENT_RUNTIME_INVENTORY.md` | Sprint-0 inventory; useful orientation, not guaranteed current despite its filename. |

## Empty architecture placeholders

The following files currently have zero bytes and therefore provide no architectural evidence:

```text
docs/architecture/010_runtime_flow.md
docs/architecture/020_policy_kernel.md
docs/architecture/030_multirole_pipeline.md
docs/architecture/040_memory.md
docs/architecture/050_rag.md
docs/architecture/060_tools_and_skills.md
docs/architecture/070_security_model.md
```

Rule:

> File existence is not documentation completeness.

Do not populate, delete, or promote these placeholders merely to make the tree look finished. Each requires an explicit owner and evidence-backed purpose.

## Agent-document interpretation

Keep three categories separate:

```text
AIpinho internal runtime agents
    config/agents/
    src/aipinho/services/agents/

external agent islands
    Codex, Gemini, and other distinct governed participants/executors

engineering agents working on the repository
    AGENTS.md, .agents/skills/, docs/engineering_agents/,
    replit.md, .github/agents/, Codex, Devin, Replit, VS Code/Copilot, etc.
```

`AGENTS.md` is now the canonical repository-local engineering instruction
entrypoint. `.agents/skills/` contains reusable engineering procedures.
`docs/engineering_agents/` contains detailed operating policy.

These files guide engineering assistants working ON AIpinho. They do not become
runtime authority and must never be interpreted as mutating `config/agents/` or
`src/aipinho/services/agents/`.

Documents under `docs/architecture/` describing Codex, Gemini, Lúcio, delegation, memory gateway, event bus, policy kernel, or tool gateway may describe implemented subsystems or historical design phases. Verify them against the current registry, policy configuration, services, tests, and runtime evidence before treating them as present behavior.

## Conflict resolution procedure

When two sources disagree:

1. state the contradiction explicitly;
2. identify each source's class and date/status;
3. inspect current code/config/contracts;
4. inspect the narrowest relevant validated evidence;
5. preserve historical intent without promoting it;
6. update the current orientation document only after the target branch contains the claimed state.

## Update policy

Update this index when:
- a new canonical authority is established;
- a draft becomes implemented/current;
- a current document becomes historical;
- a new validated wave changes the authority map;
- repository-local engineering-agent infrastructure is introduced.

Do not update it merely because a new document was added.
