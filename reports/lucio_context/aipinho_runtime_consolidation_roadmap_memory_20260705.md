# AIpinho Runtime Consolidation Roadmap Memory

Generated: 2026-07-05

Purpose: persistent context note from Lucio's roadmap guidance for the next AIpinho phases.

## Core Interpretation

The project is not in a "nothing works" state.

The current diagnosis is:

- Many components already work in isolation.
- The missing layer is a mature internal Runtime that consistently orchestrates those components.
- Fire Test 5 did not show simple failure; it exposed the boundary between governance architecture and execution architecture.
- The project should now move from "inventing components" to "consolidating the platform."

Operating rule from this point:

> Do not prioritize new features until they can pass through the canonical Runtime.

Every new capability must answer:

> Does this feature traverse the canonical Runtime end to end?

If no, it should not enter yet.
If yes, it should fit naturally into the platform.

## Phase 1: Runtime Consolidation

Goal:

Transform AIpinho into a governed execution platform where every operation traverses the same Runtime regardless of task type.

### Sprint R1: Artifact Runtime

Success Contract: `ARTIFACT_RUNTIME_READY`

Goal:

Separate definitively:

- Workspace
- Artifact Store
- Runtime Outputs

Workspace must not be confused with evidence storage.

Required artifact fields:

- `artifact_id`
- `logical_path`
- `storage_ref`
- `producer_step`
- `task_id`
- `task_run_id`
- `validation_status`
- `evidence_refs`
- `timestamps`

Expected result:

Read-only operations can still generate governed reports/artifacts without mutating the source workspace.

### Sprint R2: Execution Envelope

Success Contract: `EXECUTION_ENVELOPE_READY`

Goal:

Eliminate scattered state by creating one root execution object.

`ExecutionEnvelope` should contain:

- Task
- TaskRun
- ExecutionPlan
- RuntimeProfile
- WorkspaceContext
- ArtifactCollection
- Validation
- Completion
- SpeakerTruth

Rule:

Runtime components should receive the envelope instead of loose unrelated objects.

Benefits:

- fewer inconsistencies;
- fewer parameters;
- fewer parallel states;
- better observability.

### Sprint R3: Runtime Observability

Success Contract: `RUNTIME_OBSERVABILITY_READY`

Goal:

Make Runtime execution fully observable.

Every execution should record:

- lifecycle
- step
- duration
- inputs
- outputs
- artifacts
- validation
- truth

Build:

- Runtime Timeline
- Runtime Graph
- Runtime Inspector
- Runtime Replay

Target:

Every execution should be reproducible/auditable.

### Sprint R4: Workflow Runtime

Success Contract: `WORKFLOW_RUNTIME_READY`

Goal:

Every operation becomes a Workflow, regardless of whether it is:

- read
- build
- patch
- OCR
- diagnostic
- benchmark
- review

Workflow shape:

- steps
- progress
- artifacts
- validation
- completion

States:

- CREATED
- READY
- RUNNING
- WAITING_APPROVAL
- WAITING_DELEGATION
- WAITING_DEPENDENCY
- VALIDATING
- FINISHED
- FAILED
- BLOCKED

### Sprint R5: Capability Runtime

Success Contract: `CAPABILITY_RUNTIME_READY`

Goal:

Remove special Runtime Profiles and replace them with capability-driven assembly.

Example capability set:

```yaml
workspace_mutation: false
artifact_generation: true
requires_task: true
validation_required: true
approval_required: false
delegation_allowed: false
speaker_truth_required: true
```

Rule:

The Runtime should assemble behavior from capabilities, not from task-specific hardcoded profiles.

No specific Fire Test cases.
No special ifs.
No provider-specific branches.

### Sprint R6: Runtime Truth

Success Contract: `RUNTIME_TRUTH_READY`

Goal:

Unify Completion and Speaker Truth.

Canonical chain:

- Completion
- Validation
- Truth Engine
- UI
- API
- Provider

Never allow:

- Completion = success
- SpeakerTruth = blocked

Required claims:

- Task created requires `task_id`
- Approval created requires `approval_id`
- Artifact created requires `artifact_id`
- Delegation requires `delegation_id`
- Build requires `build_report`
- Polling requires `poll_count`

After R6:

Run Fire Test 5 phases 1-5 again with:

- no hotfixes;
- no special Runtime;
- no specific-case treatment.

The Runtime must solve the work by itself.

## Desired End State After R1-R6

AIpinho should have:

- one Runtime;
- one Governance path;
- one Validation authority;
- one Truth authority;
- one Artifact model;
- one Workflow model;
- capability-driven execution.

This means AIpinho becomes a platform, not a pile of services.

## Phase 2: Feature Evolution

Only after Runtime consolidation.

### F1: Planner Intelligence

- multi-objective planning;
- cost estimation;
- risk estimation;
- automatic replanning.

### F2: Memory Intelligence

- operational memory;
- architecture memory;
- engineering memory;
- accumulated experience;
- supervised learning.

### F3: Advanced RAG

- contextual RAG;
- project RAG;
- sprint RAG;
- artifact RAG;
- temporal RAG.

### F4: Vision Runtime

- OCR;
- screenshots;
- diagrams;
- PDF;
- UI review;
- layout analysis.

### F5: Patch Intelligence

- AutoPatch;
- Patch Preview;
- intelligent rollback;
- impact analysis;
- safe merge.

### F6: Auto Recovery

- resume interrupted executions;
- reconstruct context;
- partial re-execution;
- workflow recovery.

### F7: Engineering Doctor

- continuous analysis;
- technical debt detection;
- architecture review;
- performance;
- security;
- quality.

### F8: AIpinho Studio

- full dashboard;
- Runtime Timeline;
- Workflow Inspector;
- Artifacts;
- Marketplace;
- Observability;
- visual debugging.

### F9: Distributed Executors

- local executor;
- Android executor;
- desktop executor;
- cloud executor;
- Docker executor;
- remote executor.

### F10: Autonomous Engineering

Final objective:

AIpinho becomes a platform capable of:

- analyzing complex projects;
- creating governed plans;
- requesting approvals;
- executing complete workflows;
- generating auditable artifacts;
- validating evidence;
- recovering failures;
- learning from previous executions;
- operating multiple executors consistently.

## Priority Decision

Immediate priority should be Runtime Consolidation R1-R6.

Do not continue adding major agent features before the execution substrate is consolidated.

The next sprint should start with R1: Artifact Runtime.

## Non-Negotiable Philosophy

- No hardcode.
- No specific-case solution.
- No provider-specific branch.
- No Fire-Test-only path.
- No fake success.
- No artifact without artifact record.
- No completion without validation/truth agreement.
- No workflow outside canonical Runtime.
- AIpinho must execute what is requested correctly, not only discuss it.

## Memory Verdict

`RUNTIME_CONSOLIDATION_ROADMAP_ACCEPTED_AS_CONTEXT`
