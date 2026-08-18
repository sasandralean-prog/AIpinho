# External Agent Interface

Implemented files:

- `src/aipinho/schemas/external_collaboration.py`
- `src/aipinho/services/external_collaboration_store.py`
- `src/aipinho/services/external_collaboration_service.py`
- `src/aipinho/services/external_adapter_registry.py`
- `src/aipinho/api/routers/external_collaboration_router.py`

Public endpoint root:

- `/api/v1/external`

Authority rule:

- External providers can submit contracts and reviews.
- AIpinho remains the only execution, approval, validation and runtime authority.
- External reviews are stored for interpretation and never auto-executed.

Runtime admission:

- External tasks can create a governed TaskRun using existing `TaskRuntimeService`.
- The created TaskRun is tracked through Sprint H Universal Task Session.
- External clients receive `task_run_id` and poll public universal endpoints.

