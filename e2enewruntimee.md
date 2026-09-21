# AIpinho — E2E New Runtime: Mission Authority, Dynamic Resources and Governed Continuation

**Document status:** canonical execution plan for the E2E New Runtime wave
**Repository:** sasandralean-prog/AIpinho
**Target branch for canonization:** main
**Initial main baseline:** 7ad2b1532a53cd3becee7154a6e08dec28b00b0d
**Pre-wave diagnostic branch snapshot:** fix/firetest5-mission-runtime-intentmap @ cfba76ee094018f9680c0a63eda6378cb118a076
**Created:** 2026-09-16
**Owner of final operational authority:** AIpinho canonical runtime

---

## 1. Authority and purpose

This document is the execution map for the E2E New Runtime wave. It exists so that every sprint can be implemented, validated and closed without losing the architectural direction established by the runtime diagnosis.

This document is not higher authority than production code, canonical contracts/configuration, validated RuntimeTruth, or validated runtime evidence. When implementation and this plan diverge, the divergence must be investigated and this document must be updated only after evidence justifies the change.

The document must remain generic. FireTest 5 and Pinhoabacaxi Músicas are probes and evidence sources, not production configuration.

The wave is successful only when the runtime can perform the same governed lifecycle for unrelated projects, local workspaces and remote repositories declared dynamically by the human prompt.

---

## 2. Problem statement

The pre-wave diagnosis showed that the runtime had already corrected several important ingress and workspace-scope problems, but the complete end-to-end mission lifecycle remained fragmented across intent, workspace policy, approvals, agent policy, shell policy, Git/network policy and mission orchestration.

The historical RAW failure exposed an initial chain:

~~~text
compound repair mission
→ phrase "subdirectory" misread as create_directory
→ filesystem_create_directory
→ premature approval boundary
→ missing analysis_ref
→ no execution
~~~

The active correction branch fixed much of that entry path:

~~~text
prompt
→ semantic operational mission
→ workspace_fix_request
→ real readonly discovery TaskRun
→ frozen workspace scope
~~~

However, the diagnosis also exposed deeper structural gaps:

- mission strategy is persisted but does not yet materialize the next TaskRun automatically;
- declared capabilities are not the same thing as explicit human authority;
- Tool Gateway and TaskRuntime can disagree about Git/network;
- create_directory is implemented by tools but absent from parts of the canonical permission vocabulary;
- direct filesystem writes do not propagate dynamic scope as consistently as patch execution;
- Git classification is too coarse;
- Git network operations are not expressed as composed capabilities;
- remote repositories are not yet first-class dynamic resources;
- clean promotion staging is not yet a dynamically derived mission resource;
- mission completion criteria are not yet bound across phases as one final truth contract.

This wave closes those gaps without creating a second runtime.

---

## 3. Architectural target

The target lifecycle is:

~~~text
Human Prompt
    │
    ├─ semantic mission intent
    ├─ mission execution strategy
    ├─ local resource scopes
    ├─ remote repository scopes
    ├─ explicit human authority
    ├─ negative constraints
    └─ completion requirements
             │
             ▼
       Frozen Mission Contract
             │
             ▼
   Canonical TaskRuntime phases
             │
             ├─ Discovery
             ├─ Planning
             ├─ Mutation / Patch
             ├─ Build / Test / Smoke
             ├─ Promotion Staging
             └─ Git / Remote Promotion
             │
             ▼
   Cross-phase evidence binding
             │
             ▼
   RuntimeTruth → CanonicalOperationState → SpeakerTruth
~~~

No planner, agent, gateway, shell adapter, Git adapter or UI surface may independently expand authority.

---

## 4. Core separation of concerns

The runtime must distinguish four questions that were previously too easy to conflate:

1. **What is requested?**
2. **What has the human explicitly authorized?**
3. **What resources are in scope?**
4. **What does global policy permit?**

The executable set is the intersection:

~~~text
requested capability
∩ explicit human authority
∩ resource permission
∩ current phase contract
∩ global policy
= executable capability
~~~

A capability mentioned in prose is not automatically authorized.

A mutable workspace is not unrestricted execution authority.

An allowed remote repository is not arbitrary network access.

A successful tool invocation is not mission completion.

---

## 5. Canonical resource model

The new runtime must treat resources as explicit, frozen mission objects rather than infer them repeatedly from text.

### 5.1 Local workspace resource

Minimum fields:

~~~yaml
resource_type: local_workspace
resource_id: <stable mission-local id>
path: <absolute canonical path>
role: source_readonly | target_mutable | system_mutable | mission_staging | protected | forbidden
permissions: [...]
constraints: [...]
evidence: [...]
~~~

### 5.2 Remote repository resource

Remote repositories are dynamic prompt-derived resources exactly like local workspaces.

Minimum fields:

~~~yaml
resource_type: remote_repository
resource_id: <stable mission-local id>
provider: github
owner: <owner>
repository: <repo>
canonical_remote: <normalized remote identity>
branches:
  allowed: [...]
permissions:
  clone: true|false
  fetch: true|false
  pull_fast_forward: true|false
  commit: true|false
  push: true|false
constraints:
  force_push: false
  rewrite_history: false
  delete_remote_branch: false
evidence: [...]
~~~

No repository name may be hardcoded into production policy to make a mission pass.

The prompt may add a repository to mission scope, but cannot override global host/network deny rules.

### 5.3 Mission staging resource

A mission may derive a temporary local resource from an authorized remote repository.

~~~yaml
resource_type: local_workspace
role: mission_staging
derived_from: <remote_repository resource id>
lifetime: mission
root_policy: globally_safe_staging_root
~~~

The global configuration defines only safe staging boundaries. The project/repository identity is derived from the mission.

---

## 6. Remote repository normalization rules

Repository identity must be normalized before policy comparison.

Equivalent forms for the same GitHub repository may include:

~~~text
https://github.com/owner/repo
https://github.com/owner/repo.git
git@github.com:owner/repo.git
~~~

Normalization must preserve:

- provider/host;
- owner;
- repository;
- branch scope;
- operation being requested.

Normalization must never make distinct repositories equivalent.

Explicitly forbidden remotes in the prompt must become negative constraints and remain forbidden for the mission.

Before any push, the runtime must observe the actual configured remote and branch and compare them with the frozen remote repository resource.

---

## 7. Non-negotiable invariants

These invariants apply to every sprint in this wave:

1. Prompt-derived allow does not override global protection or deny policy.
2. Mentioned capability is not the same as authorized capability.
3. Mutable workspace is not unrestricted execution.
4. Allowed remote repository is not arbitrary network permission.
5. Git permission is not destructive Git permission.
6. One authorization may span phases only inside the frozen mission authority.
7. Child TaskRuns may narrow authority but may never expand it.
8. Every dynamically derived resource must have provenance.
9. Planner cannot grant authority.
10. Executor cannot reinterpret intent.
11. Tool Gateway cannot invent permissions.
12. Agents and roles remain subordinate to TaskRuntime.
13. RuntimeTruth remains the final completion authority.
14. SpeakerTruth may never upgrade partial, blocked or failed runtime truth.
15. FireTest evidence never becomes runtime configuration.
16. Unknown authority is fail-closed.
17. Producer completion does not authorize consumer use.
18. No success claim exists without evidence bound to the declared completion contract.
19. No project name, local path, file extension or repository identity may become generic production truth.
20. Global destructive operations remain denied unless a separate explicit governed design introduces them.

---

## 8. Wave status board

| Sprint | Name | Current state | Exit dependency |
| --- | --- | --- | --- |
| M1 | Canonical Mission Contract | CLOSED | none |
| M2 | Dynamic Local Resource Scopes | CLOSED | M1 |
| M3 | Dynamic Remote Repository Scopes | CLOSED | M1, M2 vocabulary |
| M4 | Explicit Human Authority / Mission Grants | CLOSED | M1–M3 |
| M5 | Unified Capability and Policy Kernel | CLOSED | M1–M4 |
| M6 | Governed Git and Network Execution | CLOSED | M3–M5 |
| M7 | Mission Staging and Derived Resources | CLOSED | M2, M3, M6 |
| M8 | Mission Continuation Engine | CLOSED | M1–M7 |
| M9 | Cross-Phase Truth and Completion Contract | CLOSED | M1–M8 |
| M10 | Fresh Manual E2E FireTest and Consolidation | IN_PROGRESS | M1–M9 |

No sprint is considered complete because code was written. Completion requires its Definition of Done and validation evidence.

### M1 closure evidence — 2026-09-16

