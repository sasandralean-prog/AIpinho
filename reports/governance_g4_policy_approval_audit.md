# Governance G4 Policy, Permission Resolver, and Approval Audit

- Audit type: governance_topology_audit
- Generated UTC: 2026-06-26T07:31:34.299Z
- Checkpoint: G4_POLICY_APPROVAL_AUDIT_READY

| Finding | Severity |
| --- | --- |
| Permission vocabulary is split across needs_approval, ask, approval_required, approval_required_for, waiting_input. | P0 |
| ApprovalService now blocks approval creation when executable_plan_ref is missing. | P1 |
| ApprovalRequest also stores resume/block state, coupling approval to runtime truth. | P1 |
| WorkspacePermissionMatrixService and WorkspaceRoleContractService overlap. | P0 |
| SessionGrant and ConfigChangeRequest need stricter source/intention separation. | P0 |

Decision map:

- PolicyKernelService emits allowed/needs_approval/denied/needs_clarification.
- OperationContractService emits allowed/ask/denied.
- WorkspacePermissionMatrixService emits allowed/approval_required/denied.
- TaskPreview emits approval_required/blocked/ready-style states.
- ApprovalService creates approvals only from previews and executable drafts.
- ApprovalTaskContinuationService resumes after approval and blocks approved-but-not-executable cases.

Conclusion: ask must never dry-block before preview/approval creation; denied must block with reason_code; list/show/approve/deny approval operations must not require a prior approval.
