# AIpinho - Consolidated Context for Lucio

Generated: 2026-07-05

Scope: Sprint A onward, including governance blocks, hotfixes, Fire Tests, Sprints H through P, and the latest Runtime Vertical Slice Q/R/T/V.

Source basis:

- Local reports under `C:\Dev\AIpinho\reports`.
- Current codebase state after the latest runtime vertical slice.
- Conversation history and sprint/hotfix sequence supervised by Codex.

Important note:

The strongest auditable report chain in the repository starts around Governance Blocks A-F and Sprints H-P. Earlier "Sprint A-G" work is summarized as architectural context from the conversation and implementation history, while later phases are grounded in concrete reports and test evidence.

---

## 1. Executive Summary

AIpinho evolved from a multi-chat/agent launcher into a governed execution platform with:

- Canonical governance lifecycle.
- Universal Task Session.
- Approval and permission contracts.
- Speaker Truth enforcement.
- External collaboration adapters.
- Universal Approver layer.
- Delegation contracts.
- Cooperative Execution Graph.
- Intelligent Planner.
- Dynamic Agent Marketplace.
- Mobile and Launcher alignment.
- Fire Test evidence that AIpinho can generate and validate a real Android project through governed flow.

The latest Runtime Vertical Slice proved an important operational behavior:

> A read-only workspace analysis can still create real artifacts through governed artifact storage, with a real TaskRun, real artifact records, phase dependency validation, and Speaker Truth consistency, without mutating the source workspace.

This is a strong step toward making AIpinho a real execution authority. However, the Runtime is not fully consolidated yet. Lucio's recommendation is directionally correct: the next priority should be Runtime consolidation instead of adding more surface features.

Recommended next priority:

1. Make Artifact Runtime first-class.
2. Introduce a canonical `ExecutionResult`.
3. Add Runtime Observability.
4. Generalize Workflow Runtime for every executable operation.
5. Remove remaining operation-specific routing by letting capabilities drive behavior:
   - `workspace_mutation`
   - `artifact_generation`
   - `requires_task`
   - `execution_required`
   - `approval_required`
   - `validation_required`

The central philosophy remains:

- No hardcode.
- No specific-case fixes.
- Modular, traceable, configurable architecture.
- AIpinho must execute correctly, not only discuss tasks.
- AIpinho remains the execution, persistence, validation, approval, and Speaker Truth authority.

---

## 2. High-Level Timeline

### Phase A-G: Early Multi-Agent and Governance Foundation

This phase established the broad platform direction:

- AIpinho main chat.
- Gemini Executor island.
- Codex executor island.
- Lucio strategic/chat island.
- Launcher tabs.
- Mobile tabs.
- Session persistence.
- Chat/session creation, rename, switch, delete.
- Scroll and UX fixes across chat terminals.
- Workspace registry.
- Policy kernel.
- Tool gateway.
- Shell/write/read permissions.
- Approval flow.
- Artifact/report lifecycle.
- Memory gateway.
- Dashboard/debugger.
- Self-healing and regression reports.
- Sandbox/project factory.
- Skill system.
- Agent bridge and PinhoForge bridge work.

Key issue discovered during these phases:

AIpinho had too many parallel routes and partial systems. Similar concepts existed in multiple places:

- policy
- permissions
- approvals
- previews
- task runs
- artifacts
- validation
- runtime status
- Speaker Truth
- route-specific behavior

This eventually caused real bugs:

- read-only prompts becoming writes;
- planning prompts becoming permission grants;
- approval created without executable TaskDraft;
- approval accepted but TaskRun blocked;
- validation passed while outputs were missing;
- final messages claiming success without execution evidence;
- Mobile, Launcher, Continue, Pipeline and chat sometimes using different paths.

These failures triggered the governance reset.

---

## 3. Major Hotfix Themes

### 3.1 Approval Bootstrap Paradox

Problem:

AIpinho blocked operations that required approval before creating the ApprovalRequest.

Corrected principle:

Creating these objects is not dangerous execution:

- OperationContract
- TaskDraft
- TaskPreview
- ApprovalRequest
- approval preview

If policy is `ask`, AIpinho must create preview plus ApprovalRequest and wait. It must not block before the operator has something to approve.