- validated implementation/main SHA: `489ca3bd37eb8584b7b58d86526a203897965121`;
- canonical `MissionContract` and `MissionContractBinding` are frozen before planning inside `TaskRuntimeService`;
- source prompt is retained only as SHA/provenance at this boundary; downstream runtime does not reinterpret free-form prompt text to gain authority;
- TaskRuns persist and rehydrate the contract, bootstrap binding, mission identity and authority hash;
- child TaskRuns inherit the parent contract by default; explicit revisions may only narrow capabilities/resources or add constraints and validation/completion requirements;
- mission binding is projected into durable TaskRun indexes and creation/bootstrap event metadata;
- new M1 contract suite: `10 passed`;
- broader runtime/semantic regression: `92 passed / 1 failed`; the single failure (`test_service_waits_for_approval_when_policy_requires_apply_patch`) reproduces unchanged on baseline `630d454f` from an unregistered detached worktree and is not an M1 regression;
- integration note: callers that do not yet supply a persistent `source_message_id` receive a deterministic synthetic source reference. Public ingress should bind the real persistent message identity as mission bootstrap is consolidated in later sprints.

Next sprint: **M2 - Dynamic Local Resource Scopes**.

### M2 closure evidence - 2026-09-17

- validated implementation/main SHA: `bb69739eb748472ebb36c359491bc4e7a895e24c`;
- prompt-level local paths are compiled at semantic ingress into frozen `MissionResourceScope` entries and downstream runtime consumes only the frozen `MissionContract`;
- `target_mutable` scope is permission-specific: role alone never authorizes create-directory, create/modify-file, patch or shell operations;
- static `protected`, `forbidden` and `source_readonly` workspace policy remains stronger than prompt-derived mutable scope;
- `WorkspaceContext`, `TaskRunGuard`, patch planning/target guard and final Agent Tool Gateway use the same frozen local-resource authority;
- project-specific patch root allowlists were removed; `patch_target_policy.allowed_roots` is empty and global deny boundaries remain;
- a previously unregistered temporary target proved create-directory, create-file, modify-file, governed patch contract, build shell and test shell while a second readonly resource in the same mission rejected writes;
- dedicated dynamic-local-resource suite: `10 passed`; semantic/resource/tool/patch regression: `48 passed`; runtime/workspace regression: `34 passed / 1 failed`;
- the single runtime failure (`test_service_waits_for_approval_when_policy_requires_apply_patch`) was reproduced on the unchanged M1 baseline `55e56a56` from a separate unregistered worktree, proving the failure is the legacy test's registered-project-root dependency rather than an M2 regression;
- `python -m compileall -q src/aipinho` and staged diff checks passed; production diff scan found no project/corpus-specific rule;
- newly enforced invariant: a dynamic local resource can replace only `workspace_not_registered`; it cannot relax a stronger static deny/readonly rule, and an undeclared permission is denied at the final gate;
- plan direction did not change; M2 clarified that the initial repair-mission discovery TaskRun freezes full mission resource/capability intent while executing only its readonly phase.

### M3 closure evidence - 2026-09-17

- validated implementation/main SHA: `3654d0e792f7fbe2c97aacd4f510f531c8e5b959`;
- prompt-declared repositories compile at semantic ingress into frozen `remote_repository` mission resources with provider, normalized identity, explicit branches, operation permissions and provenance;
- HTTPS and SSH forms of the same repository normalize to the same credential-free identity; embedded user/token material is detected and never retained as an authorized locator;
- remote authorization is scoped by repository + branch + operation, and multi-repository prompts associate branch/operation locally rather than cross-granting permissions;
- missing branch scope is fail-closed/needs-clarification; different repositories and wrong branches are denied;
- explicit negative repository constraints, global denied hosts/schemes, secret handling and destructive Git constraints remain stronger than prompt-derived allow;
- `git_push` scope requires repository identity reobservation immediately before later promotion execution;
- M3 deliberately does not enable Git/network execution or relax `git_write_shell`/network policy; actual governed execution remains M6;
- dedicated M3 suite: `11 passed`; MissionContract/M2/M3 regression: `31 passed`; semantic ingress regression: `15 passed`; TaskRuntime regression: `16 passed / 1 failed`;
- the single TaskRuntime failure is the same unregistered-worktree approval-test limitation documented during M2 and is outside the M3 code path;
- `compileall`, staged diff checks and production hardcode scans passed; no project/repository/host-specific production allowlist was introduced;
- plan direction did not change. M4 remains the explicit human-authority sprint.

### M4 closure evidence - 2026-09-17

- validated implementation/main SHA: `0fe414fb5196318e49eb660b5c5440b7dd135f11`;
- semantic ingress now separates requested capability from explicit human authorization and freezes only evidence-backed authority into the MissionContract;
- `Fa?a git push` and conditional mentions remain requests/mentions, while `Autorizo git push nesta miss?o` creates explicit authority evidence scoped to that source prompt;
- the existing SessionGrant path is now a compatibility facade over the canonical `AuthorityGrantService`; no second grant authority was introduced;
- mission grants bind mission id, source-message identity, source prompt hash, authority hash, capability/action, local resource/path and remote repository/branch scope;
- expiry, revocation and use-count are executable runtime behavior rather than decorative fields;
- `TaskRunGuard` and the final Agent Tool Gateway accept a valid mission grant only as satisfaction of the human-consent facet; static resource policy, profile policy and global denies remain independently authoritative;
- dedicated M4 suite: `11 passed`; grant/contract compatibility suite: `28 passed`; gate/resource/remote/semantic regression: `55 passed`; broader runtime/public regression: `100 passed / 2 failed`;
- both broader-suite failures were reproduced unchanged on M3 baseline `77685f0b`: the known unregistered-worktree approval fixture and the pre-existing persistent-chat Windows path parsing case;
- full `compileall`, diff checks and production hardcode scans passed; no project/repository-specific allowlist or Git/network policy relaxation was added;
- newly enforced invariant: requested capability is not human authority, and explicit authority cannot override stronger resource/global policy.

Next sprint: **M5 - Unified Capability and Policy Kernel**.


### M5 closure evidence - 2026-09-17

- validated implementation/main SHA: `75baa3551a1520ebc62ba985dbedbf3a1eae71f6`;
- checkpoint chain: M5-A `0f51c451`, M5-B.1 `0caea0ac`, M5-B.2 `1977d39c`, M5-C.1 `5c2101cf`, M5-C.2 `75baa355`;
- `CanonicalPolicyDecision` now composes capability demand, resource permission, human authority, runtime/global policy, profile/tool policy and execution-envelope facets;
- TaskRunGuard, Agent Tool Gateway, WriteCapabilityEnvelope and GovernedToolExecution now expose/consume the same canonical verdict instead of independently authorizing execution;
- explicit mission authority can satisfy only ASK facets for the same capability/resource; DENIED/INVALID/STALE/EXPIRED facets remain non-overridable;
- GovernedToolExecution accepts `task_run_id`, resolves the canonical TaskRun/MissionContract, honors dynamic workspace resources and uses the central workspace-role registry as legacy fallback;
- the duplicate governed-tool `allowed_workspace_roots` project allowlist was removed;
- generic `git_write_shell` and `network_shell` are fail-closed with explicit granular-classification reasons until M6; structured HTTP `web.request` remains governed through policy/approval;
- M5-C.1 focused suite: `9 passed`; C.1 regression: `26 passed`; M5-C.2 focused suite: `4 passed`; cross-gate C.2 suite: `8 passed`;
- final policy/authority/Gateway/envelope/executor regression: `55 passed`; TaskRuntime/resource regression: `55 passed / 1 failed`;
- the sole runtime failure is the previously established unregistered-worktree `test_service_waits_for_approval_when_policy_requires_apply_patch` baseline limitation;
- `compileall`, diff checks and production hardcode scans passed; project-specific governed-execution allowlist entries were removed rather than expanded;
- newly enforced invariant: specialized policies contribute facets/evidence, but only the canonical policy decision may authorize execution.

Next sprint: **M6 - Governed Git and Network Execution**.

### M6 closure evidence - 2026-09-17

