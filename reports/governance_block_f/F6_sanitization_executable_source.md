# F6 Sanitization and Executable Source

Checkpoint: F6_SANITIZATION_EXECUTABLE_SOURCE_READY
Generated: 2026-06-28T15:44:57.208267+00:00

Rule:
- TaskRun/ViewModel/debug can be sanitized.
- TaskDraft/executable plan store is the execution source.
- Executor blocks `[omitted_by_task_run_store]` when no full draft plan is available.

Evidence:
- tests added for no_executor_reads_sanitized_taskrun_content, omitted_placeholder_never_written, taskdraft_is_executable_source_for_project_generation and taskrun_is_safe_display_source_only.
- F9 had sanitized TaskRun display content but completed by reading the draft store.
