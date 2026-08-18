# Lucio Route Decision Model

Routing is configured in `config/agents/lucio_agent_policy.yaml`.

## Priority

1. Explicit operation type.
2. Requested capabilities.
3. Configured semantic concept markers.
4. Workspace context.
5. Direct strategic response fallback.

## Routes

### Direct Response

Used for conversation, strategy, architecture, product, and multimodal review
that does not require local side effects.

### Codex

Used for coding, code review, refactor, build, test, validation, and governed
technical execution.

### AIpinho

Used for local workspace reads, reports, artifacts, and local operations.

## Design Constraints

- No route depends on a sprint id, task id, user, project name, exact prompt,
  IP address, or fixed workspace path.
- Concept markers are data in policy configuration rather than branches in the
  service.
- Attachments remain evidence sources unless an operation or capability
  explicitly requires delegated local handling.
- Route decisions are observable through `lucio_route_decided` events.