- validated implementation/main SHA: `398f875e1485b878bf8bc7d242e53549c47c3659`;
- checkpoint chain: M6-A `79d3955a`, M6-B.1a `b23f61d6`, M6-B.1b `d8d49366`, M6-B.2a `3f4cac48`, M6-B.2b `ba2762ea`, controlled fixture `ca63daa9`, final compatibility validation `398f875e`;
- Git commands are classified into local read, network read, worktree write, commit, push, destructive and unknown demands; unknown/destructive operations remain fail-closed;
- GovernedToolExecution reobserves repository identity and current branch immediately before remote Git execution, composes remote scope + explicit human authority, executes with `shell=False`, and validates pushed local HEAD against the authorized remote branch HEAD;
- public ingress, TaskRunGuard and Agent Tool Gateway propagate the same granular Git capability, and the Gateway reclassifies argv/command instead of trusting caller-provided `shell_category`;
- Agent Tool Gateway delegates non-read Git execution to the canonical GovernedToolExecution path, so there is no parallel Git runtime or duplicated promotion authority;
- controlled real-Git fixture: `6 passed`, proving allowed fetch/commit/push and denied wrong-remote, wrong-branch and force-push paths;
- final Git/policy/authority/Gateway regression: `86 passed`; resource/public regression: `44 passed`; TaskRuntime/bootstrap: `21 passed / 1 failed`;
- the sole TaskRuntime failure is the established unregistered-worktree `test_service_waits_for_approval_when_policy_requires_apply_patch` baseline limitation;
- `compileall`, full M6 diff checks and production hardcode scan passed; no project/repository/host-specific production allowlist was introduced;
- generic `network_shell` remains fail-closed; structured HTTP `web.request` and classified Git network operations remain governed through canonical policy and mission scope.

Next sprint: **M7 - Mission Staging and Derived Resources**.

### M7 closure evidence - 2026-09-18

- validated implementation/main SHA: `725f47b789c6c356aa63b2126461d4c59c45fb4c`;
- checkpoint chain: M7-A `beffa0af`, M7-B.1 `0d0f764f`, M7-B.2 `7b2175f4`, M7-C implementation `725f47b7`;
- `mission_staging` is derived only from a frozen authorized `remote_repository` and a global safe staging root; prompt ingress cannot declare staging as a local resource;
- derived staging records source remote identity/branch, lifetime, provenance and explicit authority non-inheritance, and its mission id/path segments are hash-bounded;
- staging materialization reserves a canonical child TaskRun before side effects, creates the directory through GovernedToolExecution, and performs classified `git clone/fetch/pull --ff-only` through the same M6 Git authority path;
- origin identity, current branch and refreshed remote HEAD are reobserved before/after promotion-sensitive operations; branch drift and missing fetch/pull authority fail closed;
- WorkspaceContext exposes the derived staging resource without adding it to `workspace_registry.yaml`;
- controlled promotion proved arbitrary prompt-authorized remote -> staging clone/sync -> intentional change -> governed commit -> governed push while a separate `source_readonly` corpus and the static workspace registry remained hash-identical;
- terminal parent or staging child TaskRun adds a hard canonical lifecycle deny, so staging authority ceases when the mission ends while already-proven remote promotion truth remains unchanged;
- physical staging cleanup is intentionally not privileged around the global `delete_files` deny; retained staging is a cleanup limitation, not evidence that a validated push did not occur;
- validation: M7-A resource/contract regression `51 passed`; M7-B.1 `25 passed`; M7-B.2 `60 passed`; focused M7-C `8 passed`; final cross-sprint regression `107 passed`;
- `compileall`, diff checks and production hardcode scans passed; no project/repository/host-specific production allowlist was introduced.

Next sprint: **M8 - Mission Continuation Engine**.

### M8 closure evidence - 2026-09-18

- validated implementation/main SHA: `446d22349850`;
- checkpoint chain: M8-A `e56d8ca4`, M8-B.1 `9ca1ff68`, M8-B.2 `a960e6f6`, M8-C.1 `4b14e2f8`, M8-C.2 `446d2234`;
- terminal `end_to_end_governed` TaskRuns now invoke the canonical `TaskRunPlanner` to propose the next bounded phase from frozen structured mission semantics; the MissionContinuationService/Coordinator remain validators/orchestrators rather than a second planner;
- `MissionContract.semantic_context` freezes structured continuation semantics at ingress while downstream continuation never reparses `raw_prompt`; child contracts must preserve this semantic identity;
- planner output is descriptive only: phase/profile/operation/actions are validated against runtime profile/action catalogs, while canonical policy is recomputed independently and human authority is never accepted from candidate metadata;
- mission authority permissions and runtime capabilities are distinct: candidate `required_capabilities` bind frozen human authority while `runtime_capabilities_required` bind the canonical TaskRun/profile; a child phase may use a subset without erasing mission-wide authority needed by later phases;
- child resources remain monotonic, candidate actions cannot expand mission authority, and depth/phase-lineage/history guards prevent continuation cycles; `max_mission_continuation_depth` is configuration-driven;
- PhaseOutcome and PhaseSemanticDemandCompiler remain the evidence/demand boundary before child materialization; RuntimeTruth/dependency blocks still stop continuation;
- focused MissionContract/M8 suite: `38 passed`; cross-sprint M4-M8 regression: `134 passed`; broader runtime/public ingress regression: `65 passed / 1 failed`;
- the sole broader failure, `test_service_waits_for_approval_when_policy_requires_apply_patch`, reproduced identically on clean baseline `4b14e2f8` and remains the established unregistered-worktree fixture limitation;
- `compileall`, diff checks and production hardcode/`raw_prompt` scans passed; no project/repository/user-path-specific production rule or parallel runtime was introduced.

Next sprint: **M9 - Cross-Phase Truth and Mission Completion Contract**.


---

# Sprint M1 — Canonical Mission Contract

## Objective

Create one frozen representation of the mission so later phases do not reinterpret the original prompt to discover authority, resources or strategy.

## Required design

Introduce or consolidate canonical structures equivalent to:

- MissionContract;
- MissionExecutionStrategy;
- MissionResourceScope;
- MissionAuthorityBinding;
- MissionConstraint;
- MissionCompletionContract;
- MissionContractBinding.

The exact class names may differ if existing canonical schemas can be evolved cleanly.

## Minimum mission fields

- mission_id;
- session_id;
- source_message_id;
- source_prompt_hash;
- objective;
- execution strategy;
- local resource scopes;
- remote resource scopes;
- requested capabilities;
- authorized capabilities;
- negative constraints;
- validation requirements;
- completion requirements;
- authority hash/revision;
- provenance/evidence refs.

## Required behavior

Prompt interpretation occurs once at mission bootstrap.

All TaskRuns created for the mission bind to the frozen contract or a cryptographically/verifiably equivalent projection.

Child phases may narrow the contract but cannot add a workspace, repository, branch, capability or authority that the mission did not contain or derive through a governed resource-derivation rule.

## Definition of Done

- deterministic contract generation for equivalent input;
- stable hash/revision semantics;
- persisted and reloadable contract;
- child TaskRun binding;
- tests proving child authority cannot expand;
- tests proving prompt is not reparsed by downstream execution gates;
- no parallel mission authority introduced.

---

# Sprint M2 — Dynamic Local Resource Scopes

## Objective

Finish the prompt-derived local workspace model and make all local mutations consume the same scope contract.

## Required work

Generalize the existing workspace_scope_contract into the canonical local resource representation without losing compatibility during migration.

Close known gaps:

- add create_directory to canonical permission vocabulary;
- add create_directory to workspace-role operation rules;
- propagate dynamic scope through direct create_file and modify_file execution;
- implement governed create_directory in the canonical filesystem step path;
- unify apply_patch, file writes, build, test and shell path resolution;
- guarantee source_readonly denies mutation regardless of agent/tool policy;
- preserve protected/forbidden static overrides;
- repair WorkspaceContext rehydration from frozen TaskRun intent/mission data.

## Enforcement rule

Every local ToolInvocation must answer:

~~~text
target path
→ matching mission resource
→ role
→ required operation permission
→ human authority
→ global policy
→ execute / approval / deny
~~~

Checking only role == target_mutable is insufficient.

## Definition of Done

A previously unregistered temporary workspace declared by a prompt can be read and, when authorized, can create directories/files, modify files, apply patches, build and test.

A separate readonly resource declared in the same prompt remains immutable.

No project-specific workspace registration is required.

---

# Sprint M3 — Dynamic Remote Repository Scopes

## Objective

Make remote repositories first-class dynamic mission resources.

## Required work

Create a canonical remote-repository scope service/schema.

Parse positive and negative repository scope from prompt intent.

Represent at minimum:

- provider;
- normalized repository identity;
- allowed branches;
- clone/fetch/pull-fast-forward/commit/push permissions;
- destructive constraints;
- evidence/provenance.

Support explicit prompt constraints such as:

~~~text
use repository A
branch main
do not use repository B
do not initialize a repository in workspace X
~~~

## Security rules

Remote permission is scoped to repository + branch + operation.

