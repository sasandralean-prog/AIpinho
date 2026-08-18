# Artifact Library Regression Matrix

Sprint 32 tests:

- `tests/artifact_library/test_artifact_library_service.py`

Covered:

- index creation;
- query by session;
- ready requires existing file;
- missing file not ready;
- markdown preview sanitized;
- zip listing;
- zip traversal detection;
- binary metadata-only preview;
- use-as-context text allowed;
- use-as-context binary denied;
- bundle manifest;
- cleanup preserves evidence;
- mobile view-model;
- download requires Authorization header.

Focused command:

`python -m pytest tests\artifact_library -q --durations=10`