Residual concern:

The approval must be tied to an executable draft. Approval of vague permission is not enough.

---

### 3.2 Policy Kernel: `ask` vs `denied` vs `allowed`

Problem:

Dangerous actions such as `apply_patch`, `write_files`, and `run_command` were sometimes blocked dry, or worse, marked as allowed without an executable plan.

Corrected principle:

- `allowed`: only executable when constraints and plan are valid.
- `ask`: create preview plus ApprovalRequest, no execution yet.
- `denied`: block with reason code and safe next action.

Hard rule:

Shell, patch, write, build, delete, install and similar side effects cannot be `permission: allowed` by default without:

- real workspace;
- target paths;
- executable plan;
- approval scope when needed;
- validation plan;
- traceable policy snapshot.

---

### 3.3 Executable Approval Resume

Problem:

An approval was accepted but TaskRun blocked with:

- `project_generation_plan_missing`
- `no_targetable_project_generation_action`
- `missing_required_expected_outcomes`

Root cause:

The system created an ApprovalRequest for a generic permission, not for an executable TaskDraft.

Corrected principle:

ApprovalRequest must point to:

- `approval_id`
- `session_id`
- `preview_id`
- `draft_id`
- `operation_id`
- `operation_type`
- `contract_type`
- `runtime_profile`
- `workspace_path`
- `requested_actions`
- `expected_outcomes`
- `executable_plan_ref`
- `preview_hash`
- `policy_snapshot_hash`

If there is no executable plan, approval must not be created for execution.

---

### 3.4 Router and Intent Fixes

Problems observed:

- operational prompts routed to `session_diagnostic`;
- planning prompts routed to `permission_grant_request`;
- workspace registry queries routed as generic conversation;
- project bootstrap prompts routed to rebuild or blocked without approval;
- read-only prompts routed to patch/write/project creation.

Corrected principles:

- Negative constraints first.
- Explicit read-only wins over weak write/project/shell signals.
- Safe explicit override is allowed only when it reduces risk.
- `session_diagnostic` only when the user explicitly asks for session diagnosis.
- Workspace permission query has its own intent.
- Project/folder creation with policy `ask` should create preview and ApprovalRequest, not block dry.

---

### 3.5 PermissionGrant Overcapture

Problem:

Prompts containing governance words such as "grant", "policy", "approval" or "workspace registry" were being captured as permission grant requests even when the user explicitly said:

- this is not a grant;
- do not write;
- do not create ApprovalRequest;
- classify as `product_planning_readonly`.

Corrected principle:

Permission grants require positive permission language. Negative phrases and planning-only language must block grant capture.

---

### 3.6 Read-only Safety Patch

Problem:

Read-only prompts were sometimes classified as mutable operations.

Corrected invariants:

- Extract negative constraints before selecting mutable intent.
- Read-only/no-side-effect is a hard override.
- Read-only must yield:
  - `readonly: True`
  - `side_effect_requested: False`
  - no write actions
  - no ApprovalRequest
  - no operational TaskRun unless a read-only execution with artifacts is explicitly required
- Dangerous operations without executable plan must not be allowed.
- Validation/completion cannot report passed when required outputs are missing.

The latest vertical slice preserves this distinction while adding a new class:

> read-only source workspace, but artifact generation in governed storage is execution and therefore creates a TaskRun.

---

### 3.7 Continue / VSCode Adapter

Implemented OpenAI-compatible local endpoints:

- `GET /v1/models`
- `POST /v1/chat/completions`

Principles:

- no OpenAI dependency;
- no OpenAI key requirement;
- local AIpinho-compatible connection;
- Continue can use AIpinho as local assistant;
- write/shell actions are governed, not performed silently from connection setup.

Later relaxed into governed dev mode, still through AIpinho governance.

---

### 3.8 Speaker Truth and Polling

Implemented and hardened:

- no false success claims;
- no "completed" when TaskRun is blocked;
- no "validated" when outputs are missing;
- speaker updates with task state;
- external operators cannot rewrite AIpinho's response as if it were their own execution result.

The latest vertical slice verifies:

- `validation_status=passed` only after real artifact records exist;
- `safe_to_report_success=true` only when expected outputs are fulfilled;
- Speaker Truth can claim success only when completion is safe;
- missing dependencies block instead of reporting READY.

---

## 4. Governance Blocks A-F

### Block A: Governance Topology Audit

Verdict: `GOVERNANCE_BLOCK_A_AUDIT_READY`

Purpose:

Map the tangled governance topology before changing it.

Findings:

- competing sources of truth for status;
- competing policy paths;
- competing approval stores/listing paths;
- task/preview/approval inconsistencies;
- artifact lifecycle not fully canonical;
- response renderer sometimes not grounded in final lifecycle state.

Deliverables included:

- baseline cases;
- schema/config audit;
- route/config audit;
- intent/router audit;
- policy/approval audit;
- runtime/execution audit;
- conflict matrix;
- recommendations.

---

### Block B: Canonical Governance Lifecycle Rewire

Verdict in reports: `GOVERNANCE_BLOCK_B_CANONICAL_REWIRE_REQUIRES_PATCH`

What it achieved:

- introduced/expanded canonical lifecycle wiring;
- consolidated major policy/permission/approval/runtime flow concepts;
- moved toward replacing public routes with canonical service paths;
- identified residual legacy.

Why not full READY:

- residual legacy paths remained;
- some routes/configs still had compatibility behavior;
- artifact/runtime result model still needed deeper consolidation.

Block C was required to continue migration.

---

### Block C: Residual Legacy Migration

Purpose:

Continue quarantine/migration of leftover legacy paths from Block B.

Result:

Moved system closer to canonical routing and reduced duplicated runtime paths, but did not eliminate every remaining compatibility or fallback concern.

Strategic conclusion:

The system needed behavioral proof, not just structural migration. That led into Block D.

---

### Block D: Behavioral Governance Firetest

Key checkpoints:

- G20 Context Discovery Gate
- G21 Readonly Analysis Intent
- G22 Fix Request Two Phase
- G23 Capability Truth
- G24 Preview Quality Gate
- G25 Behavioral Regression
- G26 Multichannel Firetest

Evidence:

- `G26_MULTICHANNEL_GOVERNANCE_FIRETEST_READY`
- no false success before completion/validation;
- behavioral regressions added permanently;
- read-only planning and mutable execution separated more clearly.

Importance:

Block D turned the governance work from "routes look better" into "behaviors are tested."

---

### Block E: App Creation Recovery and Canonical Project Bootstrap

Purpose:

Recover app creation flows and make project bootstrap canonical.

Value:

This prepared AIpinho for real app creation again, including later Fire Test 4.

Key concept:

Project creation must be a governed lifecycle:

intent -> discovery -> executable plan -> preview -> approval -> TaskRun -> validation -> artifacts/result.

---

### Block F: Live System Alignment

Verdict: `BLOCK_F_LIVE_SYSTEM_ALIGNMENT_READY`

Closed P0:

- Executor could not write when no full draft plan existed.
- Project generation runtime now injects matching TaskDraftStore for approved plan execution.
- Approval evidence includes `draft_id` and `executable_plan_ref`.

P1 closed:

- duplicate public `/api/v1/tools*` routes;
- full pipeline path certification;
- artifact zip/binary registry certification;
- role/model live inference invocation;
- Mobile/Launcher build and scroll/terminal contract QA.

Focused detector result:

- P0=0, P1=0, P2=0, UNKNOWN=0.

Environment note:

- some emulator visual QA was blocked by environment, but Android build and focused UI contracts passed.

---

## 5. Fire Test 4

Verdict: `AIPINHO_FIRETEST4_MOBILE_GAME_READY`

Target:

AIpinho generated a real Android/Kotlin mobile game project: SapoAndando2.

What was proven:

- AIpinho generated the Android project through governed chat flow.
- AIpinho produced an APK.
- APK installed on physical device.
- App launched.
- Game screen rendered.
- Tap interaction did not crash.
- Codex did not manually edit the generated target project.

Evidence:

- APK path: `C:\Users\rafae\Documents\AIpinhoTestes\SapoAndando2\app\build\outputs\apk\debug\app-debug.apk`
- TaskRun: `task_run_adf944f8cce1494b9d1827a00ceb8b00`
- Shell exit code: 0
- Device: `ZF5253V88S`
- Logcat crash/error lines after launch/tap: 0
- Visual screenshots stored in `reports/fire_tests`.

