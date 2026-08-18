# Mobile Agent Artifact Flow

Mobile agent tabs may attach text documents through the shared governed agent
artifact endpoint.

Flow:

1. user selects a document;
2. Android reads the text through the content resolver;
3. backend registers the artifact under the selected agent session;
4. the returned `artifact_id` is attached to the next request as evidence;
5. provider-specific routing decides how the evidence may be used.

Binary attachment streaming is not part of Sprint 10. Unsupported content must
not be silently converted or represented as successfully uploaded.

## Universal artifact panel

Sprint 19 adds a shared `AgentArtifactPanel` for Gemini, Lucio and Codex agent
tabs. The panel has two responsibilities:

- show input attachments that will be sent as evidence with the next prompt;
- show generated artifacts returned by the selected agent session.

Generated artifact buttons call the canonical artifact client with bearer-token
authorization in the request header. Tokens are never embedded in the download
URL. The panel accepts canonical download endpoints when the backend provides
them, but rejects absolute URLs and query-string token patterns.

If an artifact lacks `artifact_id`, the UI must not render a fake download
button. It may show a degraded human status in details/debug mode.
