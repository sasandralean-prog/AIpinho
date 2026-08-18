# Project Factory Regression Matrix

Sprint 27 introduced a focused `project_factory` regression profile.

Command:

```powershell
python tests\multi_agent\run_multi_agent_regression.py --project-factory
```

Coverage:

- route classification;
- explicit project-name extraction;
- Android Kotlin project generation;
- Python CLI/simple app generation;
- static web generation;
- external path fallback;
- artifact ZIP validation;
- token-protected download metadata.

Manual smoke:

1. Restart backend.
2. POST to `/api/v1/sandbox/project-factory/generate`.
3. Confirm `status` is `completed` or `completed_with_warnings`.
4. Confirm `zip_artifact_id` is present.
5. Confirm unauthorized download returns `401`.
6. Inspect ZIP entries and `sandbox_manifest.json`.

Related Sprint 28 autopilot profile:

```powershell
python tests\multi_agent\run_multi_agent_regression.py --autopilot
```