Prompt scope cannot override global denied hosts, secret handling or network policy.

Remote identity must be observed again immediately before promotion operations.

## Definition of Done

Tests with unrelated temporary repositories prove:

- dynamic allow from prompt;
- negative remote constraint;
- equivalent URL normalization;
- different repository rejection;
- wrong branch rejection;
- no project-specific remote allowlist.

---

# Sprint M4 — Explicit Human Authority and Mission Grants

## Objective

Separate requested capability from explicit human authorization and make one prompt capable of authorizing a complete mission without redundant approval prompts.

## Direction

Evolve the existing SessionGrant mechanism instead of creating an unrelated second permission system.

A common authority abstraction may support:

- single-use approval;
- task grant;
- mission grant;
- session grant.

## Prompt-native authorization

An unambiguous clause such as:

~~~text
AUTORIZAÇÃO: autorizo nesta missão edição, build, testes, commit e push...
~~~

may create an already-effective mission authority binding because the user has granted consent in that source message.

A conditional or descriptive mention such as:

~~~text
if git push fails...
~~~

must not be treated as consent.

## Scope binding

Authority must be bound to:

- source_message_id and source_prompt_hash;
- mission_id;
- action/capability;
- local resource(s);
- remote repository/branch when applicable;
- optional command constraints;
- expiry/revocation/use constraints.

## Required cleanup

Make grant use-count, expiry and revocation real runtime behavior if those fields remain part of the contract.

## Definition of Done

Tests prove the semantic difference between:

~~~text
faça git push
~~~

and:

~~~text
autorizo git push nesta missão
~~~

Only explicit authorization can satisfy reusable human-authority requirements.

---

# Sprint M5 — Unified Capability and Policy Kernel

## Objective

Eliminate contradictory policy truth between TaskRuntime, Tool Gateway, shell policy, workspace roles and agent policy.

## Known pre-wave contradiction

The diagnostic branch showed Agent Tool Gateway paths that govern Git/network with approval while canonical TaskRuntime configuration still blocks git_commit/git_push and shell profile still forbids git_write_shell.

This sprint must remove that split-brain policy state.

## Canonical capability vocabulary

At minimum normalize concepts equivalent to:

~~~text
local.read
local.create_directory
local.create_file
local.modify_file
local.patch

shell.readonly
shell.test
shell.build
shell.runtime

network.http_read
network.download

git.local_read
git.network_read
git.worktree_write
git.commit
git.push
git.destructive
~~~

Names may follow existing conventions, but semantic distinctions must remain.

## Decision model

Specialized policies may contribute facets, but only one canonical decision may authorize execution.

Expected flow:

~~~text
Mission Contract
→ capability demand
→ resource permission
→ human authority
→ global safety/policy facets
→ canonical capability decision
→ execution adapter
~~~

## Definition of Done

For the same operation, TaskRunGuard, Tool Gateway, WriteCapabilityEnvelope and agent policy cannot return incompatible authority verdicts.

Diagnostics must expose which facet denied or constrained an operation.

---

# Sprint M6 — Governed Git and Network Execution

## Objective

Replace coarse Git classification with capability-aware governed Git/network execution.

## Git classification

Distinguish at least:

- local Git reads;
- network reads: clone/fetch/ls-remote;
- worktree-changing operations;
- commit;
- push;
- destructive history/worktree operations.

Commands such as the following must not fall into a generic safe git_write bucket:

~~~text
git reset --hard
git clean -f
git clean -fd
git push --force
git push -f
git branch -D
~~~

These remain fail-closed unless a separate future design explicitly governs them.

## Composed capability demands

Examples:

~~~text
git status
requires: git.local_read

git fetch
requires:
  git.network_read
  outbound network
  authorized remote repository

git push
requires:
  git.push
  outbound network
  authorized remote repository
  authorized branch
  explicit human authority
~~~

## Promotion validation

Before push:

1. observe actual origin;
2. normalize origin identity;
3. compare with remote resource contract;
4. observe current branch;
5. compare with branch scope;
6. reject force/rewrite operations;
7. execute governed push.

After push, success requires refreshed evidence that local HEAD equals the authorized remote branch HEAD.

## Definition of Done

Controlled repository fixtures prove allowed fetch/commit/push and denied wrong-remote, wrong-branch and destructive Git paths.

---

# Sprint M7 — Mission Staging and Derived Resources

## Objective

Allow an E2E mission to create a clean governed Git workspace without registering a project-specific directory in static config.

## Execution checkpoints

- **M7-A — Derived staging contract:** define the mission-scoped staging resource, safe-root policy, derivation provenance, lifetime and explicit authority non-inheritance. No directory creation or Git materialization occurs in this checkpoint.
- **M7-B — Governed staging materialization:** create the derived staging directory, clone/fetch the authorized remote, verify origin/branch, fast-forward only the authorized branch and expose the resulting staging resource through the canonical TaskRuntime gates.
- **M7-C — Promotion flow validation and closure:** prove arbitrary authorized repositories can use staging without permanent registration, validate source/corpus immutability and cleanup/truth semantics, run regression, merge and close the sprint.

Each checkpoint must remain inside the existing MissionContract → canonical policy → GovernedToolExecution authority chain. No staging-specific planner, bypass runtime or parallel Git authority is permitted.

## Resource derivation

An authorized remote_repository may derive a mission_staging local resource under a globally configured safe staging root.

The runtime must record:

- derived resource id;
- source remote resource id;
- path;
- lifetime;
- authority inherited;
- authority explicitly not inherited;
- creation evidence.

## Intended promotion flow

~~~text
authorized remote
-> create mission staging directory
-> clone/fetch
-> verify origin
-> fast-forward authorized branch
-> synchronize only intentional changes
-> validate
-> commit
-> push
~~~

## Constraints

The original source/corpus remains untouched unless separately mutable.

Staging authority is mission-scoped and disappears as an active authority when the mission ends.

Cleanup is not allowed to rewrite final truth. A cleanup limitation after a proven push is a limitation, not evidence that the push did not occur.

## Definition of Done

A mission can materialize and use a clean staging clone for an arbitrary prompt-authorized repository without permanent workspace registration.

## Closure result

M7 is validated and CLOSED. The canonical path is MissionContract -> derived `mission_staging` -> child TaskRun -> canonical policy -> GovernedToolExecution. No staging-specific planner or Git runtime was introduced. Mission-terminal lifecycle removes active staging authority; physical deletion remains governed separately and cannot rewrite promotion truth.

---

# Sprint M8 — Mission Continuation Engine

## Objective

Make end_to_end_governed operational rather than merely descriptive.

## Execution checkpoints

- **M8-A — Continuation decision contract:** define planner-supplied next-phase candidates and a pure continuation decision that composes frozen MissionContract, canonical lifecycle and PhaseOutcome/dependency truth. No child TaskRun is created in this checkpoint.
- **M8-B — Canonical child TaskRun continuation:** reserve and enrich the next TaskRun only after an M8-A continuation decision, rebind the dependency evaluation to the real child identity, preserve monotonic mission authority/resources and invoke only the existing TaskRuntime planner/executor.
- **M8-C — Automatic continuation E2E and closure:** wire terminal phase completion to the continuation coordinator for end_to_end_governed missions, prove staged/single-operation stopping boundaries, run cross-sprint regression, merge and close M8.

The continuation service may validate a planner-supplied phase candidate but may never invent a phase sequence, reparse the original prompt, grant authority, or become a second planner/runtime/truth authority.

## Service responsibility

Introduce or evolve a thin MissionContinuationService / MissionPhaseCoordinator.

It may coordinate TaskRuns but must not become another:

- semantic router;
- planner;
- policy authority;
- execution runtime;
- validation engine;
- truth authority.

## Inputs

- frozen MissionContract;
- previous TaskRun;
- RuntimeTruth;
- SemanticTruth/PhaseOutcome;
- mission checkpoints;
- outstanding completion requirements.

## Decisions

Exactly one of:

~~~text
continue_to_next_phase
await_existing_authority
request_new_authority
block
complete
~~~

## Strategy semantics

For end_to_end_governed:

- continue automatically while next phase is inside existing authority and evidence gates;
- stop only at a real authority/safety/evidence boundary.

For staged:

- stop at the requested phase boundary even if future authority exists.

For single_operation:

- do not invent a multi-phase mission.

## Expected generic phase sequence

A repair/promote mission may become:

~~~text
Discovery
-> Patch Planning
-> Mutation
-> Build/Test/Smoke
-> Promotion Staging
-> Git Promotion
-> Final Validation
~~~

