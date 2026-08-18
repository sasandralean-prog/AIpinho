# AIpinho PinhoForge Governed Terminal Provider

## Purpose

AIpinho exposes a governed terminal bridge with preview, execute, cancel, and session status operations while keeping shell behavior auditable and bounded.

## Tool Gateway surface

- pinhoforge_terminal_preview
- pinhoforge_terminal_execute
- pinhoforge_terminal_cancel
- pinhoforge_terminal_status

## Governance model

- preview required before execute
- cwd must exist
- source scope must be explicit
- risk is classified before execution
- medium and high risk can require approval
- readonly scope blocks write-like commands
- secrets are redacted from command line and output
- timeout and output limits are enforced
- reports and validated output files can be registered as artifacts

## Current limitations

- In-process preview/session state is shared inside the AIpinho runtime
- No free shell path exists outside the bridge
- Dangerous categories remain blocked by design
