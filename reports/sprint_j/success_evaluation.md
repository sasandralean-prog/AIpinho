# Success Evaluation

Implemented contracts:

- `SuccessEvaluationCreateRequest`
- `SuccessEvaluation`

Fields:

- status
- acceptance_score
- blocking_findings
- recommendations
- confidence
- needs_retry
- ready
- needs_human
- next_action

Important:

- SuccessEvaluation is not an external review.
- It is stored separately in `data/external_collaboration/success_evaluations`.
- It never grants authority to execute.