These are runtime phases, not FireTest scripts.

## Definition of Done

A discovery TaskRun can terminalize and cause the next canonical TaskRun to be created without a new prompt when strategy and authority allow it.

No phase can self-promote around RuntimeTruth.

## Closure result

M8 is validated and CLOSED. The canonical path is terminal TaskRun -> frozen MissionContract/semantic context -> canonical TaskRunPlanner continuation proposal -> deterministic catalog/authority/dependency gates -> MissionPhaseCoordinator -> canonical child TaskRun -> existing TaskRuntime planner/executor. The candidate cannot grant policy or authority, raw prompt text is not reparsed, mission-wide authority is preserved or narrowed but never expanded, and loop/depth boundaries fail closed.

---

# Sprint M9 — Cross-Phase Truth and Mission Completion Contract

## Objective

Make final mission success depend on evidence-bound completion requirements rather than on the last command returning zero.

## Execution checkpoints

- **M9-A — Mission-wide completion facet and rehydratable evidence projection.**
  - **M9-A.1 — Durable mission lineage query:** extend the canonical TaskRunStore index/query surface with mission identity and rebuild the ordered set of TaskRuns/PhaseOutcomes after restart without hydrating unrelated runtime payloads.
  - **M9-A.2 — Strict mission completion snapshot:** project the frozen mission completion contract across observed child revisions using monotonic union of completion/validation requirements and the most restrictive limited-completion policy; bind the projection to mission/run/outcome authority refs.
  - **M9-A.3 — Pure completion facet resolver:** introduce a deterministic mission-completion facet consumed later by RuntimeTruth. It accepts explicit requirement evaluations, never invents requirement semantics, and preserves missing/partial/blocked states with stable authority hashing.
- **M9-B — Requirement-to-evidence binding:** compile semantic requirement/evidence bindings only from the frozen structured MissionContract context and observed PhaseOutcomes. Model reasoning may propose semantic matches but cannot fabricate evidence, authority, policy or satisfaction; deterministic gates validate every referenced run/outcome/evidence item.
  - **M9-B.1 — Canonical evidence catalog:** project every mission evidence ref with its producer TaskRun, PhaseOutcome authority hash, RuntimeTruth/use-safety state, limitations and bounded artifact descriptors; no raw artifact payload is copied into the catalog.
  - **M9-B.2 — Contract-bound semantic binding proposal:** use the existing read-only ContractBoundSemanticReasoner over frozen semantic context + exact completion requirements + canonical evidence catalog. Output is candidate-only and may reference only catalog IDs.
  - **M9-B.3 — Deterministic binding compiler:** validate candidate requirement names, producer/outcome/evidence identities and canonical truth safety, then derive MissionCompletionRequirementEvaluation statuses without accepting model-declared truth or fabricated refs.
- **M9-C — RuntimeTruth/SpeakerTruth ceiling, restart E2E and closure:** compose the M9 facet into the existing RuntimeTruthEngine and CanonicalSpeakerTruthService, prove equivalent mission truth after process restart/rehydration, run cross-sprint regressions, merge and close M9.

M9 must not introduce a second RuntimeTruth, SpeakerTruth, planner or lifecycle authority. Mission completion is a deterministic facet consumed by the existing truth chain.

### M9-B checkpoint evidence - 2026-09-18

- B.1 canonical evidence catalog checkpoint: `483079bdd56a`; mission evidence refs are projected with producer TaskRun, PhaseOutcome authority, RuntimeTruth/use-safety state, limitations and bounded artifact descriptors without copying raw artifact payloads.
- B.2 semantic proposal checkpoint: `84df6a4805dd`; the existing ContractBoundSemanticReasoner receives only frozen semantic context, exact requirements and the canonical evidence catalog. Proposal rows carry semantic relation/confidence/rationale only and cannot inject a truth status.
- B.3 deterministic compiler derives requirement evaluations only after validating exact requirement vocabulary, evidence refs, producer bindings, policy limits and canonical truth safety. A model `supports` relation alone cannot promote unsafe evidence.
- B regression: M9 A+B plus M8 continuation and existing RuntimeTruth focused suites `93/93`; compile/diff/hardcode scans are required before the B.3 checkpoint is accepted.
- Restart note for M9-C: semantic binding proposals are model-assisted interpretations, not reconstructible truth authority. C must persist/rehydrate the accepted proposal or equivalent bounded interpretation and deterministically recompile it against current canonical evidence rather than silently re-invoking the model to reconstruct final truth.

### M9-C closure evidence - 2026-09-18

- C.1 persisted mission binding interpretation checkpoint: `9e780992705c`; accepted semantic binding proposals are persisted only after deterministic compilation and are rehydrated after restart without model reinvocation. Focused M9 completion suite: `29/29`.
- C.2 RuntimeTruth/SpeakerTruth ceiling checkpoint: `6b2f4a506180`; mission completion is an optional deterministic facet consumed by the existing RuntimeTruthEngine, CanonicalOperationState and canonical result publisher. Intermediate or blocked continuation cannot publish final mission success. Focused M8/M9/truth/publisher regression: `76/76`.
- C.3 restart-equivalence checkpoint: `19beb80d866018c5b0ee26547e2577c2ce775992`; a real terminal mission persists its accepted semantic proposal, then a fresh TaskRunStore/runtime reproduces the exact RuntimeTruth model dump without invoking the semantic reasoner or emitting a second completion event.
- Cross-sprint M4-M9 regression: `172/172`.
- Broader runtime/public regression: `69 passed / 1 failed`; the sole failure is the established `test_service_waits_for_approval_when_policy_requires_apply_patch` unregistered-worktree fixture already documented before M9, with no new M9 failure.
- Final focused restart/ceiling regression: `9/9`; `compileall`, `git diff --check` and production hardcode/`raw_prompt` scans passed.
- No second RuntimeTruth, SpeakerTruth, planner, dispatcher or execution runtime was introduced.

## Closure result

M9 is validated and CLOSED. Mission completion requirements are projected across durable mission TaskRuns and PhaseOutcomes, semantically bound only as non-authoritative candidates, deterministically compiled against canonical evidence, and consumed as a ceiling by the existing RuntimeTruth/SpeakerTruth chain. A local phase or command reporting `completed` cannot elevate mission truth above missing, blocked or limited mission evidence. Accepted model-assisted binding interpretation is persisted and recompiled after restart rather than regenerated, so restart reproduces the same final truth without granting the model authority.

## Completion contract

The mission may require outcomes such as:

- concrete code change;
- regression validation;
- relevant behavior validation;
- corpus integrity;
- build/test success;
- clean staging validation;
- commit;
- push;
- local/remote HEAD equality.

Requirements are derived from the prompt and frozen in the mission contract.

## Evidence binding

Each requirement must bind to evidence produced by one or more TaskRuns.

Example:

~~~text
code_change
-> patch/diff evidence

regression_validation
-> test result evidence

behavior_validation
-> smoke/runtime evidence

git_push
-> governed command evidence + remote observation

head_remote_equality
-> local SHA + refreshed remote SHA
~~~

## Final truth

Mission success is reportable only if all required outcomes are satisfied or the completion contract explicitly permits a limited completion state.

Partial evidence stays partial.

Blocked promotion stays blocked.

A local commit without proven push is not remote completion.

## Definition of Done

Cross-phase evidence can be rehydrated after restart and produces the same final RuntimeTruth.

SpeakerTruth cannot claim completion above the mission truth ceiling.

---

# Sprint M10 — Fresh Manual E2E FireTest and Consolidation

## Objective

Validate the completed architecture through the normal AIpinho interface with a fresh human prompt.

## M10-A preflight bugfixes discovered by the fresh manual E2E

