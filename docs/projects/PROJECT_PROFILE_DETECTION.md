# Project Profile Detection

Project detection is read-only and marker-based.

Current generic markers:

- Android/Gradle: `build.gradle`, `settings.gradle`, `gradlew`, `gradlew.bat`.
- Python: `pyproject.toml`, `requirements.txt`, `setup.py`, `pytest.ini`.
- Node: `package.json`, `tsconfig.json`, npm/yarn/pnpm lock files.

Detection output:

- `candidate`
- `proposed_profile`
- confidence;
- risks;
- missing info;
- evidence refs.

Secret handling:

- detector may scan small known config files for secret risk;
- it records only `secret_risk_detected`;
- it must not persist the secret value.

