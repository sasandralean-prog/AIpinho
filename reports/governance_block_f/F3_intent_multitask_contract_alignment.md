# F3 Intent to MultiTask to Contract Alignment

Checkpoint: F3_INTENT_MULTITASK_CONTRACT_ALIGNMENT_READY
Generated: 2026-06-28T15:44:57.208267+00:00

Mapped prompt classes: conversation_simple, planning_readonly, workspace_permission_list, project_generation, patch_request, approval_command, shell_build_test, artifact_report.

Rules enforced in the map:
- read-only planning has no write action;
- approval command has precedence over conversation;
- project generation requires project_generation runtime and approval when write_files is ask;
- shell/build/test routes through governed shell;
- artifact/report request routes through artifact_generation.