- **M10-A.1 — Contract-bound semantic demand payload:** downstream semantic reasoning must consume frozen structured mission semantics, canonical plan fields, resource/authority descriptors and hashes only. Raw prompt text and free-form semantic-goal text must not be re-sent downstream.
- **M10-A.2 — Resource-scoped negative semantics:** a write prohibition tied to a concrete readonly resource must constrain that resource without becoming a global `workspace_mutation` prohibition for the mission. Windows drive syntax must not be split at the drive colon during clause normalization.
- **M10-A.3 — Governed semantic-output robustness:** when canonical model evaluation explicitly requests retry for a retryable output-contract failure, ContractBoundSemanticReasoner may perform only the bounded retry count granted by evaluation policy. Llama CLI role echo must be sanitized before JSON validation; invalid/non-retryable output remains fail-closed.
- **M10-A.4 — Phase-local dependency safety demand:** dependency use-safety invariants must be derived from the downstream consumer step/operation, not from mission-global planning or mutation intent. A read-only consumer inside a mission that will mutate later must not require destructive-action safety; a consumer with an actual side effect must still require it.
- **M10-A.5 — Registered role-bound continuation inference:** continuation proposals must route through an existing canonical role binding; invented role identifiers are not valid runtime dependencies. Model unavailability remains fail-closed.
- **M10-A.6 — Governed role budget and model fallback:** contract-bound semantic inference must honor the selected role's canonical timeout/output budget and may use only the fallback model declared by the role binding when the configured fallback policy permits it. Primary/fallback share the same JSON contract and safety envelope; rejected evaluation remains rejected.
- **M10-A.7 — Explicit continuation contract vocabulary:** every contract identifier required from the semantic candidate must be supplied in the governed continuation vocabulary before deterministic validation.
- **M10-A.8 — Bounded deterministic candidate correction:** a candidate rejected by the deterministic continuation gate may receive at most the configured bounded correction attempt. The rejection reason is evidence for a new proposal, never permission to relax the gate; the replacement candidate is revalidated from zero.
- **M10-A.9 — Flattened continuation option catalog:** profile/operation/action compatibility is projected into deterministic continuation options before semantic selection so the model never has to invent cross-product compatibility between independent catalogs.
- **M10-A.10 — Compact runtime-owned continuation materialization:** the semantic proposal selects only a governed option id, contract type and allowed action subset. Runtime profile, operation type and fresh phase identity are materialized deterministically by TaskRunPlanner. Redundant raw profile/action catalogs are removed from the model payload so correction retries remain below inference input limits.
- **M10-A.11 — Semantic continuation selector:** choosing among already-governed continuation options is semantic interpretation/routing, not free-form planning authority. The proposal therefore uses the canonical `semantic_interpreter` role; TaskRunPlanner remains the deterministic authority that materializes and validates the next work unit.
- **M10-A.12 — Non-fatal file-context omissions:** text-read ineligibility and explicit inventory-only handoff are configurable omission classes, not security violations. They remain visible in omitted-file summaries, warnings and limitation evidence, but must not fail a required context phase when useful text context was safely collected. Secret/protected/traversal/symlink/explicitly blocked-extension violations remain fatal. A partial context producer is admitted downstream only as `ADMITTED_WITH_CONSTRAINTS`.
- **M10-A.13 — Action-scoped semantic dependency mode:** whether a dependency requires LLM semantic interpretation is declared by the canonical action registry, not inferred from mission-global `knowledge_output` and not hardcoded from phase names. Structural actions may be explicitly `deterministic`; actions not explicitly declared remain `interpreted` by default and therefore fail closed through the semantic interpreter.
- **M10-A.14 — Structured semantic resolution contract:** semantic-demand interpretation no longer uses model self-reported numeric confidence as an authorization gate. Candidates must explicitly return `resolution_status=resolved|unresolved`; unresolved candidates require one or more governed reason codes and remain fail-closed. A resolved empty requirement set is valid when the model can determine that no additional upstream semantic guarantee is required. All governed vocabulary, use-safety, semantic-property and constraint validation remains deterministic.
- **M10-A.15 — Canonical phase identity and evidence-bound runtime truth:** structured phase aliases are normalized once through `PhaseIdentityService`, with materialized `TaskRun.current_phase` taking precedence for downstream consumers. PhaseOutcome, continuation, planning, timeline and workspace context no longer maintain divergent phase-resolution rules. Workspace validation distinguishes structured operational path evidence from declarative text, so merely describing a forbidden root cannot fabricate `forbidden_root_access` while an actual operational target still blocks. TaskRun reason codes are stable identifiers rather than arbitrary blocked paths. Public fix responses project persisted continuation state instead of hardcoding a next phase, and a non-executable task lifecycle preview cannot report safe completion merely because its expected-output set is empty.
- **M10-A.16 — Consumer-owned continuation semantics and stable limitation binding:** downstream dependency requirements for a continuation candidate are now compiled from an ephemeral, non-executable semantic projection of the validated consumer action set instead of reusing the producer TaskRun plan with only the operation name changed. The projection reuses the canonical ActionRegistry, ExecutionPlanPromotionService, TaskSemanticVocabularyCompilerService and PhaseSemanticDemandCompiler, carries its own source plan/execution/hash bindings, and preserves the producer plan only as provenance. Limitation compatibility no longer asks the model to repeat arbitrary limitation text: deterministic short opaque IDs bind descriptions to model assessments, the output contract enumerates the only valid IDs and impacts, and unknown, duplicate or incomplete bindings remain fail-closed. `patch_preview` remains explicitly `interpreted`; no deterministic bypass was introduced.
- These are generic runtime corrections discovered by the FireTest. No FireTest workspace, repository, media extension or project name may appear in production policy or branch logic.
- After A.1-A.16 are checkpointed, merged and the canonical backend is restarted, repeat the same human prompt through the normal interface; do not manufacture continuation or inject TaskRuns.

### M10-A validation evidence

