# AIpinho Document Authority Index

Status: `CURRENT_AUTHORITY_INDEX`

Baseline inspected: AIpinho `main` through `6d3d3966e2f21b93632ff0a7ca5a6dbfdb0ff732`

External Control baseline inspected: `sasandralean-prog/AIpinho-FireTest-Control` `main` at `fe9daa384ff83c0c417677f07d4bb317301f812e`

Updated: 2026-08-25

## Purpose

This file routes readers to the right source and defines how conflicting evidence should be interpreted. It does not create runtime authority merely by naming a document, agent, repository, workflow, model, or conversation.

Core rules:

> Filename does not grant authority.

> A lock does not grant capability authority.

> A claimed identity string does not authenticate the claimant.

> Control Plane evidence proves the bounded Control operation it records; it does not silently become AIpinho runtime truth.

A document named `Final`, `Canonical`, `Current`, `MasterPlan`, or `Architecture` must still be interpreted through its internal status, date, implementation evidence, and agreement with current code/config/tests.

## Authority order for AIpinho runtime truth

When sources disagree about what AIpinho currently does, use this order:

1. current AIpinho production code and canonical contracts/config actually used by the path;
2. validated public/live runtime evidence for the relevant scope;
3. current issue registers and wave reports tied to that evidence;
4. architecture documents explicitly marked current/canonical and corroborated by implementation;
5. current repository/context orientation documents;
6. generated snapshots such as `genome/`;
7. historical architecture, audits, release notes, and `archaeology/`;
8. conversation-derived context/planning;
9. speculative ideas.

No lower layer may silently override a higher one.

The external Control Plane is a parallel operational authority domain. Its signed/structured results may prove what was requested, executed, observed, packaged, or returned by the Control Plane, but runtime claims still resolve through the hierarchy above.

## Class A — AIpinho runtime authority

These sources define or implement current AIpinho behavior. They remain subject to tests and observed runtime evidence.

| Source | Role | Authority note |
|---|---|---|
| `src/aipinho/` | Production implementation | Highest repository authority for implemented behavior. |
| `config/` | Active policy, registry, capability, runtime, and provider configuration | Authoritative for configured state when loaded by current code. Configuration existence alone does not prove successful execution. |
| `src/aipinho/schemas/` | Runtime/public contracts | Authoritative for current accepted/emitted shapes when used by live paths. |
| `AIpinho_Canonical_Flow.md` | Canonical runtime flow and ownership boundaries | Architectural control document; implementation details still resolve against code/config/tests/evidence. |
| `config/agents/agent_registry.yaml` | Configured internal/external-agent identities and capabilities | Enabled/configured does not equal end-to-end public validation. |
| `config/agents/delegation_policy.yaml` | Governed delegation routes and bounds | Current configured route authority. |
| `config/agents/hybrid_execution_policy.yaml` | Hybrid/Codex interpretation-island policy | Current configured hybrid-execution authority. |

## Class B — Validated runtime evidence

Validated public/live evidence proves bounded observations at the recorded scope. It does not automatically generalize beyond that scope.

| Source | Role | Authority note |
|---|---|---|
| `reports/runtime_consolidation/` wave reports | Runtime diagnostics, comparisons, issue state, verdicts | Interpret by exact branch/commit/run/scope. Newer evidence may supersede older evidence only where scope overlaps. |
| Issue registers tied to the active wave | Problem/evidence/resolution state | Keep evidence status separate from resolution status. |
| Tests tied to an implemented boundary | Unit/regression proof | Unit proof is not automatically public/live proof. |

The Context Pack currently retains the B3.5 runtime checkpoint as continuity context. That recorded pointer must not be assumed current without re-reading Git/code/reports.

## Class C — Current orientation and continuity

These documents summarize current state. They are deliberately subordinate to Class A and Class B.

| Source | Role | Authority note |
|---|---|---|
| `README.md` | Public repository orientation/current frontier | Must stay aligned with validated reports and `main`; not runtime proof by itself. |
| `AIpinho_context_pack/README_CONTEXT_PACK.md` | Context Pack entrypoint | Current continuity entrypoint. |
| `AIpinho_context_pack/docs/context/00_START_HERE.md` | Read order and authority rules | Current handoff orientation. |
| `AIpinho_context_pack/docs/context/03_ENGINEERING_WORKFLOW.md` | Engineering/control workflow continuity | Process guidance; not runtime implementation authority. |
| `AIpinho_context_pack/docs/context/05_RUNTIME_ARCHITECTURE_MAP.md` | Runtime architectural orientation and agent taxonomy | Orientation only; code/config/canonical flow win. |
| `AIpinho_context_pack/docs/context/09_CURRENT_FRONTIER.md` | Recorded runtime frontier | Must be reconciled when newer validated runtime evidence changes the frontier. |
| `AIpinho_context_pack/docs/context/11_HANDOFF_PROTOCOL.md` | Lúcio/agent continuity protocol | Handoff guidance; never substitutes for current repository inspection. |
| `AIpinho_context_pack/docs/context/current_state.json` | Machine-readable continuity state | Current-state pointer, not runtime state storage. |

