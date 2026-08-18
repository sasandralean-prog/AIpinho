# Sprint I Tests

Tests added:

- `tests/unit/test_external_collaboration_layer.py`

Covered:

- Success Contract creation.
- External Task creation with TaskRun and Universal Task Session.
- External Review registration without execution authority.
- Gemini adapter human and machine outputs.
- External routes do not create model-specific paths.
- New external service/router do not branch on `provider == ...` or `adapter_id == ...`.

Validation commands:

- `python -m py_compile src/aipinho/schemas/external_collaboration.py src/aipinho/services/external_collaboration_store.py src/aipinho/services/external_adapter_registry.py src/aipinho/services/external_collaboration_service.py src/aipinho/api/routers/external_collaboration_router.py tests/unit/test_external_collaboration_layer.py`
- `python -m pytest tests/unit/test_external_collaboration_layer.py -q`
- `python -m pytest tests/unit/test_external_collaboration_layer.py tests/unit/test_universal_task_session_service.py tests/unit/test_universal_task_session_router.py -q`

Results:

- Sprint I tests: 6 passed.
- Sprint I + Sprint H dependency tests: 16 passed.

