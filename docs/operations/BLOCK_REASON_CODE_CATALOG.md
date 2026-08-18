# Block Reason Code Catalog

| code | category | mobile_normal_message | severity | regression_candidate |
| --- | --- | --- | --- | --- |
| path_outside_workspace | workspace | Operacao bloqueada: path_outside_workspace. | warning | False |
| path_traversal_blocked | workspace | Operacao bloqueada: path_traversal_blocked. | warning | False |
| workspace_role_forbids_write | workspace | Operacao bloqueada: workspace_role_forbids_write. | warning | False |
| workspace_role_forbids_shell | workspace | Operacao bloqueada: workspace_role_forbids_shell. | warning | False |
| source_readonly_write_denied | workspace | Operacao bloqueada: source_readonly_write_denied. | warning | False |
| forbidden_workspace | workspace | Operacao bloqueada: forbidden_workspace. | warning | False |
| workspace_resolution_failed | workspace | Operacao bloqueada: workspace_resolution_failed. | warning | False |
| capability_missing | policy_capability | Operacao bloqueada: capability_missing. | warning | False |
| action_not_available | policy_capability | Operacao bloqueada: action_not_available. | warning | False |
| policy_denied | policy_capability | Operacao bloqueada: policy_denied. | warning | False |
| risk_above_allowed_threshold | policy_capability | Operacao bloqueada: risk_above_allowed_threshold. | warning | False |
| approval_required | policy_capability | Operacao bloqueada: approval_required. | warning | False |
| approval_denied | policy_capability | Operacao bloqueada: approval_denied. | warning | False |
| approval_expired | policy_capability | Operacao bloqueada: approval_expired. | warning | False |
| approval_mismatch | policy_capability | Operacao bloqueada: approval_mismatch. | warning | False |
| preview_required | patch_write | Operacao bloqueada: preview_required. | error | False |
| preview_missing | patch_write | Operacao bloqueada: preview_missing. | error | False |
| preview_mismatch | patch_write | Operacao bloqueada: preview_mismatch. | error | False |
| apply_denied | patch_write | Operacao bloqueada: apply_denied. | error | False |
| actual_changes_mismatch | patch_write | Operacao bloqueada: actual_changes_mismatch. | error | False |
| write_envelope_invalid | patch_write | Operacao bloqueada: write_envelope_invalid. | error | False |
| shell_category_denied | shell | Operacao bloqueada: shell_category_denied. | error | False |
| destructive_shell_denied | shell | Operacao bloqueada: destructive_shell_denied. | error | False |
| git_write_denied | shell | Operacao bloqueada: git_write_denied. | error | False |
| network_shell_denied | shell | Operacao bloqueada: network_shell_denied. | error | False |
| process_control_denied | shell | Operacao bloqueada: process_control_denied. | error | False |
| unknown_shell_denied | shell | Operacao bloqueada: unknown_shell_denied. | error | False |
| shell_timeout | shell | Operacao bloqueada: shell_timeout. | error | False |
| shell_exit_failed | shell | Operacao bloqueada: shell_exit_failed. | error | False |
| artifact_output_policy_denied | artifact | Operacao bloqueada: artifact_output_policy_denied. | warning | False |
| artifact_creation_failed | artifact | Operacao bloqueada: artifact_creation_failed. | warning | False |
| artifact_packaging_failed | artifact | Operacao bloqueada: artifact_packaging_failed. | warning | False |
| artifact_registration_failed | artifact | Operacao bloqueada: artifact_registration_failed. | warning | False |
| artifact_missing_id | artifact | Operacao bloqueada: artifact_missing_id. | warning | True |
| artifact_download_unavailable | artifact | Operacao bloqueada: artifact_download_unavailable. | warning | False |
| validation_required | validation | Operacao bloqueada: validation_required. | warning | False |
| validation_not_started | validation | Operacao bloqueada: validation_not_started. | warning | False |
| validation_failed | validation | Operacao bloqueada: validation_failed. | warning | False |
| validation_evidence_missing | validation | Operacao bloqueada: validation_evidence_missing. | warning | True |
| operation_contract_invalid | runtime | Operacao bloqueada: operation_contract_invalid. | error | False |
| task_runtime_failed | runtime | Operacao bloqueada: task_runtime_failed. | error | False |
| execution_exception | runtime | Operacao bloqueada: execution_exception. | error | False |
| budget_exceeded | runtime | Operacao bloqueada: budget_exceeded. | error | False |
| unsupported_file_type | runtime | Operacao bloqueada: unsupported_file_type. | error | False |
| encoding_failed | runtime | Operacao bloqueada: encoding_failed. | error | False |
| speaker_truth_violation | speaker_mobile | Operacao bloqueada: speaker_truth_violation. | warning | True |
| mobile_state_mismatch | speaker_mobile | Operacao bloqueada: mobile_state_mismatch. | warning | False |
| endpoint_mobile_divergence | speaker_mobile | Operacao bloqueada: endpoint_mobile_divergence. | warning | True |
| raw_sanitization_required | speaker_mobile | Operacao bloqueada: raw_sanitization_required. | warning | False |
| unknown_block_reason | runtime | Operacao bloqueada: unknown_block_reason. | error | True |

Each blocked response must include a known code, human reason, technical meaning, safe alternatives and evidence fields when available. Unknown reasons must create a regression candidate.
