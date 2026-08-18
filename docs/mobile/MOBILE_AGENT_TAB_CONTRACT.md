# Mobile Agent Tab Contract

## Shared fields

- `agent_id`
- `display_name`
- `route_prefix`
- `operation_type`
- `provider_label`
- `supports_workspace`
- `supports_plan`
- `supports_preview`
- `supports_route_preview`
- `external_provider_notice`

## Endpoint contract

Each tab consumes its own agent namespace for health, config, sessions,
messages, send, view-model and run cancellation.

The shared artifact gateway is used for governed attachments. Tokens remain in
the authorization header and never appear in download URLs or rendered text.

## Degraded behavior

If a view-model is unavailable, the screen falls back to the agent message
endpoint. This fallback is visible as reduced detail and does not fabricate
events, active runs or provider state.