## Class C2 — Engineering-agent infrastructure

These documents guide external engineering assistants working **ON** AIpinho. They do not define AIpinho runtime behavior and do not modify internal runtime-agent semantics.

| Source | Role | Authority note |
|---|---|---|
| `AGENTS.md` | Canonical repository-local engineering instruction entrypoint | Shared constitution/map for repository engineering agents. Subordinate to runtime code/config/evidence for runtime truth. |
| `.agents/skills/` | Reusable engineering workflow procedures | Portable engineering skill layer; not runtime skills or runtime agents. |
| `docs/engineering_agents/` | Detailed engineering operating policy | Git, platform, validation-authority, local-overlay, and handoff policy. |
| `replit.md` | Thin Replit adapter | Points back to `AGENTS.md`; not a second constitution. |
| `.github/agents/` | VS Code/GitHub Copilot role profiles | Specialized repository engineering roles; not AIpinho runtime agents. |

## Class C3 — External governed Control Plane

Repository:

`sasandralean-prog/AIpinho-FireTest-Control`

This is a separate operations/engineering authority domain that bridges GitHub and the local PC. It is not an AIpinho runtime-agent namespace and it does not outrank Class A/B for AIpinho runtime truth.

### Current Control authority sources

| Source | Role | Authority note |
|---|---|---|
| Control `main` code | Governs which named local operations exist | Highest authority for implemented Control capabilities, subject to its tests and real Actions evidence. |
| `control_plane/capabilities.py` | Named capability registry and bounded implementations | Caller authority is limited by capability IDs, targets, schemas, static plans, budgets, and provenance checks. |
| `.github/workflows/governed-local-runner.yml` | GitHub Actions execution/packaging/verdict contract | Current workflow accepts only the bounded operation-file input. |
| `control_plane/actions_result.py` | Result/manifest packaging contract | Governs bounded artifact staging and fail-closed result handling. |
| `reports/control_b1_0_d_*` | B1.0-D validation evidence | Governed test/profile/quick-validation proof at recorded scope. |
| `reports/control_b1_0_e_*` and `reports/actions_validation/` | B1.0-E/E.1 evidence | Actions result/artifact/rerun and persistent-runner proof at recorded scope. |
| `COMMUNICATION_SYNC_LUCIO.md` | Lúcio coordination directives | Read before the canonical shared ledger. Does not itself grant a capability. |
| `COMMUNICATION_SYNC.md` | Canonical shared coordination ledger | Locks/leases coordinate shared work only; they never create shell/runtime/FireTest authority. |

### Current proven Control state

```text
B1.0-D   = merged
B1.0-E   = merged
B1.0-E.1 = merged
runner aipinho-pc = official Windows service / Automatic / Running
service account = .\aipinho-runner
service-backed run = 32848578948
validated rerun attempt = 2
artifact = 9563333072
```

This proves the bounded GitHub Actions result/artifact/rerun loop through the persistent service runner.

### Current Control authority that is **not** granted

The following must be treated as false unless/until later code/evidence explicitly admits them:

```text
generic shell = NOT AUTHORIZED
arbitrary argv = NOT AUTHORIZED
arbitrary pytest = NOT AUTHORIZED
arbitrary path execution = NOT AUTHORIZED
dependency install = NOT AUTHORIZED
ChatGPT/Lúcio direct operation submission/start = NOT YET AUTHORIZED
Lúcio-operated FireTest = NOT YET AUTHORIZED
lucio.shell = NOT AUTHORIZED
```

Agreed future roadmap:

```text
F   -> Governed Operation Submission / start loop
F.1 -> Lúcio-operated bounded FireTest profiles
G   -> Lúcio Authenticated Control Channel
G.1 -> authenticated lucio.shell authority
```

Those labels are planning context only until merged code and validation prove them.

### Identity/authentication rule for future Lúcio authority

A field such as:

```text
requested_by = lucio
model = GPT-5.6 Sol
conversation_id = <value>
```

is provenance text, **not authentication**.

Future broad authority should require a trustworthy attestation/signing boundary that cryptographically binds at least the operation hash and anti-replay state, with short expiry and audit evidence. If a ChatGPT conversation/thread identifier can later be supplied by a trustworthy signer, it may be bound as provenance; a caller-provided string alone must never unlock shell authority.

### FireTest timeout rule

