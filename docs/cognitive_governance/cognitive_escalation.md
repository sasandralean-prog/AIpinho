# Cognitive Escalation

Sprint CG3 adds governed cognitive escalation after cognitive routing.

The escalation layer does not execute inference, does not call models, and does not interpret prompts. It receives canonical ISR/contracts plus a `RoutingDecision` and returns an auditable `EscalationDecision`.

## Components

- `EscalationPolicy`: deterministic thresholds for confidence, complexity, risk, and human validation.
- `ConfidenceEvaluator`: derives bounded confidence from explicit input or canonical ISR/contracts.
- `ComplexityEstimator`: estimates complexity from structured entities, constraints, expected outputs, requested actions, approvals, validations, and artifacts.
- `CognitiveEscalationEngine`: decides whether to remain, escalate, request human validation, or block.

## Decisions

- `remain`: current route is sufficient.
- `escalate`: use an escalation model already exposed by the governed route.
- `request_human_validation`: confidence or risk requires operator validation.
- `block`: routing is blocked or risk exceeds the escalation policy.

## Invariants

- No model inference is executed.
- No model-specific rule is used.
- The engine uses capabilities, contracts, risk, confidence, complexity, and routing metadata only.
- Every decision includes reason codes and trace steps.

## Endpoints

- `POST /api/v1/runtime/cognitive/escalate`
- `GET /api/v1/runtime/cognitive/escalation-history`
