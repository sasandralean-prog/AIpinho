# Multi-Agent Regression Suite

This suite protects the AIpinho multi-agent runtime after the Agent Session Kernel, Event Bus, Tool Gateway, Policy Kernel, Delegation, Memory Gateway, Dashboard, Debugger 2.0 and Governed Self-Healing layers.

The suite is intentionally contract-first:

- Normal test runs use fakes and temporary workspaces.
- No real provider key is required.
- No real user workspace is mutated.
- Raw/debug payloads are expected to stay hidden by default.
- Secrets and tokens must be redacted from public outputs.
- Security blocks must not disable safe productive work.

## Run

```powershell
python tests\multi_agent\run_multi_agent_regression.py --quick
python tests\multi_agent\run_multi_agent_regression.py --all
```

Reports are written to `reports/regression/` as `.md` and `.json`.