Generic AIpinho fixes from Fire Test 4:

- Android/Kotlin template aligns Java compileOptions and Kotlin `jvmTarget` to 17.
- Gradle JVM mismatch recovery creates executable approval-gated plan.
- Recovery plans backed by build diagnostics carry `analysis_ref` instead of bypassing approval.

Residual finding:

Approval traceability still has one polish issue:

- JVM-fix approval stored `resume_status=completed` but did not persist `task_run_id`.
- The task run completed and was discoverable, so this did not block the fire test.
- This should be tightened as traceability debt.

---

## 6. Sprints H-P

### Sprint H: Universal Task Session

Verdict: `UNIVERSAL_TASK_SESSION_FOUNDATION_READY`

Implemented:

- public governed TaskRun session;
- status, phase, progress, current step, approval, validation, artifacts, result;
- polling endpoints;
- event/artifact/summary views;
- Mobile/Dashboard/Codex/Gemini/API can all consult same session.

Architectural value:

This created a common runtime observation protocol for all clients.

---

### Sprint I: External Collaboration Layer, Gemini v1

Verdict: `EXTERNAL_COLLABORATION_LAYER_GEMINI_V1_READY`

Implemented:

- External Agent Interface.
- Success Contract.
- External Task Contract.
- Review Contract.
- Review Registry.
- Conversation Registry.
- Universal polling for external adapter.
- Provider-neutral external collaboration routes.

Principle:

Gemini became an external collaborator/reviewer, not execution authority.

---

### Sprint J: Continuous Collaboration Runtime

Verdict: `CONTINUOUS_EXTERNAL_COLLABORATION_RUNTIME_READY`

Implemented:

- Continuous Collaboration Session.
- Success Contract Runtime.
- Success Evaluation Contract.
- continuous polling over Universal Task Session.
- event subscription.
- review/evaluation loop.
- external conversation memory.

Principle:

External collaboration can continue across task runtime state, but AIpinho remains the authority.

---

### Sprint K: Universal Approver Layer

Verdict: `UNIVERSAL_APPROVER_LAYER_READY`

Implemented:

- `UniversalApprover`
- `ApprovalOrigin`
- approval signatures
- trust levels
- capability matrix
- universal approver APIs
- UI surfaces for approvers

Principle:

Gemini, Codex, humans and future agents can approve through the same pipeline. None modify the store directly.

---

### Sprint L: Operator Experience and Speaker Truth Enforcement

Verdict: `OPERATOR_EXPERIENCE_SPEAKER_TRUTH_READY`

Implemented:

- external speaker truth auditor;
- Gemini/Codex can validate/reject/request review, but cannot rewrite AIpinho output as execution truth;
- allowed Universal Task Session public states only;
- Launcher and Mobile comfort improvements:
  - internal scroll
  - selectable text
  - copy/export
  - expand conversation
  - search
  - no invasive autoscroll.

Value:

This turned external adapters into more mature operators instead of parallel chatbots.

---

### Sprint M: Real Delegation Runtime

Verdict: `REAL_DELEGATION_RUNTIME_READY`

Implemented:

- `DelegationDecisionEngine`
- `DelegationContract`
- `DelegationPollingService`
- `DelegationTruthValidator`
- `WAITING_DELEGATION` state
- neutral routes under `/api/v1/external`

Smoke:

- Direct `2+2` stayed direct.
- "Pergunte a AIpinho quanto e 2+2" created real delegation contract with parent and child runs.

Value:

An adapter cannot claim delegation without `delegation_id`, parent run, child run and polling evidence.

Residual:

Child run creation is governed, but effective execution still depends on the target operation/profile pipeline.

---

### Sprint N: Multi-Agent Execution Graph

Verdict: `MULTI_AGENT_EXECUTION_GRAPH_READY`

Implemented:

- `ExecutionGraph`
- `ExecutionNode`
- `ExecutionEdge`
- `ExecutionDependency`
- `NodeRuntime`
- `ExecutionResult` at graph/node level
- node retry/cancel/start/complete/fail
- graph polling
- node-level artifacts, review, approval, metrics, retry count, speaker truth.

