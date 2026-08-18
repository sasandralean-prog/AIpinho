# Event Subscription

Each Continuous Collaboration Session stores:

- subscribed_event_types
- last_event_sequence
- observed_events

Default subscriptions:

- run_created
- run_queued
- run_waiting_input
- approval_required
- approval_preview_created
- patch_applied
- validation_completed
- artifact_created
- run_completed
- run_failed
- run_blocked
- run_cancelled

Polling is fallback-compatible and event-aware. No aggressive background polling loop was introduced in Sprint J.

