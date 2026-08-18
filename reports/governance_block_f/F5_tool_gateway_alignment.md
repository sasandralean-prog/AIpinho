# F5 Tool Gateway Alignment

Checkpoint: F5_TOOL_GATEWAY_ALIGNMENT_READY
Generated: 2026-06-28T15:44:57.208267+00:00

Mapped tools: file_read, file_list, file_write, create_directory, patch_apply, shell_command, artifact_register, approval_create, model_inference, browser_localhost_qa.

Side-effect tools have policy_action and approval_scope when ask. The F9 write went through project_generation_plan_executor after ApprovalRequest, not through direct unapproved file write.
