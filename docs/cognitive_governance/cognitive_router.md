# Cognitive Router

The Cognitive Router decides which role may use which model for a cognitive capability.

It does not execute models, generate responses, or interpret prompts.

## Components

- `CognitiveRouter`
- `CapabilityResolver`
- `ModelSelector`
- `EscalationResolver`
- `RoutingDecision`

## Inputs

- ISR metadata;
- Runtime contracts;
- role id;
- capability;
- cognitive policy context.

## Output

`RoutingDecision` containing:

- selected model;
- allowed role;
- supervisor requirement;
- approval requirement;
- escalation availability;
- reason codes.

## Safety

The router only decides routes.

It never:

- executes inference;
- calls models;
- generates responses;
- interprets prompts.

## Endpoints

- `POST /api/v1/runtime/cognitive/router`
- `GET /api/v1/runtime/cognitive/routes`
