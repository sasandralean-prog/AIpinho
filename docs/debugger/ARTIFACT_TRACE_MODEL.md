# Artifact Trace Model

Artifact-producing operations should emit enough evidence for Debugger 2.0 and reports to answer:

- which task created the artifact;
- which project generation produced it;
- which validation approved or warned on it;
- which sandbox task owns the source files;
- whether the artifact is ready, failed, blocked or expired;
- where the authenticated download endpoint is.

Canonical evidence refs:

- `sandbox_task:<id>`
- `run:<id>`
- `tool:<id>`
- `sandbox_validation:<id>`
- `artifact:<id>`

Raw payload remains hidden by default.

