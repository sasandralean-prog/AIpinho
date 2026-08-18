# AIpinho PinhoForge Hardware Profiler Provider

## Purpose

Expose a governed, read-only environment profile through the AIpinho Tool Gateway.

## Tool Gateway tools

- `pinhoforge_hardware_profile_get`
- `pinhoforge_tool_availability_get`
- `pinhoforge_readiness_summary_get`
- `pinhoforge_environment_report_export`

## Guarantees

- No install flow
- No environment repair flow
- No PATH mutation
- No arbitrary diagnostic command execution
- Redaction enabled by default

## Outputs

- Readiness categories for Android, conversion, media and development
- Tool availability statuses
- Optional exported Markdown and JSON report as governed artifacts

## Notes

- Missing tools are treated as `missing` or `degraded`, not as fatal provider failure.
- Exported reports are registered through the Artifact system with token-protected download endpoints.

