# RC3 Fix Plan

## Purpose

Track the non-blocking follow-ups left after Sprint 20 dogfood.

Sprint 20 passed the controlled backend/kernel dogfood with warnings. RC3 should focus on proving the same flow through user-facing surfaces and real providers, not on broad architecture changes.

## Follow-Ups

### RC3-001 - Full Mobile Dogfood

- Run the Sprint 20 dogfood flow from the mobile UI.
- Confirm chat/timeline, pipeline state, artifact cards and download behavior.
- Confirm source-readonly write denial is shown as safety evidence, not as final failure after completion.

### RC3-002 - Full Launcher Dogfood

- Run the same dogfood flow from the Launcher.
- Confirm the agent cockpit, timeline, artifact panel and final status agree with endpoints.

### RC3-003 - Real Provider Smoke

- Run a small real-provider smoke for enabled external providers.
- Keep secrets outside logs, reports, raw payloads and frontend bundles.
- Do not include provider calls in the normal automated test suite.

## Acceptance

- Mobile and Launcher both show completed/safe state for a completed validated run.
- Artifacts are downloadable with token-protected endpoints.
- Real provider smoke is documented separately from normal regression.
- No project-specific or prompt-specific workaround is introduced.

