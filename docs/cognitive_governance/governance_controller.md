# Cognitive Governance Controller

Sprint CG4 introduces the central controller for cognitive governance.

The controller is the governed authority that combines semantic inputs, cognitive policy, routing, escalation, evidence, and audit into a single decision. It does not execute inference and does not call models.

## Flow

1. Receive canonical ISR and Runtime contracts.
2. Evaluate cognitive policy.
3. Resolve role, capability, and model route.
4. Evaluate cognitive escalation.
5. Produce a `GovernanceDecision`.
6. Persist the decision in governance history.

## Schemas

- `CognitiveGovernanceRequest`
- `GovernanceDecision`
- `GovernanceSession`
- `GovernanceEvidence`
- `GovernanceAudit`
- `CognitiveGovernanceHistory`

## Decision Rules

- Any blocked policy, route, or escalation blocks the governance decision.
- Any pending approval, supervisor, Runtime Doctor, or human validation requirement yields `requires_approval`.
- Only a fully satisfied route returns `allowed`.

## Endpoints

- `GET /api/v1/runtime/cognitive/governance`
- `POST /api/v1/runtime/cognitive/governance/evaluate`
- `GET /api/v1/runtime/cognitive/governance/history`

## Invariants

- No inference is executed.
- No prompt is interpreted by the controller.
- Every decision contains route, policy, escalation, session, evidence, audit, and reason codes.
- Future executors must consume the governance decision before cognitive inference.
