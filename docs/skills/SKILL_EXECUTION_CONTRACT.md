# Skill Execution Contract

`SkillExecutionRequest` requires:

- `skill_id`
- `requesting_agent_id`
- `session_id`
- `requested_capabilities`
- optional `project_profile_id`
- optional `workspace_profile_id`
- optional `inputs`

Execution stages:

1. Resolve manifest.
2. Validate manifest.
3. Check status.
4. Check required capabilities.
5. Create or reuse an `AgentRun`.
6. Emit skill events.
7. Invoke allowed tools through Tool Gateway.
8. Persist `SkillExecutionResult`.
9. Publish final answer message.

Side effects are never performed directly by `SkillExecutionService`.

Result fields include:

- `skill_execution_id`
- `status`
- `tool_invocation_ids`
- `policy_decision_ids`
- `validation_ids`
- `output_artifact_refs`
- `evidence_refs`
- `blocked_reasons`
- `speaker_truth_status`

Raw remains hidden by default.
