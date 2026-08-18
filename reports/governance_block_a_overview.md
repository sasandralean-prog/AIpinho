# Governance Block A Overview

- Audit type: governance_topology_audit
- Generated UTC: 2026-06-26T07:31:34.299Z
- Verdict: GOVERNANCE_BLOCK_A_AUDIT_READY

## Executive summary

Block A confirms the main hypothesis: AIpinho has multiple parallel governance paths for intent routing, policy/permission, approvals, runtime execution, validation, artifacts, and final speaker truth. Recent hotfixes closed several P0 holes, but the topology still needs a canonical lifecycle in Block B so all channels use the same state machine.

## Real flow today

user prompt -> channel adapter -> approval command / permission grant / operation router / prompt intelligence -> OperationContract and/or PolicyDecision and/or TaskContractDraft -> TaskPreview -> ApprovalRequest if ask and executable -> ApprovalDecision -> TaskRun -> executor/tool gateway/artifact registry -> completion resolver + validation gate -> chat publisher/mobile/launcher renderer.

## Competing sources of truth

- Intent/operation truth: ChatOperationDecision, PromptIntelligence IntentMap, OperationContract, TaskContractDraft.
- Policy truth: PolicyDecision, OperationPermissionDecision, WorkspacePermissionDecision, WorkspaceRoleDecision, CapabilityDecision.
- Approval truth: ApprovalRequest.status, ApprovalDecision, TaskPreview.status, ChatResponse.approval_required, PipelineMobileAggregator.
- Execution truth: TaskRun.status, ApprovalRequest.resume_status, TaskCompletionResolver, ValidationResult, ChatResponse.
- Artifact truth: ToolInvocation outputs, artifact registry, chat_response.artifact_links, presentation artifacts.
- UI truth: mobile view-model, launcher state, chat persisted messages, task_run publisher.

## Conflicting configs

- config/runtime/runtime_profiles.yaml: aggregate says patch/write/rag/memory disabled; conflicts with task_runtime_policy.yaml and config/runtime/profiles/*.yaml.
- config/runtime/task_completion_policy.yaml: missing project_generation/project_bootstrap contracts; conflicts with project_generation.yaml and project_bootstrap.yaml.
- config/policies/operation_contract_policy.yaml: action normalization separate from workspace permission aliases; conflicts with WorkspacePermissionMatrixService.ACTION_PERMISSION_ALIASES.
- config/integrations/continue_adapter_policy.json: Continue side-effect policy separate from chat/router; conflicts with chat_operation_routing_policy and permission matrix.
- workspace/artifact/patch target policies: artifact output and workspace write evaluated separately; conflicts with artifact/write/runtime services.

## Legacy candidates

- Direct ChatService.respond vs persistent chat _persistent_chat_response: parallel route handling.
- WorkspaceRoleContractService vs WorkspacePermissionMatrixService: overlapping workspace/action decision authority.
- config/runtime/runtime_profiles.yaml aggregate: stale capability status compared with per-profile runtime.
- Continue adapter side-effect regex layer: parallel classifier for VSCode.
- Generic TaskPreview summary renderer: obscures executable plan quality.
- TaskRunChatResultPublisherService standalone truth formatting: separate final-answer truth source.

## P0 risks

- No canonical lifecycle object/state enum spans intent -> operation -> preview -> approval -> run -> validation -> speaker.
- project_generation runtime profile lacks matching completion/result mapping.
- Policy/permission vocabularies are not normalized before rendering.
- Multiple channel entrypoints can bypass fixes applied to one chat path.
- Validation and completion truth can disagree about required outcomes.

## P1 risks

- Runtime status/degraded can be computed from stale aggregate config/status helpers.
- ApprovalRequest stores execution resume details, increasing stale UI risk.
- Continue adapter uses a separate regex classifier and policy file.
- Artifact lifecycle can be invoked from tool gateway/report writer outside a single runtime route.
- Publisher strings show encoding/mojibake risk in user-facing text.

## Recommendation for Block B

1. Canonical IntentDecision with precedence table and negative constraints.
2. Canonical OperationContract normalization for action/workspace/risk.
3. Single permission resolver output enum: allowed, ask, denied.
4. Preview builder emits plan_only_preview or executable_task_preview.
5. ApprovalRequest targets only executable draft or explicit non-execution approval.
6. TaskRun starts only from approved executable draft.
7. Completion resolver and validation gate share required outcomes.
8. Speaker Truth reads only from final lifecycle snapshot.
9. All channels call the same facade; old routes become adapters.

## Checkpoints

- G0_BASELINE_READY
- G1_SCHEMA_CONFIG_AUDIT_READY
- G2_ROUTE_CONFIG_AUDIT_READY
- G3_INTENT_ROUTER_AUDIT_READY
- G4_POLICY_APPROVAL_AUDIT_READY
- G5_RUNTIME_EXECUTION_AUDIT_READY
