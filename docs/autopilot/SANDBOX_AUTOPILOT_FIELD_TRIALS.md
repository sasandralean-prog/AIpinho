# Sandbox Autopilot Field Trials

Sandbox Autopilot is a governed execution path for creative, exploratory and project-generation work inside the local sandbox.

Canonical endpoints:

- `GET /api/v1/sandbox/autopilot/status`
- `POST /api/v1/sandbox/autopilot/route`
- `POST /api/v1/sandbox/autopilot/run`

## Contract

Autopilot may execute when:

- the operation remains inside the sandbox;
- the Project Factory can provide a governed template;
- artifact export stays token-protected;
- validation and evidence refs are produced;
- no external workspace read/write is required.

Autopilot must block or stop when:

- the prompt references an unregistered external path for analysis;
- a path escape is attempted;
- network shell, destructive shell or git write would be required;
- the operation cannot classify risk safely.

## Field Trial Matrix

Recommended trials:

1. Android sandbox project generation.
2. Python CLI project generation.
3. Static Web project generation.
4. ZIP artifact integrity and token-protected download.
5. External path fallback with safe sandbox alternative.
6. Negative security checks for forbidden capabilities.

## Evidence Required

- `autopilot_run_id`
- route decision
- recommended skills
- sandbox task id
- project generation id
- validation status
- artifact id
- download endpoint
- unauthorized download behavior
- final human-safe answer

