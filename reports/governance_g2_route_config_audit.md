# Governance G2 Route and Config Audit

- Audit type: governance_topology_audit
- Generated UTC: 2026-06-26T07:31:34.299Z
- Checkpoint: G2_ROUTE_CONFIG_AUDIT_READY

| Channel | Endpoint | Handler | Main service | Task | Preview | Approval | Risk |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Direct chat | POST /api/v1/chat | chat_router.py | ChatService.respond | conditional | conditional | conditional | different path from persistent chat |
| Persistent chat | POST /api/v1/chat/sessions/{id}/send | chat_router.py | ApprovalCommand -> PermissionGrant -> OperationRouter -> persistent response | conditional | conditional | conditional | local branches plus partial ChatService delegation |
| Approvals | /api/v1/approvals* | approval_router.py | ApprovalService + ApprovalTaskContinuationService | after approve | no | yes | button/chat must share one store |
| Continue | GET /v1/models, POST /v1/chat/completions | continue_integration_router.py | Continue policy/regex + ChatService/OperationContract | conditional | conditional | conditional | separate VSCode classifier and policy |
| Pipeline/mobile | mobile view-model routes | mobile_view_model_router.py | PipelineMobileAggregator | no | no | no | state is aggregated from task and standalone approvals |
| Task runtime | task_runtime_router.py | task runtime routes | TaskRuntimeService/SupervisedExecutionLoop | yes | no | no | can run only safely if created from approved executable draft |
| Draft/preview | task_draft_router.py, preview_router.py | draft/preview routers | TaskContractDraftService/TaskPreviewService | draft | yes | not directly | preview can be non-executable |
| Patch | patch_planning_router.py, patch_apply_router.py | patch routers | Patch planning/apply services | conditional | yes | conditional | patch path can diverge from project generation |
| Artifacts | artifact routers, transfer_router.py | artifact routers | Artifact registry/write/status services | conditional | conditional | conditional | artifact output vs workspace write distinction must hold |
| Workspace/config | config_governance_router.py, workspace_flow_router.py | governance routers | WorkspacePermissionMatrix/ConfigChange services | conditional | yes | yes | temporary grant and permanent config change can mix |
| Realtime/health | realtime, health, monitor, supervisor | status routers | event/status services | no | no | no | degraded can derive from stale status helpers |

Required answers:

- Direct chat and persistent chat are not identical.
- Continue has a separate OpenAI-compatible adapter and policy/regex classifier.
- Approval buttons and approval chat commands can converge through ApprovalService, but UIs aggregate state separately.
- Some routes can create previews, approvals, artifacts, or tool invocations without one canonical lifecycle facade.
- View-models read from aggregators and may not be the source of truth.
