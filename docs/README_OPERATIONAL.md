# AIpinho Operational README

AIpinho is a local multi-agent runtime with governed execution. It exposes separate agent surfaces for AIpinho, Lucio, Codex and Gemini while sharing policy, tool, memory, artifact, dashboard and debugger contracts.

## Ports

- `9088`: core backend.
- `9089`: realtime/SSE, when enabled.
- `9098`: artifacts/download service, when enabled.
- `9099`: monitor/supervisor. This service must not restart itself.

## Main Components

- Agent Session Kernel: persistent sessions, messages, runs and events.
- Event Bus: incremental timelines with after-event cursors.
- Tool Gateway: governed tools for files, shell, validation and artifacts.
- Policy Kernel: capability, workspace, risk and autoapproval decisions.
- Delegation: parent/child run contracts between agents.
- Memory Gateway: private and shared memory boundaries.
- Dashboard and Debugger 2.0: sanitized observability.
- Self-Healing: auditable candidates and guarded actions.
- Regression Suite: local multi-agent golden/freedom/security/truth tests.

## Run Regression

```powershell
python tests\multi_agent\run_multi_agent_regression.py --quick
python tests\multi_agent\run_multi_agent_regression.py --all
```

Reports are written to `reports/regression/`.

## Security Defaults

- Provider keys stay outside mobile, launcher, reports and logs.
- Authorization headers are used for protected downloads.
- Tokens must not appear in URLs.
- Raw/debug details are hidden by default.
- Source-readonly and forbidden workspaces block writes.

