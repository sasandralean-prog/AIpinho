# Artifact Library

Artifact Library is the canonical operational index for AIpinho artifacts.

It aggregates:

- historical chat artifact records;
- Tool Gateway artifacts;
- sandbox/project-factory exports;
- template output artifacts;
- future skill, autopilot, promotion, validation and debugger artifacts.

Main endpoints:

- `GET /api/v1/artifact-library/health`
- `GET /api/v1/artifact-library`
- `POST /api/v1/artifact-library/query`
- `POST /api/v1/artifact-library/reindex`
- `POST /api/v1/artifact-library/{artifact_id}/preview`
- `POST /api/v1/artifact-library/{artifact_id}/use-as-context`
- `POST /api/v1/artifact-library/bundles`
- `POST /api/v1/artifact-library/cleanup/preview`
- `GET /api/v1/mobile/view-model/artifact-library`

Download remains token-protected through:

`GET /api/v1/artifacts/{artifact_id}/download`

Tokens are never embedded in URLs.
