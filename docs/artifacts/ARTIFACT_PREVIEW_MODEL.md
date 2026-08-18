# Artifact Preview Model

Preview modes:

- `metadata_only`
- `text`
- `markdown`
- `json`
- `image`
- `zip_listing`
- `manifest`
- `safe_summary`

Rules:

- text/markdown/json previews are sanitized;
- fake or real secrets are redacted;
- zip preview lists entries and detects path traversal;
- binary preview is metadata-only;
- preview never executes files.