Default cooperative graph:

- Planner
- Executor
- Debugger
- Vision
- OCR
- Review
- Memory
- Supervisor
- Finalizer

Important:

Providers do not create/finalize graphs. AIpinho remains authority.

Residual:

This sprint implemented graph lifecycle. Full automatic decomposition was left to Sprint O.

---

### Sprint O: Intelligent Planner

Verdict: `INTELLIGENT_PLANNER_READY`

Implemented:

- Planning Engine.
- Task Decomposer.
- Execution Strategy Builder.
- Dependency Resolver.
- Graph Optimizer.
- Risk-aware Planner.
- Planning Report.
- planning policies:
  - `planning_policy.yaml`
  - `planning_constraints.yaml`
  - `planning_cost_policy.yaml`
  - `planning_parallel_policy.yaml`
  - `planning_review_policy.yaml`

Smoke:

Android task created graph with:

- planner
- executor
- debugger
- vision
- OCR
- review
- memory
- supervisor
- finalizer.

Residual:

- planner uses configurable heuristics;
- model-backed deeper reasoning can be plugged later;
- dynamic topology replan is still limited.

---

### Sprint P: Dynamic Agent Ecosystem and Capability Marketplace

Verdict: `DYNAMIC_AGENT_ECOSYSTEM_READY`

Implemented:

- `AgentManifest`
- capabilities
- scopes
- heartbeat
- health snapshots
- dynamic runtime registry
- capability query
- failover
- auto-disable policy
- marketplace UI in Launcher and Mobile
- Planner selects executors by capability via marketplace.

Evidence:

- 9 official agents loaded.
- 17 capabilities discovered.
- OCR query returned `ocr_local`.
- Planner Android selected local agents by capability.

Residual:

- runtime registry is JSON local, not transactional store;
- external health endpoints are modeled but not fully background-polled;
- some legacy runtime profiles remain as historical fallback.

---

## 7. Latest Runtime Vertical Slice Q/R/T/V

Verdict: `RUNTIME_ANALYSIS_VERTICAL_SLICE_READY`

Files changed:

- `src/aipinho/services/governance/runtime/readonly_analysis_artifact_runtime_service.py`
- `src/aipinho/services/governance/lifecycle/canonical_public_chat_service.py`
- `src/aipinho/services/governance/lifecycle/governance_lifecycle_service.py`
- `src/aipinho/services/governance/runtime/canonical_runtime_service.py`
- `src/aipinho/services/governance/lifecycle/public_route_lifecycle_service.py`
- `src/aipinho/services/governance/intent/canonical_intent_router.py`
- `config/runtime/task_run_event_policy.yaml`
- `tests/governance/test_runtime_vertical_slice.py`

Behavior added:

- Read-only analysis with explicit artifact paths creates a real TaskRun.
- Artifacts are stored in Universal Artifact Registry, not the source workspace.
- Requested artifact paths are validated.
- Completion blocks if required artifacts or validation evidence are missing.
- Phase 2 can validate and consume Phase 1 artifacts through phase artifact store.
- Pure read-only planning still does not create tasks, approvals or artifacts.

Safety:

- Source workspace mutation remains false.
- No shell, patch, build, install, delete or source write enabled.
- Approval is not required for governed artifact generation when source workspace mutation is false.

Tests:

- Runtime vertical slice focused tests: 4 passed.
- Combined governance regression set: 22 passed.

Truth consistency:

- validation passed only after real artifact records exist;
- completion safe only when expected outputs are fulfilled;
- Speaker Truth success only when completion is safe;
- missing phase dependencies block instead of creating TaskRun;
- missing artifact outputs block instead of returning READY.

Architectural significance:

This is the first clean proof of a subtle capability:

> read-only with respect to source workspace is not the same as no execution. AIpinho can execute a governed read-only workflow that produces artifacts in governed runtime storage.

This should become the general model for all executable operations.

---

## 8. Current Architecture State

### Strong foundations now present