- Focused current continuation/reasoner/dependency regression: `61/61`.
- Cross-sprint M4-M9 plus M10-A regression: `238/238`.
- Broader runtime/public regression: `71 passed / 1 failed`; the sole failure is the previously documented `test_service_waits_for_approval_when_policy_requires_apply_patch` unregistered-worktree approval fixture, with no new M10-A failure.
- Real in-memory replay of the blocked FireTest run leaves the persisted run untouched and now returns `MISSION_CONTINUATION_CANDIDATE_PLANNED`.
- The real continuation selection uses `qwen3_1_7b_q6_k`, returns `evaluation_status=accepted`, confidence `0.9`, zero candidate retries, and deterministically materializes `phase_001_patch / patch_preview / patch_request`.
- The compact continuation payload is approximately 10.6k characters for the observed real mission, below the 20k semantic-inference ceiling.
- M10-A.12 focused file-selection/context/workflow regression: `18/18`.
- Real workspace replay: 76 discovered candidates, 40 safely included, 36 omitted (2 text-read-ineligible and 34 max-files budget), `bundle.status=partial`, zero violations, 88,153 bytes read; the downstream project-analysis phase is `ADMITTED_WITH_CONSTRAINTS`.
- Expanded analysis/workflow/M8/M9 regression: `194 passed / 2 timing-sensitive failures`; the two 1 ms timeout tests passed `2/2` immediately when rerun in isolation with no code change, confirming timing flakiness rather than an A.12 regression.
- Runtime/publisher regression: `21 passed / 1 failed`; the sole failure is the previously documented unregistered-worktree approval fixture `test_service_waits_for_approval_when_policy_requires_apply_patch`, with no new A.12 failure.
- M10-A.13/A.14 focused action-registry/phase-demand/hybrid-semantic regression: `31/31`.
- Real latest-FireTest replay: `project_tree` and `project_context` compile deterministically with semantic interpretation `not_required`; `project_analysis`, `project_report`, `role_pipeline_run` and the fail-closed unregistered `compose_result` path compile through the real `qwen3_1_7b_q6_k` semantic interpreter as `resolution_status=resolved`.
- Sequential in-memory workflow replay of `task_run_1c335e92cf694a8baeaea3633db77567` leaves persistent state untouched and admits `phase_003_build_project_tree` as `ADMITTED`, `phase_004_build_file_context` as `ADMITTED`, and `phase_005_run_project_analysis` as `ADMITTED_WITH_CONSTRAINTS` over the safe partial context established by A.12.
- Broad A.12-A.14/M8/M9/runtime/publisher regression after the structured-resolution change: `229 passed / 1 failed` in 202.04 s. The sole failure is the already documented unregistered-worktree approval fixture `test_service_waits_for_approval_when_policy_requires_apply_patch`; no new A.13/A.14 regression was observed.
- M10-A.15 canonical phase/result/access regressions: `25/25`; lifecycle completion/speaker ceiling: `21/21`; public intent plus M9 RuntimeTruth: `33/33`; M8 continuation planner/decision: `18/18` including the full TaskRuntime terminal continuation path; M8 coordinator: `11/11`.
- The standalone validation-gate E2E is now green: `1/1` test covering all `24/24` internal cases. Its harness imports the canonical runtime fixture directly, derives forbidden-root evidence from the configured validation policy, and evaluates real-inference behavior against the active role-pipeline policy instead of stale project-specific assumptions. Focused workspace-access regressions independently prove that declarative forbidden-root text is non-blocking while a structured operational event path remains blocking.
- M10-A.16 implementation commit: `d1f4963b` (`fix(runtime): bind continuation semantics to consumer`). Focused action-registry/semantic-binding/continuation regression: `27/27`; broader dependency/semantic-gate/M8/A.15 regression: `68/68`. Both suites were executed with `PYTHONPATH` explicitly bound to the A.16 worktree after detecting that the machine-wide editable install still pointed at the canonical A.15 tree.
- Read-only replay against the persisted manual-E2E outcome confirms that the previous `LIMITATION_COMPATIBILITY_BINDING_INVALID` frontier is removed from the new binding contract: the three upstream limitations are exposed through deterministic IDs (`lim_<sha-prefix>`) and the model contract enumerates exactly those IDs. The observed next fail-closed frontier is `SEMANTIC_REASONER_EVALUATION_NOT_ACCEPTED` after governed retry reports malformed/truncated JSON; this is separate from limitation identity binding and is the diagnostic entry point for M10-A.17.
- M10-A.17 root-cause replay showed that `requirement_provenance` alone occupied 5,581 of 6,775 serialized downstream-requirement characters; the resulting semantic prompt reached 9,067 chars despite the `semantic_interpreter` low-role budget of 6,000 chars. llama.cpp then reported `request (3131 tokens) exceeds the available context size (3072 tokens)`, while the old retry expanded the prompt further to 9,338 chars and produced truncated JSON.
- M10-A.17 keeps provenance/hashes/timestamps in deterministic authority but projects only the bounded semantic requirement view to the model; `ContractBoundSemanticReasoner` now fails closed on an exceeded role budget, llama.cpp context sizing uses configurable conservative token estimation plus safety margin, context-window overflow is explicit provider evidence, overflow retry expands context without increasing the prompt, and nested `json_shape` validation is carried through the canonical OutputContract -> OutputContractValidator -> JSONOutputValidator -> RetryPolicy chain rather than a parallel reasoner validator.
- Real read-only A.17 replay reduces the same semantic prompt from 9,067 to 2,758 chars, stays inside the low-role budget, runs with `ctx_size=2048`, and avoids context overflow. The first structurally valid response omitted the three per-assessment rationales; canonical evaluation reported `missing_required_field:assessments[0..2].rationale`, one governed retry grew only to 3,227 chars, and the second response was accepted. `LimitationCompatibilityResolverService` returned `accepted` with all three limitations compatible.
- A read-only continuation decision over the persisted PhaseOutcome now returns `continue_to_next_phase`, `mission_continuation_existing_authority_and_evidence_allow`, no authority gap, and dependency decision `ADMITTED_WITH_CONSTRAINTS` for the existing `phase_001_patch` candidate. No child TaskRun was materialized by this diagnostic replay.
- M10-A.17 validation: focused semantic/provider/evaluator suite `64/64`; final cross A.15/A.16/A.17 + M8/dependency regression `106/106`; cross-caller OutputSchema compatibility `32/32`; role-budget enforcement `8/8`; `compileall`, `git diff --check`, and production/config hardcode scan are clean.
- M10-A.17 implementation/main SHA: `0a803b6d6b36c95065d11b2b70f96992439e089e` (`fix(runtime): harden governed semantic inference`). Promotion was fast-forward only. The dirty canonical workspace had zero incoming-path overlap; hashes for the pre-existing modified `config/skills/registry/skills_index.json` and `reports/cvl/dependency_graph.md` remained byte-identical and all 153 pre-existing untracked files remained present after synchronization.
- The first post-A.17 backend restart record (`backend_restart_1789955928500`) was later disproven as an effective restart. Its persisted supervisor trace shows stop returned `0` with `Recorded process no longer exists.` from a stale PID file, start returned `0` with `AIpinho API already listening on port 9088 (PID 13788).`, and post-health remained healthy. Process creation time confirmed PID 13788 predated the requested restart, so healthy-to-healthy was a false restart claim. The subsequent manual FireTest therefore executed pre-A.16/A.17 loaded code and its `LIMITATION_COMPATIBILITY_BINDING_INVALID` result is not valid post-A.17 regression evidence.
- **M10-A.18 — restart truth:** implementation commits `a266b732` (`fix(supervisor): verify backend restart transition`) and `5833fccd` (`fix(supervisor): detach restart script capture`). `stop_aipinho_9088.ps1` now validates that a recorded PID is still the active listener, removes stale PID metadata and falls back to the real listener, verifies identity, stops it and waits for the port to cease listening. `BackendControlService` now requires `stop_health=down` before invoking start and fails rather than accepting a healthy-to-healthy no-op. Canonical script output is captured through temporary files instead of subprocess pipes, preventing a spawned uvicorn descendant from keeping the restart controller blocked after PowerShell exits.
- M10-A.18 validation: backend-control unit regression `4/4`, supervisor/launcher focused regression `10/10`, backend-control unit+API integration `8/8`, PowerShell parser clean, `compileall`, `git diff --check`, and production hardcode scan clean. Canonical dirty tracked files retained their pre-sync hashes and all 153 pre-existing untracked files remained present during both A.18 promotions.
- Real restart proof after A.18: restart `backend_restart_1789957290698` returned `accepted` with no warnings in 13.21 s; trace records `pre_health=healthy`, successful stop of PID 24636 with port 9088 closed, `stop_health=down`, successful start of PID 21432, and `post_health=healthy`. PID file contains `21432`, `/api/v1/health=ok`, `/api/v1/runtime/health=ok`, backend-control status is online/healthy, and canonical Git was `HEAD == origin/main == 5833fccdbff9100a50076b6b0ade810b3855fe80` at restart verification.
- Read-only replay of the latest persisted manual mission on the truly restarted code no longer reaches the old limitation-binding frontier; it fails earlier and explicitly at `SEMANTIC_REASONER_ROLE_BUDGET_EXCEEDED` during continuation selection. Captured planner input is 11,237 serialized chars: `continuation_options` alone is 7,367 chars, while the `semantic_interpreter` low-role prompt budget is 6,000. This is a separate bounded-payload problem and the next M10 diagnostic frontier; no child TaskRun was materialized by the replay.
- **M10-A.19 — bounded semantic continuation reasoning:** implementation/main SHA `57833beb7e54862956b67e91c0927c0f04d8f91f` (`fix(runtime): bound semantic continuation reasoning`). Semantic demand now separates deterministic authority/provenance from the bounded model view, continuation selection projects only relevant authorized options, non-empty output constraints have a dedicated evaluator/retry reason, and interpreted actions may declare the use-safety dimensions actually applicable to the consumer through ActionRegistry instead of exposing the entire system vocabulary. Real replay of `project_analysis` compiles through `qwen3_1_7b_q6_k` with only `safe_for_downstream_static_analysis=[true]`; the earlier role-budget and malformed-rationale frontiers are absent. Validation: focused suites `69/69`, `75/75` and `20/20`; expanded continuation/dependency/evaluator regression `130/130`; `compileall`, diff and production hardcode scans clean. Verified restart `backend_restart_1789982393071` records `healthy -> down -> healthy`, PID `21432 -> 23916`, and no warnings.
- **M10-A.20 — requested capability / explicit authority / resource-envelope separation:** implementation SHA `93b2cf13` (`fix(runtime): separate request authority from resource scope`). Semantic ingress no longer converts every permission available on a mutable/local or remote resource into a human-requested capability. Capability markers were narrowed to positive action/object semantics so negative mentions such as transient artifacts or a corpus that is not a write workspace do not fabricate `artifact_create`/write demand; explicit `criacao/alteracao de testes` resolves to `create_file`, and diagnostic/preflight authority resolves to governed `shell_readonly` when that capability exists in the resource envelope. Remote scope parsing now recognizes clean Git-copy, `fetch`, and safe fast-forward wording as `git_clone`, `git_fetch`, and `git_pull_ff` resource/request semantics without converting those requested operations into human authority.
- M10-A.20 validation: focused ingress/authority/remote regression `45/45`; MissionContract/grant/staging/continuation regression `76/76`; final A.20 authority/staging focused set `72/72`; exact read-only replay of the persisted manual mission now removes the false gaps `artifact_create`, `copy_from`, and `create_directory`, while `create_file` and `shell_readonly` are correctly covered by explicit human evidence. The remaining future-side-effect authority gap is exactly `git_clone`, `git_fetch`, and `git_pull_ff`. Those operations are genuinely requested and in remote resource scope but are not named by the explicit human authorization clause, so they remain fail-closed rather than being inferred from commit/push authority. `read_workspace` remains a phase-level read capability injected by the discovery TaskRun and does not require the human-authority facet under current read policy.

## Test restrictions

Do not:

