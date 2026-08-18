# Project Profiles

Project Profiles are governed context records for real projects. They describe project stack, workspaces, commands, validation and namespaces so AIpinho, Lúcio, Codex and Gemini can understand a project without hardcoded path rules.

Profiles do not grant permissions. Tool Gateway, Policy Kernel, Workspace Registry and Approval remain the source of permission truth.

Core flow:

1. Detect project markers read-only.
2. Create a proposed profile.
3. Save profile only after secret scan.
4. Select profile for a session or globally.
5. Pass `project_profile_id` through agent runs, delegations, tools, artifacts and memory candidates.
6. Validate profile health before operational use.

Official endpoints:

- `GET /api/v1/projects/profiles`
- `GET /api/v1/projects/profiles/{project_id}`
- `POST /api/v1/projects/profiles/detect`
- `POST /api/v1/projects/profiles`
- `PATCH /api/v1/projects/profiles/{project_id}`
- `POST /api/v1/projects/profiles/{project_id}/validate`
- `POST /api/v1/projects/profiles/{project_id}/archive`
- `POST /api/v1/projects/profiles/{project_id}/select`
- `GET /api/v1/projects/profiles/{project_id}/commands`
- `GET /api/v1/projects/profiles/{project_id}/workspaces`
- `GET /api/v1/projects/profiles/{project_id}/health`
- `GET /api/v1/mobile/view-model/projects`

