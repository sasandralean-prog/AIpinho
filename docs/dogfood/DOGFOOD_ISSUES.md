# Dogfood Issues

## Fixed During Sprint 20

### DG-001 - Shell Tool Did Not Require Workspace

- Severity: high.
- Affected config: `config/agents/tool_gateway_registry.yaml`.
- Root cause: `run_shell` had `requires_workspace: false`, allowing shell requests to be shaped without an explicit workspace.
- Fix: changed `run_shell` to require workspace.
- Why generic: shell execution should always have an auditable working directory and workspace policy context.
- Validation: governed dogfood test shell ran in `dogfood20_target_mutable` and passed.

### DG-002 - Historical Tool Block Overrode Completed Run State

- Severity: high.
- Affected service: `src/aipinho/services/agents/agent_session_kernel_service.py`.
- Root cause: session status aggregation treated any historical blocked tool event as the session latest status, even after the run completed and validation passed.
- Fix: completed/success terminal runs now prefer run-level terminal events and no longer let resolved tool-level blocks override final state.
- Why generic: a resolved or expected blocked tool event is evidence, not necessarily final run status.
- Validation: unit test `test_completed_run_is_not_overridden_by_resolved_tool_block` passed; mobile view-model now reports `completed`.

## Open Warnings

- The core dogfood was executed through the multi-agent kernel and endpoints, not through a complete mobile tap-by-tap scenario.
- Full Launcher and Mobile visual dogfood remains useful before declaring a broad public release.

