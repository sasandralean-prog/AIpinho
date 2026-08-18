# Mobile Artifact Download

The mobile `AgentArtifactPanel` renders artifact status before showing actions.

UI behavior:

- `ready`: show human label and download button.
- `requested`, `generating`, `validating`: show progress text.
- `failed`: show sanitized failure reason.
- `blocked`: show sanitized block reason.
- `expired`, `deleted`: show unavailable state.

The mobile app must download by `artifact_id` through the backend using token headers. It must not expose raw URLs or token values in normal chat.

