# Sprint I Contracts

Contracts implemented:

- `SuccessContract`
- `ExternalTaskContract`
- `ExternalReviewContract`
- `ExternalConversationRecord`
- `ExternalAdapterOutput`

Success Contract fields:

- objective
- acceptance_criteria
- forbidden
- required_evidence
- completion_definition
- priority

External Review Contract fields:

- review_id
- provider
- contract_version
- task_run_id
- external_task_id
- conversation_id
- received_at
- status
- confidence
- findings
- recommendations
- missing_evidence
- next_action
- authority_decision
- may_execute
- replaces_internal_reviewer

External Task Contract fields:

- external_task_id
- provider
- objective
- context
- expected_output
- constraints
- deadline
- success_contract_id
- conversation_id
- related_task_run_id

