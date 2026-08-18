# G16 - Legacy Chat Services Folded

Status: G16_LEGACY_CHAT_SERVICES_FOLDED_READY

Generated UTC: 2026-06-26T10:32:19.629848+00:00

## Result

- `ChatService` is no longer public route authority for critical or residual migrated endpoints.
- `CanonicalPublicChatService.respond()` evaluates `GovernanceLifecycleService` before any legacy content provider path.
- `ChatService` remains available only through `_conversation_response()` for plain conversation content.
- `ChatOperationRouterService` and `ChatPermissionGrantService` are no longer active public-route authorities after `chat_router.py` quarantine.

## Tests

- `tests/governance/test_g16_legacy_chat_services_folded.py`

## Residual note

`ChatService` still imports internal legacy chat helpers. This is acceptable for this checkpoint because public operational routing no longer delegates final lifecycle authority to it, but a later cleanup can split a pure content provider class.

