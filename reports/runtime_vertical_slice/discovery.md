# Runtime Vertical Slice Discovery

Date: 2026-07-05

## Scope

Audited the path for read-only workspace analysis requests that must still execute as governed runtime tasks when artifacts are explicitly requested.

## Findings

- `CanonicalPublicChatService` routed `workspace_analysis_readonly` directly to chat-only responses.
- `GovernanceLifecycleService` hard-overrode all read-only intents by clearing actions, target paths, executable plan refs and expected outputs.
- `PublicRouteLifecycleService` only recognized generic `artifact_result` and `validation_result`, not logical artifact outputs requested by the operator.
- TaskRun persistence, UniversalArtifactRegistry and lifecycle validation already existed and could be reused without adding provider-specific routes.

## Relevant Files

- `src/aipinho/services/governance/lifecycle/canonical_public_chat_service.py`
- `src/aipinho/services/governance/lifecycle/governance_lifecycle_service.py`
- `src/aipinho/services/governance/lifecycle/public_route_lifecycle_service.py`
- `src/aipinho/services/governance/runtime/canonical_runtime_service.py`
- `src/aipinho/services/governance/intent/canonical_intent_router.py`
- `src/aipinho/services/runtime/task_runtime_service.py`
- `src/aipinho/services/artifacts/universal_artifact_registry_service.py`

## Checkpoint

DISCOVERY_READY