- Canonical public chat/lifecycle path exists.
- Universal Task Session exists.
- Universal Approver exists.
- Delegation contracts exist.
- Execution Graph exists.
- Planner exists.
- Agent Marketplace exists.
- Mobile and Launcher consume more shared view-models than before.
- Speaker Truth blocks false success.
- Approval gates are tied more closely to executable plans.
- Fire Test 4 proved real app generation.
- Runtime Vertical Slice proved artifact-producing read-only task.

### Remaining structural debt

1. Artifact Registry is not yet a full first-class Runtime subsystem.
2. `ExecutionResult` exists in graph work, but not yet as universal final object across every operation.
3. Observability is still mostly event/report/task based, not full runtime metrics/tracing.
4. Workflow Runtime is not fully generalized for every operation type.
5. Vertical Slice service is still too operation-specific.
6. Some legacy profiles/routes remain as historical fallback.
7. Approval traceability has a known polish gap from Fire Test 4.
8. Planner replan is still conservative and does not fully rewrite graph topology dynamically.
9. Marketplace runtime store is JSON local.
10. External agent health polling is modeled but not fully automatic.

---

## 9. Lucio's Recommendation, Adapted

Lucio recommended:

1. Artifact Runtime.
2. ExecutionResult.
3. Runtime Observability.
4. Workflow Runtime.
5. Generalization away from `workspace_analysis_readonly_with_artifacts`.

I agree with the philosophy and would adapt it into a sequence that preserves momentum while reducing risk.

### Proposed next sequence

#### Sprint R1: Artifact Runtime First-Class

Goal:

Turn Artifact Registry into a true runtime subsystem.

Required:

- retention policy;
- versioning;
- hashes;
- artifact lineage;
- `task_run_id`, `graph_id`, `node_id`, `phase_id`;
- artifact search;
- artifact validation;
- artifact dependency tracking;
- binary/zip integrity;
- download audit;
- orphan detection.

Why first:

The latest vertical slice depends on artifacts. If artifacts become the proof of execution, they need lifecycle guarantees.

---

#### Sprint R2: Canonical ExecutionResult

Goal:

One result object for all executions.

Should include:

- `execution_result_id`
- `task_run_id`
- `graph_id`
- `node_id`
- `operation_type`
- `capabilities_used`
- `inputs`
- `outputs`
- `artifacts`
- `validation`
- `approval`
- `policy`
- `speaker_truth`
- `status`
- `safe_to_report_success`
- `human_summary`
- `machine_summary`

Why second:

Without a canonical result, UI, Speaker Truth, artifacts and TaskRun completion can drift.

---

#### Sprint R3: Runtime Observability

Goal:

Make every TaskRun inspectable as an execution system, not just as a chat response.

Required:

- metrics;
- tracing;
- phase duration;
- node duration;
- queue time;
- approval wait time;
- artifact generation time;
- validation time;
- resource usage where available;
- failure categories;
- retry history;
- runtime health by operation/capability.

Why third:

AIpinho cannot reliably improve execution without measuring runtime behavior.

---

#### Sprint R4: Workflow Runtime Generalization

Goal:

Generalize the vertical slice into a workflow runtime that supports:

- diagnosis;
- read-only analysis;
- artifact generation;
- patch preview;
- write;
- build;
- test;
- benchmark;
- recovery;
- review.

No operation should require a special hardcoded path.

Workflow should be driven by:

- capabilities;
- contracts;
- policies;
- runtime profile;
- expected outputs;
- artifact requirements;
- validation requirements.

---

#### Sprint R5: Capability-Driven Runtime Generalization

Goal:

Remove special treatment for `workspace_analysis_readonly_with_artifacts`.

The runtime should decide from capability flags:

- `workspace_mutation`
- `artifact_generation`
- `requires_task`
- `execution_required`
- `approval_required`
- `validation_required`
- `graph_required`
- `can_run_without_workspace_write`

Expected outcome:

The same runtime path can handle:

- read-only no artifact;
- read-only with artifacts;
- write preview;
- approved write;
- shell test;
- build;
- project generation;
- review-only;
- benchmark.

---

#### Sprint R6: Fire Test 5

Goal:

Run a real project operation through the consolidated runtime:

