# AIpinho Operational Contract Inventory

Generated: 2026-06-11T13:07:38

This inventory is the operational constitution for governed AIpinho flows before Fire Test 3.

## Principles

- Chat is human and sanitized.
- Debugger/details expose technical evidence.
- Raw is hidden by default and copied only as sanitized raw.
- Artifact output is not workspace write.
- Patch/write/shell side effects require governed flow, approval when required, audit and validation.
- Blocked states are not healthy/safe success states.
- Completed states require evidence appropriate to the operation.

## Operation Types

| operation_type | task | read | write | shell | artifact | approval | validation | mobile |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| simple_chat | False | False | False | False | False | False | False | User message plus AIpinho answer only. |
| simple_conversation | False | False | False | False | False | False | False | Runtime alias for simple chat conversation. |
| artifact_request | False | False | False | False | True | False | True | Answer plus artifact download actions. |
| readonly_analysis | True | True | False | False | False | False | True | Human summary or explicit blocked state. |
| readonly_analysis_with_artifact_output | True | True | False | False | True | False | True | Summary plus artifact downloads. |
| patch_preview | True | True | False | False | False | False | True | Patch preview and approval explanation. |
| patch_apply | True | True | True | False | False | True | True | Applied/failed/blocked state with validation. |
| shell_command | True | True | False | True | False | True | True | Sanitized command status; details in debugger. |

## Workspace Roles

| role | read | write | patch | shell | artifact_source | artifact_target | approval |
| --- | --- | --- | --- | --- | --- | --- | --- |
| source_readonly | True | False | False | False | True | False | False |
| target_mutable | True | True | True | True | True | True | True |
| system_mutable | True | True | True | True | True | True | True |
| protected | True | False | False | False | True | False | True |
| forbidden | False | False | False | False | False | False | True |

## Capabilities And Actions

| capability | action | preconditions | roles | preview | approval | validation | risk |
| --- | --- | --- | --- | --- | --- | --- | --- |
| chat | answer_message | none | any | False | False | False | low |
| read_workspace | scan_workspace | registered readable workspace plus budget | source_readonly,target_mutable,system_mutable,protected | False | False | True | medium |
| artifact | create_artifact | artifact store policy allows output | artifact_store | False | False | True | low |
| artifact | package_artifact_zip | artifact_id exists and zip policy allows format | artifact_store | False | False | True | low |
| patch | create_preview | mutable target workspace | target_mutable,system_mutable | True | False | True | medium |
| patch | apply_patch | preview plus matching approval | target_mutable,system_mutable | True | True | True | high |
| workspace_write | write_file | preview plus approval plus validation | target_mutable,system_mutable | True | True | True | high |
| shell | run_command | allowlisted executable, workspace, timeout, approval | target_mutable,system_mutable | True | True | True | medium-high |
| validation | validate_result | operation requires validation | any | False | False | False | low |

## Patch Lifecycle States

preview_created, needs_approval, approved, apply_started, apply_finished, post_validation_passed, post_validation_failed, completed, failed, blocked

## Shell Categories

readonly_shell, git_read_shell, test_shell, build_shell, package_shell, network_shell, process_control_shell, write_shell, destructive_shell, unknown_shell

## Validation Gates

| validation_id | operation_types | pass_criteria |
| --- | --- | --- |
| file_exists | artifact_write, patch_apply | Path exists when required. |
| directory_exists | readonly_analysis, shell_command | Source directory exists. |
| artifact_registered | artifact_request, readonly_analysis_with_artifact_output | Artifact registry contains artifact_id. |
| artifact_downloadable | artifact_download | Download endpoint available and token required. |
| zip_contains_expected_file | artifact_request, readonly_analysis_with_artifact_output | Zip includes requested logical file. |
| diff_matches_preview | patch_apply | Applied diff matches preview. |
| no_write_to_source | readonly_analysis_with_artifact_output | Read-only source was not mutated. |
| no_secret_leak | all | Output and raw are sanitized. |
| py_compile | patch_apply | Changed Python files compile when applicable. |
| unit_tests | patch_apply, shell_test_or_build | Focused tests pass when applicable. |
| android_unit_tests | patch_apply | Android tests pass when Android changed. |
| assemble_debug | patch_apply | APK build passes when Android app changed. |
| shell_exit_code | shell_command | Command exits as expected. |
| report_contains_required_sections | readonly_analysis_with_artifact_output | Report has required sections. |
| event_trace_exists | all | Traceable events exist. |
| mobile_viewmodel_matches_endpoint | all_mobile | Mobile state matches endpoint state. |
| task_state_consistent | task | Task lifecycle is coherent. |

## Artifact Lifecycle

artifact_requested, artifact_content_created, artifact_packaged, artifact_registered, artifact_validated, artifact_link_created, artifact_download_requested, artifact_download_completed, artifact_download_failed

## Event Contracts

Every operational event should include event_id, source_service, status, severity, human_summary, technical_summary, visibility, copy_policy and created_at.

## Mobile ViewModel States

| state | normal | details | actions |
| --- | --- | --- | --- |
| idle | human status | ids, policy, evidence and trace when available | download if artifact_id exists |
| running | human status | ids, policy, evidence and trace when available | download if artifact_id exists |
| pending_approval | human status | ids, policy, evidence and trace when available | approve/cancel |
| pending_validation | human status | ids, policy, evidence and trace when available | download if artifact_id exists |
| validating | human status | ids, policy, evidence and trace when available | download if artifact_id exists |
| completed | human status | ids, policy, evidence and trace when available | download if artifact_id exists |
| completed_with_warnings | human status | ids, policy, evidence and trace when available | download if artifact_id exists |
| degraded | human status | ids, policy, evidence and trace when available | download if artifact_id exists |
| blocked | human blocked reason | ids, policy, evidence and trace when available | download if artifact_id exists |
| failed | human status | ids, policy, evidence and trace when available | download if artifact_id exists |
| validation_failed | human status | ids, policy, evidence and trace when available | download if artifact_id exists |

## Regression Candidate Triggers

- operation blocked without code
- source_readonly write allowed
- artifact output confused with workspace write
- approval required but blocked
- validation failed but completed
- speaker truth violation
- mobile endpoint divergence
- raw/token leaked
- shell dangerous allowed
- event trace missing
- artifact id missing after creation
- stale task reused
- unknown block reason