FireTest execution budgets must be capability/profile-specific. The agreed planning baseline is roughly:

```text
generic short operations -> short bounded budget
normal governed FireTest  -> about 900 seconds / 15 minutes
heavier FireTest profile  -> only via explicitly admitted larger ceiling
```

This is roadmap policy, not current FireTest authority.

## Class D — Active ledgers and partially current working documents

These may contain useful current entries, but their titles/statuses do not imply complete present coverage.

| Document | Interpretation |
|---|---|
| `AIpinho_BreakingChanges.md` | Active historical ledger; verify completeness for later waves. |
| `AIpinho_RemovedFiles.md` | Removal ledger; authoritative only for recorded removals. |
| `AIpinho_TestCoverageMatrix.md` | Partial test index, not proof of complete current coverage. |
| `AIpinho_CompatibilityMatrix.md` | Started compatibility/migration ledger; not final present-state authority. |
| `AIpinho_DuplicateClasses.md` | Working duplicate ledger; verify against current code. |
| `AIpinho_Hardcode_Remediation.md` | Working remediation plan/ledger; verify each item against current code. |

## Class E — Draft, target, or migration planning

These preserve design intent and migration history. They must not be used as evidence that a target is implemented.

| Document | Classification |
|---|---|
| `AIpinho_CanonicalDirectories.md` | Draft target ownership map. |
| `AIpinho_FinalArchitecture.md` | Target/draft despite the filename `FinalArchitecture`. |
| `AIpinho_Consolidation_MasterPlan.md` | Migration master plan/history. |
| `AIpinho_MigrationPlan.md` | Historical/ongoing migration plan. |
| `AIpinho_RuntimeContractBundle.md` | Draft contract design; current schemas/code determine implemented shape. |

The same rule applies to future Control labels such as F/F.1/G/G.1: roadmap naming does not create implemented authority.

## Class F — Historical evidence, snapshots, and archaeology

These preserve why decisions were made. They are valuable but not current runtime authority.

| Source | Classification |
|---|---|
| `AIpinho_Architecture_Audit.md` | Historical large audit corpus. |
| `AIpinho_Architecture_Audit_Consolidated_Report.md` | Historical audit consolidation. |
| `genome/` | Generated architecture snapshot/design DNA. |
| `archaeology/` | Historical project archaeology. |
| `RELEASE_NOTES_RC*.md` | Historical release snapshots. |
| timestamped `docs/architecture/*` inventories | Date-bounded snapshots unless separately revalidated. |
| old `FINAL_*` architecture files | Historical/design material unless current implementation/evidence reconfirms them. |

## Class G — Operational guides and surface matrices

User/operator guides are aids. Commands, ports, endpoints, and feature status must be checked against current scripts/config before use.

Examples include:

- `README_FIRST_RUN.md`
- `README_OPERATIONAL.md`
- `DESKTOP_MOBILE_PARITY_MATRIX.md`
- older/current-runtime inventory documents under `docs/architecture/`

## Agent/control vocabulary

Keep four categories separate:

```text
AIpinho internal runtime agents
    config/agents/
    src/aipinho/services/agents/

external agent islands
    Codex, Gemini, and other distinct governed participants/executors

engineering agents working on the repository
    AGENTS.md, .agents/skills/, docs/engineering_agents/,
    replit.md, .github/agents/, Codex, Devin, Replit, VS Code/Copilot, etc.

external Control Plane
    sasandralean-prog/AIpinho-FireTest-Control
    named governed PC operations + evidence return
```

Do not infer runtime-agent semantics from engineering-agent instructions, and do not infer shell/runtime/FireTest authority from the existence of the external Control Plane.

## Conflict resolution procedure

When two sources disagree:

1. state the contradiction explicitly;
2. identify each source's authority class and date/status;
3. inspect current code/config/contracts for the domain being claimed;
4. inspect the narrowest relevant validated evidence;
5. inspect current Git provenance/branch/HEAD;
6. preserve historical intent without promoting it;
7. update current orientation only after the target branch/main actually contains the claimed state.

For a disagreement between Control evidence and AIpinho runtime evidence, first classify the claim:

- **What did the Control Plane execute/observe/package?** -> Control code/manifest/result has authority at that scope.
- **What does AIpinho currently do at runtime?** -> AIpinho Class A/B wins.

## Update policy

Update this index when:
- a new canonical authority is established;
- a draft becomes implemented/current;
- a current document becomes historical;
- a new validated runtime wave changes the authority map;
- repository-local engineering-agent infrastructure changes materially;
- the external Control Plane gains or loses an authority class;
- a new authenticated remote-control boundary is actually implemented and validated.

Do not update it merely because a document, branch, roadmap label, or conversation claim exists.
