# Cognitive Policy Engine

The Cognitive Policy Engine governs whether cognitive inference may occur.

It never executes inference and never calls models directly.

## Components

- `CognitivePolicyEngine`
- `CognitivePolicy`
- `CapabilityPolicy`
- `InferencePolicy`
- `ReasoningPolicy`
- `ModelPolicy`
- `RiskPolicy`

## Policy Fields

Each policy contains:

- id;
- name;
- scope;
- capability;
- allowed models;
- forbidden models;
- max risk;
- max cost;
- max latency;
- approval requirement;
- supervisor requirement;
- Runtime Doctor requirement.

## Endpoints

- `GET /api/v1/runtime/cognitive/policies`
- `GET /api/v1/runtime/cognitive/policies/{id}`
- `POST /api/v1/runtime/cognitive/evaluate`

## Decision Only

The engine returns deterministic decisions:

- `allowed`
- `requires_approval`
- `blocked`

It does not invoke models.
