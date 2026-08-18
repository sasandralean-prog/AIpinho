# Gemini Integration

Gemini integration path:

1. Create or receive a `task_run_id` through governed task creation.
2. Poll the same Universal Task Session endpoints used by Mobile, Dashboard, API and Codex.
3. Read approval, validation, artifact and result state from the session payload.

No Gemini-specific runtime endpoint was added.

Gemini is treated as a client of the Universal Task Session.

