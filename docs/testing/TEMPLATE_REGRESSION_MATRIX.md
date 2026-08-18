# Template Regression Matrix

Sprint 31 added:

- `tests/templates/test_template_registry_execution.py`
- `tests/fixtures/templates/*`
- multi-agent runner flag `--templates`

Covered behaviors:

- registry loads the required catalog
- active invalid manifests are rejected
- template endpoints expose sanitized registry data
- Project Factory generates FastAPI from the catalog
- Project Factory generates docs pack from the catalog
- artifact download endpoints do not include tokens
- generated zips include `PROJECT_MANIFEST.json`

Recommended focused command:

`python -m pytest tests\project_factory tests\templates -q --durations=10`
