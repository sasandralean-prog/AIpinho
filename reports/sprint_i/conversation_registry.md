# External Conversation Registry

Implemented by:

- `ExternalConversationRecord`
- `/api/v1/external/conversations`

Registry storage:

- `data/external_collaboration/conversations/*.json`

Guarantees:

- External conversations are separate from internal chat.
- Each record can link to a provider session, external task and external review.
- No conversation grants runtime authority.