- drive phases with FireTest scripts;
- inject internal TaskRuns to manufacture progress;
- hardcode Pinhoabacaxi workspace names;
- hardcode repository names;
- pre-register a project only to make the test pass;
- bypass canonical approval/authority;
- declare PASS from compilation alone.

## Required observations

The fresh mission must demonstrate:

1. correct strategy selection;
2. correct local mutable/readonly resource scopes;
3. correct remote repository/branch scope;
4. preserved explicit human authority;
5. real discovery;
6. real patch planning;
7. real mutation;
8. real tests/build and relevant smoke evidence when feasible;
9. readonly corpus integrity;
10. dynamic mission staging;
11. observed origin/branch validation;
12. governed commit/push;
13. refreshed remote SHA equality;
14. final mission truth consistent with all required outcomes.

## Failure semantics

Any real boundary failure must produce a specific reason_code and preserved evidence.

No failure may be hidden by a later phase.

No incomplete remote promotion may be called complete.

## Definition of Done

The same architecture must also be demonstrable with an unrelated workspace/repository fixture by changing only prompt-provided resources.

The final validation must show no project-specific production configuration was introduced.

---

## 9. Sprint closure protocol

Every sprint closure MUST update both current-state documents:

1. **CURRENT_STATE.md**
2. **AIpinho_context_pack/docs/context/current_state.json**

This is part of the sprint Definition of Done, not optional documentation cleanup.

Each closure update must record at minimum:

- sprint identifier and name;
- final status;
- merge/main SHA;
- validation summary;
- architecture boundary closed;
- remaining limitations or open frontier;
- next sprint;
- any newly introduced invariant;
- whether this plan changed.

The status board in this document must also be updated when a sprint changes state.

Allowed sprint states:

~~~text
PLANNED
IN_PROGRESS
BLOCKED
IMPLEMENTED_UNVALIDATED
VALIDATED
MERGED
CLOSED
~~~

A sprint should normally move to CLOSED only after validated work is merged to main and both current-state files reflect the new state.

---

## 10. Per-sprint engineering lifecycle

Unless a task explicitly requires another governed route, each sprint follows repository policy:

~~~text
sync main
-> create sprint branch/worktree
-> diagnose exact current boundary
-> implement minimal coherent change
-> focused tests
-> regression tests appropriate to scope
-> runtime/doctor checks when relevant
-> inspect diff
-> push branch
-> merge validated work into main
-> push main
-> sync local main
-> confirm tracked local main == tracked origin/main
-> update current state and this status board
~~~

Do not develop directly on main.

Do not use destructive cleanup to reconcile the local overlay.

Do not commit generated local evidence, caches, secrets or unrelated dirty files.

---

## 11. Validation philosophy

Every sprint needs three proof levels where applicable:

### Contract proof

Schemas, hashes, immutable bindings and deterministic decisions behave as specified.

### Enforcement proof

The last gate before execution actually rejects authority/resource violations; safety must not rely only on the planner choosing not to request them.

### E2E proof

The public/runtime path exercises the contract under realistic TaskRun execution.

Unit tests alone do not prove E2E authority propagation.

A successful E2E test does not excuse missing unit-level denial tests.

---

## 12. Regression requirements for the whole wave

At minimum retain coverage for these failure classes:

- "subdirectory" language does not become directory creation;
- compound repair mission starts discovery-first;
- source_readonly remains immutable;
- target_mutable can be dynamic and unregistered;
- create_directory is explicitly governed;
- missing declared permission is denied at final tool gate;
- missing human authority is denied or requires authority;
- protected/forbidden global roots override prompt grants;
- wrong remote repository is denied;
- wrong branch is denied;
- remote normalization does not broaden identity;
- Git push requires network + remote + branch + authority;
- destructive Git is denied;
- child TaskRun cannot expand mission scope;
- restart/rehydration preserves mission contract;
- partial phase evidence is not converted into failure solely because it is partial;
- partial evidence cannot become success without compatible completion truth;
- final SpeakerTruth respects RuntimeTruth.

---

## 13. Known pre-wave evidence to preserve

The diagnostic branch snapshot cfba76ee established several useful facts that future sprints should preserve or re-prove after refactoring:

- compound repair intent is routed to discovery-first;
- the "subdirectory" false create-directory classification is covered by regression;
- end_to_end_governed strategy is derived from prompt intent;
- dynamic workspace scopes can distinguish mutable target and readonly corpus;
- prompt-derived workspace scope can replace project-specific allowlists;
- protected/readonly static policy still overrides prompt mutation;
- patch planning paths already consume workspace scope in several layers;
- partial workflow phases can remain partial with limitations;
- agent Git/network policy has experimental governed paths;
- the current focused diagnostic regression produced 57 passed and one known pre-existing workflow dependency failure.

These are evidence checkpoints, not guarantees that main already contains the implementation.

---

## 14. Known pre-wave gaps to close

The following findings motivated this wave and should be explicitly retired by sprint evidence:

- no actual discovery -> next TaskRun mission coordinator;
- no canonical remote_repository mission resource;
- no mission-scoped authority consumed by final execution gates;
- SessionGrant not integrated into TaskRuntime/Tool Gateway authority;
- grant use-count semantics incomplete;
- create_directory absent from canonical workspace permission vocabulary;
- direct filesystem step missing scope propagation;
- no canonical explicit create-directory path in GovernedTaskStepRunner;
- Tool Gateway resource role check not sufficient to enforce declared permission;
- approval matching broader than exact operation authority;
- coarse git_write_shell classification;
- destructive Git can be hidden inside generic Git classification;
- Git network operations do not demand composed Git + network + remote capabilities;
- TaskRuntime and Agent Tool Gateway disagree about Git write authority;
- no prompt-derived remote/branch enforcement before push;
- no mission-created staging-resource model;
- WorkspaceContext fallback rehydration can lose frozen scope;
- final mission completion is not yet one cross-phase evidence contract.

---

## 15. Design decisions that require special care

### 15.1 Do not auto-approve every imperative

"Faça X" expresses desired operation.

"Autorizo X nesta missão" expresses explicit authority.

The semantic model must preserve both.

### 15.2 Do not turn repository scope into general network scope

A prompt-authorized GitHub repository authorizes only the operations granted for that resource. It does not allow arbitrary HTTP access to github.com or the internet.

### 15.3 Do not hardcode FireTest resources

Pinhoabacaxi workspaces, music corpora and repository names may appear in tests only as realistic fixtures where appropriate, never as production policy.

### 15.4 Do not create Runtime v3 by accident

Mission continuation is orchestration over the canonical TaskRuntime. It is not another lifecycle, truth engine, planner, dispatcher or policy authority.

### 15.5 Preserve global boundaries

Static configuration remains appropriate for global protections such as protected roots, forbidden hosts, secret constraints, destructive command policy and safe staging roots.

Static configuration must not become a project allowlist.

---

## 16. Final wave Definition of Done

This wave is CLOSED only when all of the following are true:

- M1–M10 are CLOSED;
- one frozen mission contract owns mission strategy/resources/authority/completion requirements;
- local resources are prompt-dynamic;
- remote repository resources are prompt-dynamic;
- repository + branch + operation authority is enforced;
- human authority is distinguishable from requested capability;
- final tool gates consume mission authority;
- TaskRuntime and tool/agent policies cannot disagree on canonical authority;
- Git/network capabilities are granular and compositional;
- destructive Git remains fail-closed;
- mission staging is dynamically derived and governed;
- end_to_end_governed creates subsequent TaskRuns without another prompt when authority permits;
- cross-phase evidence determines final truth;
- public SpeakerTruth cannot overclaim;
- fresh manual E2E mission succeeds or blocks honestly;
- an unrelated project/repository fixture proves generality;
- no project/repository-specific production allowlist was added;
- both current-state files and this document reflect the final architecture;
- tracked local main equals tracked origin/main after canonization.

---

## 17. Success criterion in one sentence

AIpinho must be able to receive one human mission prompt, derive and freeze its local and remote resources plus explicit authority, autonomously traverse the canonical governed phases that authority permits, and report success only when cross-phase RuntimeTruth proves the requested outcome.

---

## 18. Maintenance rule for future conversations

When continuing this wave in a later conversation, start by reading:

1. current production code/config for the active sprint;
2. CURRENT_STATE.md;
3. AIpinho_context_pack/docs/context/current_state.json;
4. this document;
5. validated evidence from the most recently closed sprint.

Do not assume a sprint is complete merely because this document describes it.

The current-state files identify what has actually been canonized.

This document identifies where the wave is going and the invariants that must not be lost.
