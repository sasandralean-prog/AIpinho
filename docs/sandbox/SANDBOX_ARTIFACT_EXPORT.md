# Sandbox Artifact Export

Sandbox content can be packaged as ZIP through `POST /api/v1/sandbox/artifacts/export`.

The exporter:
1. resolves every included path inside the sandbox;
2. applies exclusion globs;
3. checks the configured size limit;
4. registers bytes in the shared Tool Gateway artifact store;
5. returns an `artifact_id` and authenticated download endpoint.

Tokens never appear in URLs. Exports invoked through Tool Gateway are attached to the tool invocation contract.
