# Governed Autopilot Mode

Sandbox operations are the preferred autorun target for creative or exploratory work. Low/medium-risk file operations, safe shell, validation and artifact export may proceed without repeated human interruption when they remain inside the sandbox.

Autopilot must stop when policy detects escape, secrets, network shell, destructive commands, unknown shell or cleanup without preview.

Sprint 27 project generation is an allowed autopilot building block when the request is for a new sandbox deliverable. Autopilot should prefer Project Factory over direct file-by-file writes for recognized project templates, then validate and export a governed artifact.

Sprint 28 adds explicit Sandbox Autopilot endpoints. The service is intentionally thin: it routes, selects recommended skills and delegates actual project creation to the Project Factory. This prevents a second executor path from bypassing sandbox policy, artifact validation or trace generation.

Use `docs/autopilot/SANDBOX_AUTOPILOT_FIELD_TRIALS.md` for the field-trial checklist.
