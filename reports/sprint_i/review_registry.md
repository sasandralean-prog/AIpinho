# Review Registry

Implemented by:

- `ExternalCollaborationStore`
- `ExternalCollaborationService.receive_review`

Registry storage:

- `data/external_collaboration/reviews/*.json`

Guarantees:

- Reviews are separate from internal chat.
- Reviews do not replace internal reviewers.
- Reviews do not execute actions.
- Reviews preserve provider, contract version, related task run and confidence.
- Sensitive fields are sanitized before persistence.

