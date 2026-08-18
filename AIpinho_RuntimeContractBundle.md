# AIpinho - RuntimeContractBundle

Status: RUNTIME_CONTRACT_BUNDLE_DRAFTED

## Purpose

`RuntimeContractBundle` is the single operational package passed between semantic, policy, runtime, artifact, validation, and response layers.

It prevents dozens of loose parameters from becoming competing sources of truth.

## Draft Shape

```yaml
RuntimeContractBundle:
  version: "1"
  bundle_id: string
  correlation_id: string
  source:
    channel: chat | mobile | launcher | api | external | pipeline
    session_id: string
    actor_id: string | null
  semantic:
    intent: string
    semantic_tags: []
    confidence: number
    ambiguity: number
    negative_constraints: {}
  conversation_context:
    thread_id: string | null
    prior_task_id: string | null
    current_workspace: string | null
  workspace:
    workspace_id: string | null
    project_root: string | null
    external_roots: []
    readonly_flags: {}
  operation:
    operation_id: string
    operation_type: string
    contract_type: string
    runtime_profile: string
    requested_actions: []
  policy:
    decision_id: string | null
    permission: allowed | ask | denied | blocked
    reason_code: string | null
    approval_required_for: []
  execution_plan:
    plan_id: string | null
    executable: boolean
    steps: []
    expected_outputs: []
    validation_plan: {}
    rollback_plan: {}
  approval:
    approval_id: string | null
    status: not_required | pending | approved | denied | expired | blocked
    approval_scope: string | null
  task:
    task_id: string | null
    task_draft_id: string | null
    task_run_id: string | null
    parent_task_id: string | null
  timeline:
    timeline_id: string | null
    current_event_id: string | null
  artifacts:
    required_artifacts: []
    produced_artifacts: []
    missing_artifacts: []
    artifact_identity:
      artifact_id: string | null
      logical_path: string | null
      storage_ref: string | null
      producer_step: string | null
      producer_event_id: string | null
      task_id: string | null
      task_run_id: string | null
      validation_status: validated | pending | failed | blocked | unknown
  validation:
    validation_status: not_started | running | passed | failed | blocked | not_applicable
    missing_outputs: []
  completion:
    status: created | running | waiting_approval | completed | failed | blocked | cancelled
    safe_to_report_success: boolean
  speaker_truth:
    final_answer_allowed: boolean
    forbidden_claims: []
    truth_source: runtime_truth_engine
    evidence_required:
      timeline: boolean
      validation: boolean
      artifacts: boolean
      completion: boolean
```

## Invariants

- Prompt text does not pass beyond semantic resolution as execution input.
- Mutable execution cannot be `allowed` without executable plan and policy evidence.
- Approval cannot exist for mutable execution without task draft and executable plan.
- Completion cannot be `completed` when validation/artifacts/timeline indicate blocked.
- SpeakerTruth cannot claim created/modified/executed/validated without evidence.
- Artifacts cannot become completion or SpeakerTruth evidence without task, task-run, producer step, storage, and timeline event binding.
- `TaskRunResult.status` is display data; operational success requires RuntimeTruth-backed canonical state.

## Migration

Initial implementation may wrap existing schemas. The wrapper must not become a third decision path; it must delegate to canonical authorities.
