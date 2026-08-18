# Continuous Polling Engine

Implemented by:

- `ExternalCollaborationService.poll_continuous_session`

Source of truth:

- `UniversalTaskSessionService`

The polling engine observes:

- Universal task summary.
- Universal task session.
- Universal task events after the last observed sequence.

It does not read executor internals and does not inspect private runtime stores directly.

Endpoint:

- `POST /api/v1/external/collaboration-sessions/{session_id}/poll`

