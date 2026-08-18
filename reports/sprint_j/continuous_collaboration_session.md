# Continuous Collaboration Session

Implemented contract:

- `ContinuousCollaborationSession`

Fields:

- session_id
- provider
- external_conversation_id
- task_run_id
- success_contract_id
- review_iteration
- status
- started_at
- last_activity
- expires_at
- success_runtime
- retry_state
- subscribed_event_types
- last_event_sequence
- observed_events
- memory

Service:

- `ExternalCollaborationService.start_continuous_session`

Endpoints:

- `POST /api/v1/external/collaboration-sessions`
- `GET /api/v1/external/collaboration-sessions`
- `GET /api/v1/external/collaboration-sessions/{session_id}`