- Planner decomposes.
- Execution Graph runs.
- Agent Marketplace selects agents.
- Artifact Runtime records outputs.
- ExecutionResult consolidates result.
- Observability records timings/events.
- Speaker Truth validates.
- AIpinho responds.

Recommended target:

Use a real application issue, such as the Pinhoabacaxi Musicas Desktop or another project with build/test/UI behavior, because it validates more than file creation.

---

## 10. Dependencies Before Fire Test 5

### Required dependencies

- Artifact Runtime first-class.
- Canonical ExecutionResult.
- Workflow Runtime generalization.
- Observability minimum viable metrics.
- Runtime result renderer grounded in ExecutionResult.
- Approval trace tightening.
- Capability-driven execution flags.

### Useful but not strictly blocking

- transactional store for marketplace runtime registry;
- background health polling for external/local agents;
- dynamic graph topology replan;
- richer visual graph QA;
- permanent storage lifecycle service;
- expanded emulator/physical device QA automation.

---

## 11. Known Risks

### P0 risks to prevent regression

- Any read-only prompt becoming mutable.
- Any dangerous operation returning `permission: allowed` without executable plan.
- Any approval created without executable draft/plan.
- Any TaskRun created without expected outputs.
- Any validation passed with missing outputs.
- Any final response claiming success while runtime blocked.

### P1 risks

- Artifact records exist but lack enough lineage/version/hash data.
- UI displays a status derived from stale task state instead of canonical runtime.
- Planner produces graph but operation execution falls back to legacy runtime profile.
- Marketplace health is stale.
- Approval traceability has incomplete task linkage.

### P2 risks

- UI polish for large histories/logs.
- Mobile/Launcher parity lag.
- Report proliferation.
- Storage growth from artifacts/logs/screenshots.

---

## 12. What Is Done vs What Still Needs Work

### Done with strong evidence

- Universal Task Session.
- External collaboration layer.
- Continuous collaboration runtime.
- Universal Approver.
- Operator UX and Speaker Truth.
- Real delegation contracts.
- Multi-agent execution graph.
- Intelligent planner.
- Dynamic agent marketplace.
- Fire Test 4 Android mobile game.
- Runtime Vertical Slice for read-only analysis with artifacts.

### Partially done

- Canonical lifecycle rewire.
- Legacy migration/quarantine.
- Artifact registry certification.
- Approval execution resume.
- General runtime profiles.
- Runtime result object.
- Observability.

### Still needed

- Artifact Runtime as first-class service.
- Canonical ExecutionResult across all execution paths.
- Unified workflow runtime for all operations.
- Full capability-driven runtime generalization.
- Stronger runtime metrics/tracing.
- Removal or quarantine of remaining legacy fallback paths.
- Traceability fix for approved recovery tasks missing `task_run_id`.

---

## 13. Recommended Message to Lucio

Lucio's strategic direction is correct, but I would phrase the next stage as:

> Stop adding new agent features temporarily. Consolidate the execution substrate.

The AIpinho now has enough pieces to execute real work, but those pieces must be made into one runtime spine:

1. Artifact Runtime proves what was produced.
2. ExecutionResult proves what happened.
3. Observability proves how it happened.
4. Workflow Runtime makes every operation use the same execution grammar.
5. Capability-driven generalization removes operation-specific hardcode.

After that, Fire Test 5 becomes meaningful because it tests the ecosystem, not a single route:

- Planner decomposition.
- Agent selection by capability.
- Execution Graph.
- Artifact lineage.
- Approval trace.
- Validation.
- Speaker Truth.
- Final result.

---

## 14. Final Verdict

Current state:

`AIPINHO_RUNTIME_FOUNDATION_ADVANCED_BUT_NEEDS_RUNTIME_CONSOLIDATION`

Recommended next milestone:

`CANONICAL_RUNTIME_CONSOLIDATION_READY`

Success criteria for next milestone:

- Artifact Runtime first-class.
- ExecutionResult canonical.
- Runtime Observability available.
- Workflow Runtime generalized.
- Vertical Slice behavior no longer special-cased.
- Fire Test 5 can run through the same runtime path from planning to final answer.

The AIpinho is no longer just a wrapper around chats. It has become a governed execution platform in progress. The next work should make that platform internally simpler, more canonical, and harder to accidentally bypass.
