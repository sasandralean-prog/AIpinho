# Sprint 22 - Operation Contract

Gerado em: 2026-06-25 08:22:50

Veredito: SPRINT22_OPERATION_CONTRACT_REQUIRES_PATCH

## generated_at
2026-06-25 08:22:50

## sprint
22

## title
Operation Contract + Permission Resolver Unico

## verdict
SPRINT22_OPERATION_CONTRACT_REQUIRES_PATCH

## why_not_ready
[
  "OperationContract foundation is implemented and chat/Continue side-effect paths are connected.",
  "Mobile, Launcher and Pipeline consume the same preview/approval artifacts indirectly, but do not yet call OperationContractService directly in this sprint evidence.",
  "A follow-up should move approval queue/view-model adapters to read operation_contract as first-class fields."
]

## implemented
[
  "OperationContract schema with permission decisions, normalized actions, negative constraints, workspace refs and Speaker Truth requirements.",
  "OperationContractService with action aliases, negative constraint extraction and WorkspacePermissionMatrixService permission decisions.",
  "Config-driven operation_contract_policy.yaml for aliases/constraints.",
  "Chat governed_file_write now embeds operation_contract in draft/policy/contract_preview and still creates approval before write.",
  "Chat governed_shell_request now embeds operation_contract and still creates approval before shell.",
  "Continue side-effect approval drafts now include operation_contract and return it in aipinho metadata."
]

## files_changed
[
  "src/aipinho/schemas/governance/operation_contract.py",
  "src/aipinho/schemas/governance/__init__.py",
  "src/aipinho/services/governance/operation_contract_service.py",
  "src/aipinho/services/governance/__init__.py",
  "config/policies/operation_contract_policy.yaml",
  "src/aipinho/services/chat/chat_service.py",
  "src/aipinho/api/routers/continue_integration_router.py",
  "tests/unit/test_operation_contract_service.py",
  "tests/integration/test_chat_api.py",
  "tests/integration/test_continue_openai_compat_api.py"
]

## tests
[
  "python -m py_compile src\\aipinho\\services\\governance\\operation_contract_service.py src\\aipinho\\schemas\\governance\\operation_contract.py src\\aipinho\\services\\chat\\chat_service.py src\\aipinho\\api\\routers\\continue_integration_router.py -> passed",
  "python -m pytest tests\\unit\\test_operation_contract_service.py tests\\integration\\test_chat_api.py tests\\integration\\test_continue_openai_compat_api.py -q -> 47 passed in 50.47s"
]

## covered_requirements
{
  "write_files_alias_maps_to_workspace_write_policy": "covered by tests/unit/test_operation_contract_service.py",
  "read_only_negative_constraint_blocks_write": "covered",
  "chat_only_negative_constraint_blocks_artifact": "covered",
  "ask_policy_creates_approval_request": "covered by chat/Continue integration approvals",
  "denied_policy_returns_blocked_reason_code": "covered by unit operation contract test",
  "continue_route_uses_operation_contract": "covered by Continue integration assertions",
  "speaker_truth_blocks_success_without_execution": "contract includes speaker_truth_requirements and chat messages still state no execution before approval"
}

## remaining_gaps
[
  "Direct OperationContract invocation in Mobile view-model adapters.",
  "Direct OperationContract invocation in Launcher-specific endpoints/adapters if separate from chat/preview.",
  "Direct OperationContract invocation in Pipeline queue adapters; currently operation_contract is inside draft/preview payload.",
  "Canonical report/status endpoint for OperationContract inventory was not added to avoid route duplication without Sprint 23 context."
]
