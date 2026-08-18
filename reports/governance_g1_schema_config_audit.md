# Governance G1 Schema and Config Audit

- Audit type: governance_topology_audit
- Generated UTC: 2026-06-26T07:31:34.299Z
- Checkpoint: G1_SCHEMA_CONFIG_AUDIT_READY

| Schema | File | Claimed truth | Status fields | Risk |
| --- | --- | --- | --- | --- |
| OperationContract | src/aipinho/schemas/governance/operation_contract.py | normalizes operation/actions/workspace/risk | approval_required, execution_allowed, execution_plan.mode | competes with PolicyDecision and TaskContractDraft for truth |
| PolicyDecision | src/aipinho/schemas/policy/policy_decision.py | Policy Kernel decision | status, safe_to_execute, safe_to_preview, approval_required_for | uses needs_approval while other layers use ask/approval_required |
| TaskContractDraft | src/aipinho/schemas/tasks/task_contract_draft.py | draft before preview | status, safe_to_execute, safe_to_preview, executable_plan_ref | can carry requested actions without executable plan unless guarded |
| TaskPreview | src/aipinho/schemas/tasks/task_preview.py | preview shown to user | status, executable_plan_ref, expected_outcomes | can be approval_required while warning missing_executable_plan |
| ApprovalRequest | src/aipinho/schemas/approvals/approval_request.py | persistent approval request | status, execution_status, resume_status, block_reason_code | mixes approval lifecycle and execution resume truth |
| ApprovalDecision | src/aipinho/schemas/approvals/approval_decision.py | human decision | decision, decided_at | must be the only approval decision source for command/button paths |
| TaskRun | src/aipinho/schemas/runtime/task_run.py | runtime execution | status, current_step_id, validation_status | can diverge from ChatResponse and ApprovalRequest.resume_status |
| SessionGrant | src/aipinho/schemas/interaction/session_grant.py | temporary permission | status, expires_at, remaining_uses | can be confused with ConfigChangeRequest by broad language |
| WorkspacePermissionDecision | src/aipinho/services/config_governance/workspace_permission_matrix_service.py | effective workspace/action permission | status, requires_approval, reason_code | parallel with WorkspaceRoleContractService |
| Artifact/ArtifactPreview | src/aipinho/schemas/artifacts | artifact evidence and downloads | status, validation_status, requires_token | chat links can become a parallel artifact truth |
| ValidationResult | src/aipinho/services/validation | validation evidence | status, score, blocking_findings | completion resolver and validation gate can disagree |
| ChatResponse | src/aipinho/schemas/chat/chat_response.py | chat answer contract | status, message_type, approval_required, task_id | can contain derived partial state from noncanonical sources |
| RuntimeProfile | config/runtime/profiles/*.yaml | execution profile | steps, allowed_actions, required_capabilities | aggregate runtime_profiles.yaml appears stale |
| ToolInvocation | src/aipinho/schemas/agents/tool_gateway.py | governed tool call | status, block_reason_code, validation_result | tool gateway can be invoked outside full TaskRun lifecycle |

Required answers:

- More than one field represents final state: yes. Examples include status, chat_response_status, execution_status, validation_status, resume_status, safe_to_execute, execution_allowed, approval_required.
- Approval truth should be ApprovalRequest plus ApprovalDecision, but UI and TaskRun continuation store derived state.
- Final status truth is split across TaskRun, TaskCompletionResolver, ValidationResult, ChatResponse, and publisher.
- Policy truth is split across PolicyKernelService, OperationContractService, WorkspacePermissionMatrixService, WorkspaceRoleContractService, and capability gates.
- Artifact truth should be registry-backed, but chat links and tool outputs can become parallel truth.
- Success should be decided only from a final lifecycle snapshot after validation.
