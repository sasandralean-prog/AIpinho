# External Review Loop

Implemented:

- Continuous session can receive SuccessEvaluation contracts.
- Adapter output can be transformed into SuccessEvaluation.
- AIpinho stores the evaluation and decides next state.

Endpoints:

- `POST /api/v1/external/collaboration-sessions/{session_id}/evaluations`
- `GET /api/v1/external/collaboration-sessions/{session_id}/evaluations`
- `POST /api/v1/external/collaboration-sessions/{session_id}/adapters/{adapter_id}/success-evaluation`

No external recommendation executes automatically.

