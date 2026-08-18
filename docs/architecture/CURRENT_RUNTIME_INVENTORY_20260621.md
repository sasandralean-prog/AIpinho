# Current Runtime Inventory - 2026-06-21

This timestamped inventory preserves the historical document and records the current revalidation baseline.

- App creation: `src/aipinho/app_factory.py` and `src/aipinho/api/routers/__init__.py`.
- Primary chat: `/api/v1/chat` through `ChatService`.
- Execution: `TaskRuntimeService`, `SupervisedExecutionLoop`, runtime profiles, Policy Kernel, governed tools, approvals, validation, and artifacts.
- Patch preview: `PatchPlanningService`; model-assisted planning remains read-only and preview-only in `ModelAssistedPatchPlannerService`.
- Multi-agent session kernel: profile registry, session store, event bus, state aggregation, and generic `/api/v1/agents` endpoints.
- Presentation: Mobile and Launcher use separate clients/view models; raw is hidden in normal mode.

This is an inventory, not a second runtime. New work must compose these owners rather than create parallel execution paths.
