# Mobile Multi-Agent UI

The Android application exposes four independent agent surfaces:

1. AIpinho
2. Lucio
3. Codex
4. Gemini

Each surface keeps its own session namespace, selected session, history, endpoint
contract, active run and event cursor. The UI never merges provider histories.

The shared agent screen is presentation-only. Policy, capability, approval,
delegation and execution decisions remain backend-owned.

## Session lifecycle

Each agent tab supports:

- list sessions;
- create session;
- open session;
- rename session;
- delete session and its history;
- persist the selected session locally;
- reload the selected session after activity recreation.

Session dialogs use the neon cyberpunk theme and do not expose tokens, provider
keys or raw payloads.

## Timeline

Agent timelines are vertically scrollable and text-selectable. They scroll to
the latest message on initial load and when the user is already at the bottom.
Manual reading above the bottom is preserved during polling.

Normal mode shows human messages. Details mode adds sanitized events. Raw mode
requires an explicit confirmation and remains sanitized.

## Sprint 19 layout contract

The root activity must not wrap all screens in a single global `ScrollView`.
Each screen owns its own `MobileScreenScaffold`, starts at the top when opened,
and leaves chat/log terminals responsible for their own scroll state. This
prevents one terminal from pulling the whole tab to the bottom during refresh.

Agent action bars use `NeonActionGroup`, which groups actions into compact
two-column rows when needed. The goal is to avoid squeezed buttons without
duplicating actions or hiding core controls.

Gemini, Lucio and Codex share the same agent tab contract:

- independent session namespace;
- session create/open/rename/delete;
- scrollable timeline;
- normal/details/raw display modes;
- input artifacts;
- generated artifacts;
- copied sanitized text;
- no token or raw URL in normal mode.

## Refresh

The active screen polls every five seconds while attached. Polling stops when
the screen is detached.
