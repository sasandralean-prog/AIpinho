# Mobile Agent Timeline Renderer

The renderer follows three display modes:

- `normal`: user and agent messages only;
- `details`: messages plus sanitized operational events;
- `raw`: sanitized JSON after explicit confirmation.

The normal renderer never displays API keys, bearer tokens, raw references or
unsafe endpoint actions. Text remains selectable and copy uses the current
selection or the latest agent message.

Auto-scroll is bounded to initial load or an already-bottomed timeline. A
five-second refresh therefore does not pull the user away from older messages.

## Nested terminal behavior

Sprint 19 formalizes nested scrolling for chat/log terminals. A terminal may
request that the parent screen does not intercept touch events while the
terminal can scroll vertically. This keeps long Debugger, Chat, Gemini, Lucio
and Codex histories readable inside their own card instead of forcing the whole
screen to jump.

The implementation must use local scroll decisions, not a global activity-level
scroll command. Refresh-driven follow-bottom is allowed only for the active
terminal when the user was already at the bottom.
