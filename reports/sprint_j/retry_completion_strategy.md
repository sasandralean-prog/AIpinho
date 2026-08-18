# Retry and Completion Strategy

Retry states:

- Continue
- Retry
- Needs Human
- Needs Approval
- Completed
- Cancelled
- Expired

Rules:

- Retry never exceeds `maximum_iterations`.
- If maximum iterations are reached, strategy becomes `Needs Human`.
- Waiting approval in Universal Task Session maps to `Needs Approval`.

Completion requires all three:

- `SuccessEvaluation.ready == true`
- AIpinho validation reports safe success.
- Speaker Truth/result state reports safe success.

Gemini or any external model cannot complete a task alone.

