# Final Multi-Agent Architecture

AIpinho RC1 is organized around governed agents rather than unrestricted provider calls.

```mermaid
flowchart TD
  U["User"] --> A["Agent Session Kernel"]
  A --> I["Intent / Operation Contract"]
  I --> P["Policy Kernel + AutoApproval"]
  P --> T["Tool Gateway"]
  P --> D["Delegation Service"]
  T --> V["Validation Gate"]
  D --> V
  V --> S["Speaker Truth / Final Message"]
  A --> E["Event Bus / Timeline"]
  E --> M["Dashboard + Debugger 2.0"]
  E --> H["Self-Healing"]
  E --> R["Regression Evidence"]
```

## Agents

- AIpinho: local primary agent.
- Lucio: multimodal and strategic routing agent.
- Codex: technical executor through governed contracts.
- Gemini: cloud agent with governed delegation and tool boundaries.

## Release Status

- Backend multi-agent kernel: ready with warnings.
- Mobile/Launcher surfaces: implemented, but visual QA must remain part of every release pass.
- Provider integrations: available through separated contracts; real provider smoke is not part of the normal automated suite.

