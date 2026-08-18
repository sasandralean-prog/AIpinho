# Success Contract Runtime

Implemented contract:

- `SuccessContractRuntime`

Fields:

- goal
- definition_of_done
- acceptance_criteria
- blocking_conditions
- non_blocking_conditions
- required_evidence
- maximum_iterations
- current_iteration
- status

Behavior:

- Derived from an existing Sprint I SuccessContract when available.
- Falls back to a generic governed goal tied to the TaskRun.
- Does not execute tasks or override AIpinho validation.

