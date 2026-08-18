# Semantic Interpreter

Sprint SR2 adds a parallel semantic interpreter role.

The semantic interpreter produces an Intermediate Semantic Representation (ISR)
from natural language. It does not create operation contracts, task drafts,
approvals, tool calls, skills, file writes, patches, or runtime executions.

## Role

`semantic_interpreter`

The role is configured as a normal AIpinho role, but its permissions are closed:

- no tools
- no skills
- no writes
- no patches
- no approvals
- no runtime execution

## Capability

All interpretation is gated through the Capability Registry using:

`semantic_understanding`

## Feature Flag

The feature flag is:

`semantic_runtime.semantic_runtime_enabled`

in:

`config/semantic_runtime/semantic_interpreter.yaml`

## Output

The output is `SemanticInterpreterOutput`, containing:

- intent
- scope
- entities
- constraints
- requested outputs
- confidence
- ambiguity score
- reasoning summary

## Compatibility

The existing IntentMap remains the Runtime input. SR2 only produces a parallel
ISR and does not replace routing, policy, planning, approval, or execution.
