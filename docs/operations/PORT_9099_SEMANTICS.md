# Port 9099 Semantics

Port `9099` is the monitor/supervisor control plane.

## Rules

- It is not the main backend.
- It must not restart itself.
- It may supervise/restart the core backend on configured ports.
- Mobile UI can show it as a control-plane dependency, not as the primary backend status.

## Expected UI Language

- Backend: derived from core backend health.
- Supervisor/control: derived from 9099.
- Observability: derived from dashboard/debugger consistency.
