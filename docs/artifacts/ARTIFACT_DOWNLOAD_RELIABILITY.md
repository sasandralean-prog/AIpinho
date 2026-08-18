# Artifact Download Reliability

The reliable download contract is:

1. Create content.
2. Package content.
3. Register artifact with metadata.
4. Mark status as `ready` only after registration succeeds.
5. Return `artifact_id`, `filename`, `download_endpoint`, `requires_token=true` and optional size.
6. Require Authorization Bearer for download.

If generation fails, the system must return `failed` or `blocked` with a human-safe reason. It must not render a false download button.

Unauthorized download attempts are expected to return `401` with `authorization_bearer_required`.

Artifact ZIP export excludes generated caches and local dependency/build directories such as `__pycache__`, `.pyc`, `.gradle`, `build`, `node_modules` and `dist`. Validation may create temporary build/cache files, but final artifacts should contain source deliverables and manifests only.
